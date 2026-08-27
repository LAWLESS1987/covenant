#!/usr/bin/env python3
"""probe_win_connect.py -- WHY does a REFUSED connect cost a second on Windows?

A23's S3 asserts that a REFUSED peer (RST: nothing listening) costs almost
nothing next to a DEAD peer (SYN black-holed: no answer at all). That gap is
what A12's dead-peer headroom is bought with. On Linux it holds. Measured on
win32 on 2026-08-27 it did NOT -- refused 1.053 s vs dead 1.12 s, near enough
identical -- so on the platform that runs production, A12's arithmetic rests on
a difference that is not there.

This probe does not assume a cause. It DISTINGUISHES the two candidates, which
need different fixes:

  (b1) connect() really did return WSAECONNREFUSED, slowly, because Windows
       does not surface the RST immediately -- it holds the socket in SYN-SENT
       and spends its SYN-retransmission budget first. Then the ~1.05 s is the
       stack, and the fix is at the dial layer.
  (b2) connect() never returned at all and OUR OWN timeout fired. Then both
       numbers are just our deadline, the "measurement" measured the
       stopwatch, and the fix is in the test.

THE EXCEPTION TYPE SEPARATES THEM, and only if the deadline is generous:
ConnectionRefusedError => b1.  TimeoutError => b2.  At a 1 s timeout the two
are indistinguishable -- which is exactly the trap the original measurement
fell into, so this uses 6 s.

Read-only. Opens sockets to ports where nothing is listening and to a
non-routable address, times them, and reads (never writes) the TCP settings.
Nothing is bound, nothing is sent, no node is touched.

Run:  python probe_win_connect.py
"""
import platform
import socket
import statistics
import subprocess
import sys
import time

TIMEOUT = 6.0
REPS = 5
CLOSED_LOOPBACK = ("127.0.0.1", 9), ("127.0.0.1", 47811)
# RFC 5737 TEST-NET-1: routable nowhere, so the SYN is black-holed rather than
# refused. This is the "dead peer" shape A12/A23 care about.
BLACKHOLE = ("192.0.2.1", 5000)


def attempt(addr, timeout=TIMEOUT):
    """(seconds, outcome) -- never raises. Outcome is the exception CLASS name,
    which is the whole point: it is what tells b1 from b2."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    t0 = time.perf_counter()
    try:
        s.connect(addr)
        return time.perf_counter() - t0, "CONNECTED (something IS listening -- pick another port)"
    except Exception as e:
        return time.perf_counter() - t0, type(e).__name__
    finally:
        s.close()


def series(label, addr, reps=REPS):
    times, outcomes = [], []
    for _ in range(reps):
        dt, out = attempt(addr)
        times.append(dt)
        outcomes.append(out)
    med = statistics.median(times)
    print(f"  {label:<34} median {med*1000:9.1f} ms   "
          f"min {min(times)*1000:8.1f}  max {max(times)*1000:8.1f}")
    print(f"  {'':<34} outcome: {sorted(set(outcomes))}")
    return med, set(outcomes)


def tcp_settings():
    if not sys.platform.startswith("win"):
        return
    print()
    print("  TCP settings (read-only). MaxSynRetransmissions is the number that")
    print("  decides how long a refused connect takes here:")
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Get-NetTCPSetting | Select-Object SettingName,InitialRtoMs,"
             "MaxSynRetransmissions | Format-Table -AutoSize | Out-String -Width 120"],
            capture_output=True, text=True, timeout=60)
        for line in (out.stdout or out.stderr or "").splitlines():
            if line.strip():
                print("    " + line.rstrip())
    except Exception as e:
        print(f"    could not read: {type(e).__name__}: {e}")


def main():
    print("probe_win_connect -- refused vs dead, and WHICH error came back")
    print(f"  platform {platform.system()} {platform.release()} "
          f"({platform.machine()})  python {sys.version.split()[0]}")
    print(f"  timeout {TIMEOUT}s, {REPS} reps. A generous timeout is load-bearing:")
    print( "  at 1 s a slow refusal and our own deadline look identical.")
    print()

    refused = []
    for addr in CLOSED_LOOPBACK:
        med, outs = series(f"REFUSED {addr[0]}:{addr[1]}", addr)
        refused.append((med, outs))
    dead_med, dead_outs = series(f"DEAD    {BLACKHOLE[0]}:{BLACKHOLE[1]}", BLACKHOLE)

    tcp_settings()

    ref_med = statistics.median([m for m, _ in refused])
    all_ref_outs = set().union(*[o for _, o in refused])
    print()
    print("  " + "-" * 70)
    print(f"  refused median {ref_med*1000:.1f} ms   dead median {dead_med*1000:.1f} ms")
    ratio = dead_med / ref_med if ref_med else float("inf")
    print(f"  dead/refused ratio {ratio:.1f}x  "
          f"(A23 S3 assumes this is LARGE; on Linux it is ~1000x+)")
    print()
    if "ConnectionRefusedError" in all_ref_outs:
        print("  VERDICT b1: connect() DID return ConnectionRefusedError -- the RST")
        print("    was received and reported. If it was also slow, the cost is the")
        print("    stack's SYN-retransmission budget before it surfaces the RST,")
        print("    NOT our timeout. Fix at the dial layer: key backoff on the")
        print("    CONSECUTIVE FAILURE COUNT and the ERROR CLASS, never on measured")
        print("    wall-clock cost, which is a platform accident.")
    elif "TimeoutError" in all_ref_outs:
        print("  VERDICT b2: connect() to a CLOSED port raised TimeoutError, not")
        print("    ConnectionRefusedError. Our own deadline fired first, so both")
        print("    of A23 S3's numbers are measurements of the stopwatch. The")
        print("    suite's premise, not the node, is what needs fixing.")
    else:
        print(f"  VERDICT unclear -- outcomes {sorted(all_ref_outs)}. Read them before")
        print("    changing anything.")
    print()
    print("  Either way the durable lesson is the same: a REFUSED connect being")
    print("  cheap is a property of Linux, not of TCP. RFC 793 does not require a")
    print("  stack to fail a connect on the first RST.")


if __name__ == "__main__":
    main()
