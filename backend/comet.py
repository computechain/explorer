"""Read-only CometBFT observer: canonical IDs, atomic SQLite index, no wallet keys.

The local node is the data source, not an independent light-client proof. Legacy
FastAPI/Postgres handlers are intentionally not loaded by this entrypoint.
"""
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timezone
import base64
import fcntl
import hashlib
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
import urllib.parse
import urllib.request

from fastapi import FastAPI, HTTPException, Query

log = logging.getLogger(__name__)
MAX_REPLY = 32*1024*1024
METHODS = {"status", "genesis", "block", "block_results", "abci_query", "validators"}


def rpc_url(value):
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "http" or parsed.username or parsed.password or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment or not parsed.port
            or not ipaddress.ip_address(parsed.hostname).is_loopback):
        raise ValueError("RPC source must be a literal loopback HTTP URL")
    return value.rstrip("/")


class Client:
    def __init__(self, url, chain):
        self.url, self.chain = rpc_url(url), chain

    def call(self, method, **params):
        if method not in METHODS:
            raise ValueError("read-only RPC allowlist")
        suffix = "?"+urllib.parse.urlencode(params) if params else ""
        with urllib.request.urlopen(self.url+"/"+method+suffix, timeout=5) as response:
            raw = response.read(MAX_REPLY+1)
        if len(raw) > MAX_REPLY:
            raise ValueError("RPC response size limit")
        value = json.loads(raw)
        if value.get("error"):
            raise ValueError("node RPC error")
        return value["result"]

    def state(self):
        result = self.call("abci_query", path=json.dumps("/state"))["response"]
        if int(result.get("code", 0)):
            raise ValueError("application query failed")
        state = json.loads(base64.b64decode(result["value"], validate=True))
        if state["chain_id"] != self.chain or state["schema"] != 3:
            raise ValueError("wrong chain or unsupported application schema")
        return state


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def amount(value):
    if not isinstance(value, str) or not re.fullmatch(r"0|[1-9][0-9]{0,77}", value) or int(value) >= 2**256:
        raise ValueError("invalid integer token amount")
    return value


def transaction(raw, height, position, result):
    digest = hashlib.sha256(raw).hexdigest().upper()  # native transaction ID
    try:
        tx = json.loads(raw)
        if not isinstance(tx, dict):
            raise ValueError("invalid envelope")
        principal, price = amount(tx["amount"]), amount(tx["gas_price"])
        kind, sender, recipient = tx["type"], tx["from"], tx["to"]
        if not isinstance(kind, str) or not isinstance(sender, str) or recipient is not None and not isinstance(recipient, str):
            raise ValueError("invalid transaction fields")
    except (ValueError, UnicodeError, KeyError, TypeError):
        tx, principal, price, kind, sender, recipient = {}, "0", "0", "UNKNOWN", "", None
    code = int(result.get("code", 0))
    gas = int(result.get("gas_used", 0))
    return {"hash": digest, "block_height": height, "tx_index": position,
        "tx_type": kind, "from_address": sender, "to_address": recipient,
        "amount": principal, "fee": str(gas*int(price) if code == 0 else 0),
        "nonce": str(tx.get("nonce", 0)), "gas_price": price, "gas_limit": tx.get("gas_limit", 0),
        "gas_used": gas, "code": code, "status": "success" if code == 0 else "failed",
        "log": result.get("log", ""), "signature": tx.get("signature"),
        "pub_key": tx.get("pub_key"), "payload": tx.get("payload", {})}


def block_record(reply, results, chain):
    block = reply["block"]
    header, digest = block["header"], reply["block_id"]["hash"]
    height = int(header["height"])
    if header["chain_id"] != chain or not re.fullmatch(r"[0-9A-F]{64}", digest) or int(results["height"]) != height:
        raise ValueError("block identity/domain mismatch")
    raw = [base64.b64decode(tx, validate=True) for tx in block["data"].get("txs") or []]
    receipts = results.get("txs_results") or []
    if len(raw) != len(receipts) or len(raw) > 500:
        raise ValueError("transaction/result count mismatch")
    txs = [transaction(tx, height, i, receipts[i]) for i, tx in enumerate(raw)]
    return {"height": height, "hash": digest, "timestamp": timestamp(header["time"]),
        "proposer": header["proposer_address"], "tx_count": len(txs),
        "gas_used": sum(tx["gas_used"] for tx in txs), "gas_limit": 10_500_000,
        "prev_hash": header["last_block_id"]["hash"], "chain_id": chain,
        "tx_root": header["data_hash"], "app_hash_before": header["app_hash"], "transactions": txs}


class Index:
    def __init__(self, path, chain):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.writer = (path.parent / ".writer.lock").open("a+b")
        try:
            fcntl.flock(self.writer, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.db = sqlite3.connect(path, check_same_thread=False)
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.executescript('''CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS blocks(height INTEGER PRIMARY KEY,hash TEXT UNIQUE,time REAL,body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS txs(hash TEXT PRIMARY KEY,height INTEGER,position INTEGER,kind TEXT,sender TEXT,recipient TEXT,body TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS tx_height ON txs(height DESC,position DESC);
                CREATE INDEX IF NOT EXISTS tx_sender ON txs(sender,height DESC);
                CREATE INDEX IF NOT EXISTS tx_recipient ON txs(recipient,height DESC);
                CREATE INDEX IF NOT EXISTS tx_kind ON txs(kind,height DESC);''')
            previous = self.db.execute("SELECT value FROM meta WHERE key='chain'").fetchone()
            if previous and previous[0] != chain:
                raise ValueError("index belongs to another chain; choose a fresh directory")
            self.chain, self.lock = chain, threading.RLock()
            self.updated, self.error, self.node_height = 0, "not connected", 0
            row = self.db.execute("SELECT value FROM meta WHERE key='state'").fetchone()
            self.state = json.loads(row[0]) if row else None
            if self.state:
                self.node_height = self.state["height"]
            row = self.db.execute("SELECT value FROM meta WHERE key='native_powers'").fetchone()
            self.native_powers = json.loads(row[0]) if row else {}
        except Exception:
            if hasattr(self, "db"):
                self.db.close()
            self.writer.close()
            raise

    def genesis(self, value):
        if value["chain_id"] != self.chain or value["app_state"].get("schema") != 3:
            raise ValueError("unsupported genesis")
        digest = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with self.lock, self.db:
            previous = self.db.execute("SELECT value FROM meta WHERE key='genesis'").fetchone()
            if previous and previous[0] != digest:
                raise ValueError("genesis changed; index is not reset automatically")
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('genesis',?)", (digest,))
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('chain',?)", (self.chain,))

    def height(self):
        with self.lock:
            return self.db.execute("SELECT COALESCE(MAX(height),0) FROM blocks").fetchone()[0]

    def append(self, block):
        txs = block["transactions"]
        summary = {k: v for k, v in block.items() if k != "transactions"}
        with self.lock, self.db:
            row = self.db.execute("SELECT height,hash FROM blocks ORDER BY height DESC LIMIT 1").fetchone()
            if block["height"] != (row[0]+1 if row else 1) or row and block["prev_hash"] != row[1]:
                raise ValueError("nonsequential or conflicting finalized history; no rollback")
            if not row and block["prev_hash"]:
                raise ValueError("unexpected parent of genesis block")
            self.db.execute("INSERT INTO blocks VALUES(?,?,?,?)", (block["height"], block["hash"], block["timestamp"], json.dumps(summary)))
            for tx in txs:
                self.db.execute("INSERT INTO txs VALUES(?,?,?,?,?,?,?)", (tx["hash"], tx["block_height"], tx["tx_index"],
                    tx["tx_type"], tx["from_address"], tx["to_address"], json.dumps(tx)))
            previous = self.db.execute("SELECT value FROM meta WHERE key='totals'").fetchone()
            totals = json.loads(previous[0]) if previous else {"transferred": "0", "fees": "0", "transactions": 0}
            totals["transferred"] = str(int(totals["transferred"])+sum(int(tx["amount"]) for tx in txs if tx["code"] == 0 and tx["tx_type"] == "TRANSFER"))
            totals["fees"] = str(int(totals["fees"])+sum(int(tx["fee"]) for tx in txs))
            totals["transactions"] += len(txs)
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('totals',?)", (json.dumps(totals),))

    def observe(self, state, powers, node_height):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('state',?)", (json.dumps(state),))
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('native_powers',?)", (json.dumps(powers),))
            self.state, self.native_powers, self.node_height = deepcopy(state), powers, node_height
            self.updated, self.error = time.time(), None

    def snapshot(self):
        with self.lock:
            if self.state is None:
                raise HTTPException(503, "observer not synchronized yet")
            return deepcopy(self.state)

    def close(self):
        self.db.close()
        self.writer.close()


def synchronize(index, client, stop):
    initialized = False
    while not stop.is_set():
        try:
            if not initialized:
                index.genesis(client.call("genesis")["genesis"])
                initialized = True
            status = client.call("status")
            if status["node_info"]["network"] != index.chain:
                raise ValueError("wrong RPC chain")
            target = int(status["sync_info"]["latest_block_height"])
            state = client.state()
            at_height = max(1, state["height"])
            vals = client.call("validators", height=at_height, per_page=100)["validators"]
            powers = {base64.b64decode(v["pub_key"]["value"], validate=True).hex(): int(v["voting_power"]) for v in vals}
            current = index.height()
            if current > target:
                raise ValueError("RPC history is behind the durable index")
            if current:
                remote = client.call("block", height=current)["block_id"]["hash"]
                with index.lock:
                    local = index.db.execute("SELECT hash FROM blocks WHERE height=?", (current,)).fetchone()[0]
                if remote != local:
                    raise ValueError("finalized block conflict; no automatic reset/reorg")
            for h in range(current+1, min(target, current+100)+1):
                if stop.is_set():
                    break
                value = block_record(client.call("block", height=h), client.call("block_results", height=h), index.chain)
                index.append(value)
            index.observe(state, powers, target)
            stop.wait(0.05 if index.height() < target else 2)
        except Exception as exc:
            with index.lock:
                index.error = str(exc)
            log.warning("observer sync: %s", exc)
            stop.wait(2)


def pages(total, page, limit):
    return {"page": page, "limit": limit, "total": total, "pages": (total+limit-1)//limit}


PAGE = Query(1, ge=1, le=1_000_000)
LIMIT = Query(25, ge=1, le=100)


def create_app(index, client=None):
    @asynccontextmanager
    async def lifespan(app):
        stop = threading.Event()
        worker = threading.Thread(target=synchronize, args=(index, client, stop), daemon=True) if client else None
        if worker:
            worker.start()
        yield
        stop.set()
        if worker:
            worker.join(timeout=12)
        index.close()

    app = FastAPI(title="ComputeChain v3 read-only explorer", version="0.3.0",
        docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None, lifespan=lifespan)

    @app.middleware("http")
    async def read_only(request, call_next):
        if request.method not in ("GET", "HEAD"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "read-only explorer"}, status_code=405)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/api/health")
    def health():
        if index.error or time.time()-index.updated > 15:
            raise HTTPException(503, "node unavailable or observer stale")
        return {"ok": True, "chain_id": index.chain, "indexed_height": index.height(), "node_height": index.node_height}

    @app.get("/api/stats")
    def stats():
        state = index.snapshot()
        with index.lock:
            height = index.height()
            latest = index.db.execute("SELECT time FROM blocks ORDER BY height DESC LIMIT 1").fetchone()
            row = index.db.execute("SELECT value FROM meta WHERE key='totals'").fetchone()
            totals = json.loads(row[0]) if row else {"transferred": "0", "fees": "0", "transactions": 0}
        return {"chain_id": index.chain, "blocks": {"total": height, "latest_height": index.node_height, "latest_timestamp": latest[0] if latest else 0},
            "transactions": {"total": totals["transactions"], "total_transferred": totals["transferred"], "total_fees": totals["fees"]},
            "accounts": {"total": len(state["accounts"])}, "supply": str(state["supply"]), "burned": str(state["burned"]),
            "sync": {"indexed_height": height, "state_height": state["height"], "node_height": index.node_height,
                "online": not index.error and time.time()-index.updated <= 15, "error": index.error,
                "last_updated": datetime.fromtimestamp(index.updated, timezone.utc).isoformat() if index.updated else None}}

    @app.get("/api/stats/tps")
    def tps():
        now = time.time()
        with index.lock:
            rows = index.db.execute("SELECT time,body FROM blocks WHERE time>=? ORDER BY height", (now-3600,)).fetchall()
        blocks = [(r[0], json.loads(r[1])["tx_count"]) for r in rows]
        span = max(1, now-blocks[0][0]) if blocks else 1
        return {"current_tps": sum(n for t,n in blocks if t >= now-30)/30,
            "avg_tps_1h": sum(n for t,n in blocks)/span, "avg_block_time": (blocks[-1][0]-blocks[0][0])/(len(blocks)-1) if len(blocks)>1 else 0,
            "blocks_1h": len(blocks), "txs_1h": sum(n for t,n in blocks)}

    @app.get("/api/blocks")
    def blocks(page: int = PAGE, limit: int = LIMIT):
        with index.lock:
            rows = index.db.execute("SELECT body FROM blocks ORDER BY height DESC LIMIT ? OFFSET ?", (limit,(page-1)*limit)).fetchall()
            return {"blocks": [json.loads(r[0]) for r in rows], "pagination": pages(index.height(),page,limit)}

    @app.get("/api/blocks/{identifier}")
    def block(identifier: str):
        with index.lock:
            if re.fullmatch(r"[1-9][0-9]{0,17}", identifier):
                row = index.db.execute("SELECT body FROM blocks WHERE height=?", (int(identifier),)).fetchone()
            elif re.fullmatch(r"[0-9a-fA-F]{64}", identifier):
                row = index.db.execute("SELECT body FROM blocks WHERE hash=?", (identifier.upper(),)).fetchone()
            else:
                raise HTTPException(400,"invalid block identifier")
            if not row:
                raise HTTPException(404,"block not indexed")
            value = json.loads(row[0])
            value["transactions"] = [json.loads(r[0]) for r in index.db.execute("SELECT body FROM txs WHERE height=? ORDER BY position", (value["height"],))]
            next_block = index.db.execute("SELECT body FROM blocks WHERE height=?", (value["height"]+1,)).fetchone()
            value["app_hash_after"] = json.loads(next_block[0])["app_hash_before"] if next_block else None
            return value

    def list_transactions(page, limit, kind=None, owner=None, direction=None):
        clauses, params = [], []
        if kind:
            clauses.append("kind=?")
            params.append(kind)
        if owner:
            if direction in ("sent", "received"):
                clauses.append("sender=?" if direction == "sent" else "recipient=?")
                params.append(owner)
            else:
                clauses.append("(sender=? OR recipient=?)")
                params.extend([owner,owner])
        where = " WHERE "+" AND ".join(clauses) if clauses else ""
        with index.lock:
            total = index.db.execute("SELECT COUNT(*) FROM txs"+where, params).fetchone()[0]
            rows = index.db.execute("SELECT body FROM txs"+where+" ORDER BY height DESC,position DESC LIMIT ? OFFSET ?", (*params,limit,(page-1)*limit)).fetchall()
        txs = [json.loads(r[0]) for r in rows]
        if owner:
            for tx in txs:
                tx["direction"] = "sent" if tx["from_address"] == owner else "received"
        return {"transactions": txs, "pagination": pages(total,page,limit)}

    @app.get("/api/transactions")
    def transactions(page: int = PAGE, limit: int = LIMIT, tx_type: str | None = Query(None, max_length=32), address: str | None = Query(None,max_length=64)):
        return list_transactions(page,limit,tx_type,address)

    @app.get("/api/transactions/recent")
    def recent(limit: int = Query(10,ge=1,le=100)):
        return list_transactions(1,limit)

    @app.get("/api/transactions/{digest}")
    def tx(digest: str):
        if not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise HTTPException(400,"invalid transaction ID")
        with index.lock:
            row = index.db.execute("SELECT body FROM txs WHERE hash=?", (digest.upper(),)).fetchone()
        if not row:
            raise HTTPException(404,"transaction not indexed")
        return json.loads(row[0])

    def account(owner, state):
        if owner not in state["accounts"]:
            raise HTTPException(404,"account not present in observed state")
        with index.lock:
            sent = index.db.execute("SELECT COUNT(*) FROM txs WHERE sender=?", (owner,)).fetchone()[0]
            received = index.db.execute("SELECT COUNT(*) FROM txs WHERE recipient=?", (owner,)).fetchone()[0]
            total = index.db.execute("SELECT COUNT(*) FROM txs WHERE sender=? OR recipient=?", (owner,owner)).fetchone()[0]
        return {"address": owner, "balance": str(state["accounts"][owner]["balance"]), "nonce": str(state["accounts"][owner]["nonce"]),
            "state_height": state["height"], "tx_count": total, "tx_sent_count": sent, "tx_received_count": received,
            "is_validator": any(v["owner"] == owner and not v["tombstoned"] and state["engine_powers"].get(key,0)>0 for key,v in state["validators"].items()),
            "unbonding": str(sum(q["amount"] for q in state["unbondings"] if q["owner"] == owner)),
            "self_stake": str(sum(v["self_stake"] for v in state["validators"].values() if v["owner"] == owner)),
            "delegated": str(sum(v["delegations"].get(owner,{}).get("amount",0) for v in state["validators"].values()))}

    @app.get("/api/accounts")
    def accounts(page: int = PAGE, limit: int = LIMIT, sort_by: str = "balance", order: str = "desc"):
        if sort_by not in ("balance","nonce","address") or order not in ("asc","desc"):
            raise HTTPException(400,"unsupported sort")
        state = index.snapshot()
        keys = sorted(state["accounts"], key=lambda a: (a if sort_by == "address" else state["accounts"][a][sort_by],a), reverse=order == "desc")
        return {"accounts": [account(a,state) for a in keys[(page-1)*limit:page*limit]], "pagination": pages(len(keys),page,limit)}

    @app.get("/api/accounts/{owner}/transactions")
    def history(owner: str, page: int = PAGE, limit: int = LIMIT, direction: str | None = None):
        if len(owner)>64 or direction not in (None,"sent","received"):
            raise HTTPException(400,"invalid account/direction")
        return list_transactions(page,limit,owner=owner,direction=direction)

    @app.get("/api/accounts/{owner}")
    def detail(owner: str):
        return account(owner,index.snapshot())

    @app.get("/api/validators")
    def validators():
        state = index.snapshot()
        return {"state_height": state["height"], "validators": [{"pub_key": key, "owner": val["owner"],
            "self_stake": str(val["self_stake"]), "delegated": str(sum(d["amount"] for d in val["delegations"].values())),
            "commission_bps": val["commission_bps"], "commission_change": val["commission_change"],
            "native_power": str(index.native_powers.get(key,0)), "scheduled_power": str(state["engine_powers"].get(key,0)),
            "tombstoned": val["tombstoned"], "penalties": str(val["penalties"])} for key,val in state["validators"].items()]}

    @app.get("/api/search")
    def search(q: str = Query(min_length=1,max_length=100)):
        q = q.strip()
        if re.fullmatch(r"[1-9][0-9]{0,17}",q):
            block(q)
            return {"path": "/blocks/"+q}
        if re.fullmatch(r"[0-9a-fA-F]{64}",q):
            with index.lock:
                if index.db.execute("SELECT 1 FROM txs WHERE hash=?",(q.upper(),)).fetchone():
                    return {"path": "/transactions/"+q.upper()}
            block(q)
            return {"path": "/blocks/"+q.upper()}
        detail(q)
        return {"path": "/accounts/"+urllib.parse.quote(q,safe="")}

    return app


def application():
    chain = os.environ["CPC_CHAIN_ID"]
    return create_app(Index(os.environ["CPC_INDEX_PATH"],chain), Client(os.environ["CPC_RPC_URL"],chain))
