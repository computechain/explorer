"""Observer contracts. Uses scratch storage and synthetic public data, never keys."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from explorer.backend.comet import Index, create_app, block_record, transaction, Client, rpc_url
from explorer.backend.comet import genesis_identity
from explorer.backend.comet import synchronize, NoRedirect

CHAIN = "observer-test"
RAW = json.dumps({"type":"TRANSFER","from":"cpc1sender","to":"cpc1recipient","amount":str(2**100+19),
    "gas_price":"1000","gas_limit":21000,"nonce":0,"payload":{}},sort_keys=True,separators=(",",":")).encode()


def test_observer_pins_public_genesis_and_node_together(tmp_path):
    genesis={'chain_id':CHAIN,'app_state':{'schema':3},'genesis_time':'2026-10-08T05:03:41.982680Z'}
    path=tmp_path/'genesis.json'; path.write_text(json.dumps(genesis))
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    client=Client('http://127.0.0.1:27641',CHAIN,'a'*40,path,sha)
    assert client.expected_node_id=='a'*40
    assert client.pinned_genesis==genesis_identity({**genesis,'genesis_time':'2026-10-08T05:03:41.98268Z'})
    assert client.pinned_genesis!=genesis_identity({**genesis,'genesis_time':'2026-10-08T05:03:41.982680001Z'})
    with pytest.raises(ValueError): Client('http://127.0.0.1:27641',CHAIN,'a'*40)
    with pytest.raises(ValueError): Client('http://127.0.0.1:27641',CHAIN,'a'*40,path,'f'*64)
    with pytest.raises(ValueError): Client('http://127.0.0.1:27641','other-chain','a'*40,path,sha)


@pytest.mark.parametrize('fault',['node-id','genesis'])
def test_wrong_pinned_source_cannot_publish_history_or_account_state(tmp_path,monkeypatch,fault):
    genesis={'chain_id':CHAIN,'app_state':{'schema':3}}
    path=tmp_path/'genesis.json'; path.write_text(json.dumps(genesis))
    client=Client('http://127.0.0.1:27641',CHAIN,'a'*40,path,hashlib.sha256(path.read_bytes()).hexdigest())
    def call(method,**params):
        if method=='genesis': return {'genesis':{**genesis,'extra':'foreign'} if fault=='genesis' else genesis}
        if method=='status': return {'node_info':{'network':CHAIN,'id':'b'*40}}
        pytest.fail('unapproved source must fail before block/state queries')
    monkeypatch.setattr(client,'call',call)
    monkeypatch.setattr(client,'state',lambda:pytest.fail('unapproved state query'))
    class OnePoll:
        done=False
        def is_set(self): return self.done
        def wait(self,seconds): self.done=True
    index=Index(tmp_path/'index/index.sqlite',CHAIN)
    try:
        synchronize(index,client,OnePoll())
        assert index.height()==0 and index.state is None
        assert 'identity' in index.error if fault=='node-id' else 'genesis' in index.error
    finally: index.close()


def test_rpc_redirect_cannot_escape_loopback():
    with pytest.raises(ValueError,match='redirect'):
        NoRedirect().redirect_request(None,None,302,'redirect',{},'http://8.8.8.8/')


def sample(h=1, prev="", raw=(RAW,), codes=None):
    digest=hashlib.sha256(str(h).encode()).hexdigest().upper()
    header={"height":str(h),"chain_id":CHAIN,"time":"2026-10-07T13:00:00.123456789Z",
        "proposer_address":"AA"*20,"last_block_id":{"hash":prev},"data_hash":"DD"*32,"app_hash":str(h)*64}
    return {"block_id":{"hash":digest},"block":{"header":header,"data":{"txs":[base64.b64encode(r).decode() for r in raw]}}}, {
        "height":str(h),"txs_results":[{"code":code,"gas_used":21000 if not code else 0} for code in (codes or [0]*len(raw))]}


@pytest.fixture
def observer(tmp_path):
    index=Index(tmp_path/"index.sqlite",CHAIN)
    index.genesis({"chain_id":CHAIN,"app_state":{"schema":3}})
    reply,result=sample()
    index.append(block_record(reply,result,CHAIN))
    state={"schema":3,"chain_id":CHAIN,"height":2,"supply":2**200+11,"burned":21000000,
        "accounts":{"cpc1sender":{"balance":2**100+7,"nonce":2**60+1},"cpc1recipient":{"balance":0,"nonce":0}},
        "validators":{"ab"*32:{"owner":"cpc1sender","self_stake":1000*10**18,"delegations":{},
            "commission_bps":1000,"commission_change":None,"tombstoned":False,"penalties":0}},
        "engine_powers":{"ab"*32:1000},"unbondings":[{"owner":"cpc1sender","amount":2**90+3}]}
    index.observe(state,{"ab"*32:1000},2)
    with TestClient(create_app(index)) as client:
        yield index,client


def test_native_ids_apphash_semantics_and_search(observer):
    index,client=observer
    expected=hashlib.sha256(RAW).hexdigest().upper()
    tx=client.get("/api/transactions/"+expected.lower()).json()
    assert tx["hash"]==expected and tx["amount"]==str(2**100+19)
    block=client.get("/api/blocks/1").json()
    assert block["hash"]==hashlib.sha256(b"1").hexdigest().upper()
    assert block["app_hash_before"]=="1"*64 and block["app_hash_after"] is None
    reply,result=sample(2,prev=block["hash"],raw=())
    index.append(block_record(reply,result,CHAIN))
    assert client.get("/api/blocks/1").json()["app_hash_after"]=="2"*64
    assert client.get("/api/search",params={"q":expected}).json()["path"]=="/transactions/"+expected
    assert client.get("/api/search",params={"q":block["hash"]}).json()["path"]=="/blocks/"+block["hash"]


def test_exact_accounts_power_and_totals(observer):
    index,client=observer
    account=client.get("/api/accounts/cpc1sender").json()
    assert account["balance"]==str(2**100+7) and account["nonce"]==str(2**60+1)
    assert account["unbonding"]==str(2**90+3)
    stats=client.get("/api/stats").json()
    assert stats["supply"]==str(2**200+11)
    assert stats["transactions"]["total_transferred"]==str(2**100+19)
    assert stats["transactions"]["total_fees"]=="21000000"
    assert stats["sync"]["indexed_height"]==1 and stats["sync"]["node_height"]==2
    val=client.get("/api/validators").json()["validators"][0]
    assert val["native_power"]=="1000" and val["self_stake"]==str(1000*10**18)


def test_pagination_filters_history_and_invalid_routes(observer):
    index,client=observer
    assert client.get("/api/blocks",params={"limit":101}).status_code==422
    assert client.get("/api/blocks",params={"page":0}).status_code==422
    assert client.get("/api/transactions",params={"tx_type":"STAKE"}).json()["transactions"]==[]
    assert client.get("/api/accounts/cpc1sender/transactions?direction=sent").json()["pagination"]["total"]==1
    assert client.get("/api/accounts/cpc1sender/transactions?direction=oops").status_code==400
    assert client.get("/api/accounts/unknown").status_code==404
    assert client.get("/api/accounts?sort_by=DROP%20TABLE").status_code==400
    assert client.get("/api/blocks/invalid").status_code==400
    assert client.get("/api/search?q=javascript:alert(1)").status_code==404
    assert client.post("/api/stats").status_code==405
    assert client.get("/api/broadcast_tx_commit").status_code==404


def test_offline_is_not_fake_live_zero(observer):
    index,client=observer
    index.error="node unavailable"
    assert client.get("/api/health").status_code==503
    stats=client.get("/api/stats").json()
    assert not stats["sync"]["online"] and stats["blocks"]["total"]==1


def test_failed_and_malformed_transaction_preserve_native_status():
    tx=transaction(RAW,1,0,{"code":1,"gas_used":0,"log":"invalid nonce"})
    assert tx["status"]=="failed" and tx["fee"]=="0" and tx["code"]==1
    tx=transaction(b"invalid json",1,0,{"code":1})
    assert tx["tx_type"]=="UNKNOWN" and tx["hash"]==hashlib.sha256(b"invalid json").hexdigest().upper()


def test_block_result_count_and_domain_mismatch():
    reply,result=sample()
    with pytest.raises(ValueError):
        block_record(reply,result,"wrong-chain")
    result["txs_results"]=[]
    with pytest.raises(ValueError,match="count"):
        block_record(reply,result,CHAIN)


def test_atomic_failed_index_write_and_restart(observer):
    index,client=observer
    first=client.get("/api/blocks/1").json()
    reply,result=sample(2,prev=first["hash"])  # duplicate tx ID triggers rollback
    with pytest.raises(sqlite3.IntegrityError):
        index.append(block_record(reply,result,CHAIN))
    assert index.height()==1
    assert client.get("/api/stats").json()["transactions"]["total"]==1


def test_storage_identity_writer_lock_and_no_reset(tmp_path):
    path=tmp_path/"index.sqlite"
    index=Index(path,CHAIN)
    index.genesis({"chain_id":CHAIN,"app_state":{"schema":3}})
    with pytest.raises(OSError):
        Index(path,CHAIN)
    with pytest.raises(ValueError,match="genesis"):
        index.genesis({"chain_id":CHAIN,"app_state":{"schema":3,"changed":True}})
    index.close()
    with pytest.raises(ValueError,match="another chain"):
        Index(path,"other")
    reopened=Index(path,CHAIN)
    reopened.close()


@pytest.mark.parametrize("url",["http://8.8.8.8:80","https://127.0.0.1:80","http://localhost:80","http://127.0.0.1:80/path","http://user@127.0.0.1:80"])
def test_no_external_arbitrary_rpc_proxy(url):
    with pytest.raises(ValueError):
        rpc_url(url)
    with pytest.raises(ValueError,match="allowlist"):
        Client("http://127.0.0.1:28601",CHAIN).call("broadcast_tx_commit")
