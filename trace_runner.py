import sys, os, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov
def log(*a):
    print(f"TRACE {time.time():.3f} [{threading.current_thread().name}]", *a, flush=True)
P = cov.P2PNode
M = cov.CovenantUnifiedMaster
_ann = P.announce_block
def announce_block(self, block, exclude_peer=None):
    with self.peers_lock: peers = list(self.peers.items())
    log(f"announce_block idx={block.index} exclude={exclude_peer} peers={peers}")
    return _ann(self, block, exclude_peer)
P.announce_block = announce_block
_send = P._send_raw
def _send_raw(self, host, port, data, attempts=3):
    r = _send(self, host, port, data, attempts)
    log(f"_send_raw to {host}:{port} {data[:60]} -> {r}")
    return r
P._send_raw = _send_raw
_fa = M._fetch_announced
def _fetch_announced(self, host, port, index, sender_id):
    log(f"_fetch_announced from {host}:{port} idx={index} sender={sender_id} height={len(self.node.chain)}")
    r = _fa(self, host, port, index, sender_id)
    log(f"_fetch_announced done height={len(self.node.chain)}")
    return r
M._fetch_announced = _fetch_announced
_rec = cov.AnomalyMonitor.record if hasattr(cov, "AnomalyMonitor") else None
if _rec:
    def record(self, kind, detail=""):
        log(f"anomaly {kind}: {detail}")
        return _rec(self, kind, detail)
    cov.AnomalyMonitor.record = record
_acc = M._accept_block_common
def _accept_block_common(self, block):
    r = _acc(self, block)
    log(f"_accept_block_common idx={block.index} -> {r} height={len(self.node.chain)}")
    return r
M._accept_block_common = _accept_block_common
sys.argv[0] = cov.__file__
cov.main()
