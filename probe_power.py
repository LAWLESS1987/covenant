"""probe_power.py -- E1: what does a Covenant node cost to run, idle and mining?

Measures, on this host, with the shipped source:
  P1  idle CPU of a REAL node process (listeners, tip-gossip loop, governor
      loop, succession loop, main sleep loop) over a 60 s window, from
      /proc/<pid>/stat  (utime+stime) -- plus RSS
  P2  one block of proof-of-work at MINING_DIFFICULTY, 5 samples: CPU
      seconds per block and the mean/worst, with the expected count
      (16**difficulty / 2 hashes) for scale
  P3  the cost of each periodic loop per day from its interval and a
      measured per-iteration CPU time (tip gossip = one announce per peer)
  P4  a rough energy translation: CPU-seconds/day at ~2.5 W per active
      core (phone class) and ~10 W (laptop) -> Wh/day; against a phone's
      ~15 Wh battery

No node code changes. Numbers are this sandbox's; a phone is slower (the
ratio idle:mining is what transfers, not the seconds).
"""
import os
import subprocess
import sys
import tempfile
import time

os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_unified_v8 as cov

CLK = os.sysconf("SC_CLK_TCK")


def cpu_seconds(pid):
    with open(f"/proc/{pid}/stat") as fh:
        f = fh.read().rsplit(")", 1)[1].split()
    return (int(f[11]) + int(f[12])) / CLK


def rss_mb(pid):
    with open(f"/proc/{pid}/status") as fh:
        for line in fh:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024
    return float("nan")


def main():
    print(f"== E1 power probe: MINING_DIFFICULTY={cov.MINING_DIFFICULTY} ADAPTIVE_POW={cov.ADAPTIVE_POW} "
          f"TIP_GOSSIP_INTERVAL_S={cov.TIP_GOSSIP_INTERVAL_S}")

    # ---- P1 idle node process
    db = tempfile.mktemp(suffix="_power.db")
    env = dict(os.environ, COVENANT_DB=db)
    p = subprocess.Popen([sys.executable, os.path.join(HERE, "covenant_unified_v8.py"), "--port", "19700",
                          "--node-id", "powerprobe"], cwd=HERE, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(12)                       # boot + genesis mint + first gossip
        c0, t0 = cpu_seconds(p.pid), time.monotonic()
        time.sleep(60)
        c1, t1 = cpu_seconds(p.pid), time.monotonic()
        idle_pct = 100.0 * (c1 - c0) / (t1 - t0)
        print(f"P1 idle node: {c1 - c0:.3f} CPU-s over {t1 - t0:.0f} s = {idle_pct:.2f}% of one core; "
              f"RSS {rss_mb(p.pid):.0f} MB; boot CPU {c0:.2f} s (includes genesis PoW)")
    finally:
        p.kill(); p.wait()

    # ---- P2 mining cost
    samples = []
    for _ in range(5):
        b = cov.Block(1, [], "0" * 64)
        t = time.process_time()
        b.mine(cov.MINING_DIFFICULTY)
        samples.append(time.process_time() - t)
    exp_hashes = 16 ** cov.MINING_DIFFICULTY / 2
    print(f"P2 mining: per block CPU-s {['%.2f' % s for s in samples]} mean {sum(samples)/5:.2f} s "
          f"(expected ~{exp_hashes:,.0f} hashes at difficulty {cov.MINING_DIFFICULTY}; "
          f"hash rate ~{exp_hashes/(sum(samples)/5):,.0f}/s here)")

    # ---- P3 per-loop cost
    # tip gossip: one announce frame build + send attempt per peer per interval;
    # measure the frame build only (network is the peer's problem)
    m = cov.CovenantUnifiedMaster("probe", host="127.0.0.1", port=19712, p2p_port=19713,
                                  db_path=tempfile.mktemp(suffix="_p3.db"))
    m.add_genesis_block()
    t = time.process_time()
    for _ in range(200):
        cov.asdict(m.node.chain[-1])
    per_frame = (time.process_time() - t) / 200
    per_day_gossip = 86400 / cov.TIP_GOSSIP_INTERVAL_S
    print(f"P3 loops: tip gossip every {cov.TIP_GOSSIP_INTERVAL_S:.0f} s = {per_day_gossip:.0f}/day; "
          f"frame build {per_frame*1e3:.2f} ms -> {per_frame*per_day_gossip:.2f} CPU-s/day/peer; "
          f"governor + succession loops sleep on their interval (no busy wait)")

    # ---- P4 energy
    idle_cpu_day = idle_pct / 100 * 86400
    mine_cpu = sum(samples) / 5
    for label, watts in (("phone core", 2.5), ("laptop core", 10.0)):
        idle_wh = idle_cpu_day * watts / 3600
        per_block_wh = mine_cpu * watts / 3600
        print(f"P4 {label} ~{watts} W active: idle {idle_wh:.2f} Wh/day; mining {per_block_wh*1000:.1f} mWh/block; "
              f"100 blocks/day = {per_block_wh*100:.2f} Wh/day "
              f"(phone battery ~15 Wh: idle = {idle_wh/15:.1%}/day, 100 blocks = {per_block_wh*100/15:.1%}/day)")
    try:
        m.db.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()
