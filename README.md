# ComputeChain Explorer — Comet v3

Read-only observer for the current CometBFT/ABCI ledger. The existing
Next.js UI now uses a separate canonical Comet adapter and durable SQLite index.
It is not a wallet, block producer or independent light client.

## Run on the stand

From the sibling blockchain repository, after starting its v3 stand:

~~~bash
./start_test.sh explorer-up
./start_test.sh explorer-status
./start_test.sh explorer-logs
./start_test.sh explorer-down
~~~

Open [Explorer](http://192.168.0.100:4000/). No login required.
Normal stand up includes explorer; --no-web skips explorer/website startup.
Override the UI port with --explorer-port and LAN address with --monitoring-host.
Stop/restart keeps the SQLite index in <devnet>/explorer/index/. No keys or node
databases are mounted. Runtime settings/config live outside Git.

## Current source: multisite WAN devnet

The deployed explorer now observes `cpc-multisite-devnet-1` via full-a1 native
loopback RPC27641. One synchronized full node provides this chain's state; the
explorer does not need to aggregate all replicas. It remains a trusted observer,
not an independent light client. Source node ID and the approved genesis are pinned.

The old local-chain index stays at `<devnet>/explorer/index/`. The new index is
separate: `<devnet>/explorer/indexes/CHAIN/GENESIS_SHA256/`. Never reuse or reset one
chain's SQLite for another. Latest account state and indexed-history heights may
briefly differ during catch-up. The source selection persists across ordinary
`explorer-up`; the old stand's network.json cannot silently switch it back.

Explicit operator switch from the workspace (full history from block1 required):

~~~bash
.tools/blockchain-venv/bin/python computechain/scripts/web_services.py explorer up \
  --observer-home /root/computechain-node/cpc-multisite-devnet-1/nodes/full-a1
~~~

Only public genesis/source config and the chain-specific public index are mounted;
the supplied node home, wallets and signer keys are NEVER container mounts. A wrong
ID/genesis, RPC redirect or conflicting finalized history fails closed. Website
stats use this same explorer, so both sites now display the WAN devnet.

В LAN: http://192.168.0.100:4000/. Логин не нужен. Команды выше управляют только
explorer, не перезапускают цепь. Индекс сохраняется после остановки.

## Working minimum

- Actual native block ID; transaction ID = SHA256 of raw signed wire bytes.
- Paginated blocks and transactions; type/account filters and authored/recipient history.
- Height/block-hash/transaction-hash/account search, including lowercase hex.
- Liquid balance, nonce, self stake, delegation and queued withdrawals.
- Validator owner/key binding, native versus scheduled power, commission and tombstone.
- Explicit successful/failed execution status; exact base-unit token strings.
- Visible observed-node, index and account-state heights; offline/stale state is labelled.
- Responsive UI; local assets/fonts, without a runtime Tailwind CDN.

AppHash in block H is the result before executing H. The after-H hash comes
from indexed header H+1; it stays unavailable until that header is indexed.
Account snapshots are latest observed application state, not historical proofs.
Transaction totals cover indexed history only; the index is rebuilt from genesis
and may initially lag. The local node is trusted as observer data source.

## Deployment boundary

Nginx exposes only GET/HEAD UI/API on a selected private LAN IP. Backend and
Next.js bind loopback at base_port+200 / base_port+201. Comet RPC/ABCI remain
loopback; arbitrary RPC proxying and transaction broadcasting are not exposed.
Containers are non-root, read-only except the public index/tmpfs, resource-bounded,
with digest-pinned base images. No Postgres is needed for this MVP.

[Public explorer](https://explorer.computechain.space/) uses the existing edge
Nginx and HTTPS. It displays the experimental multisite devnet, not a public
production chain. Public POST/broadcast and arbitrary native RPC are rejected.
Only the configured edge peer may forward the HTTPS scheme; untrusted LAN
clients cannot override it with X-Forwarded-Proto. The current TCP SNI edge loses
original client IPs: the gateway's API quota is shared by public visitors.
Core PUBLIC_SITES.md describes the edge routing, renewal and operator commands.

The active backend is backend/comet.py (single index writer, one Uvicorn worker).
Legacy API/Postgres/indexer modules and docker-compose.legacy.yml are historical,
not compatible with v3; do not use the old bare startup instructions.
The default Compose file requires runtime variables from the stand controller.
Finalized conflicts/domain changes fail closed; no automatic reorg/reset occurs.

## Development checks

Python dependencies: backend/requirements-comet.txt; tests also need pytest/httpx.
Run tests with scratch storage, e.g. from the workspace:

~~~bash
.tools/explorer-venv/bin/python -m pytest explorer/backend/tests -q
~~~

Frontend: Next.js 16 / React 19 / Tailwind 4; package-lock.json is checked in.
Use npm ci and npm run build (includes TypeScript checks). Docker builds these
without installing Node globally. Runtime versions are pinned in the Dockerfiles.

Still pending: production-grade per-client API quotas/auth, large-history performance,
independent light-client proofs and real wallet/compute-market functionality.
