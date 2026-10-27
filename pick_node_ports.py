"""pick_node_ports.py -- find blocks of three ports a covenant node can actually bind.

WHY BINDING AND NOT NETSTAT. netstat shows what is LISTENING. It does not show
Windows' reserved and excluded port ranges (`netsh int ipv4 show
excludedportrange`), which Hyper-V and WSL carve out and which fail a bind with
WinError 10013 -- "an attempt was made to access a socket in a way forbidden by
its access permissions". test_multinode_live.py hit exactly that at 49553 and
switched to bind-probing for the same reason. A port can be free in netstat and
unbindable.

A node needs THREE ports and they are not adjacent: --port N is the API, N+1 is
P2P and N+11 is the bridge (M2). All three must bind, and nodes must sit at
least 20 apart so their blocks cannot overlap.

Usage:
    python pick_node_ports.py                    survey the default range
    python pick_node_ports.py 5000 5400          survey a range
    python pick_node_ports.py --need 3           report the first 3 free blocks
"""
import socket
import sys


def block_free(base, host="0.0.0.0"):
    """True only if all three of N, N+1, N+11 bind. Returns (ok, reason)."""
    socks = []
    try:
        for off in (0, 1, 11):
            s = socket.socket()
            # No SO_REUSEADDR: on Windows it lets a second process bind a port
            # another is actively listening on, which is the exact footgun A2
            # could not see until v8.30 (P5/A19). We want the strict answer.
            s.bind((host, base + off))
            s.listen(1)
            socks.append(s)
        return True, ""
    except OSError as e:
        return False, f"{base + len(socks)}: {e.__class__.__name__} {e}"
    finally:
        for s in socks:
            try:
                s.close()
            except Exception:
                pass


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    lo = int(args[0]) if args else 5000
    hi = int(args[1]) if len(args) > 1 else 5400
    need = 3
    if "--need" in sys.argv:
        need = int(sys.argv[sys.argv.index("--need") + 1])

    print(f"bind-probing {lo}-{hi} in steps of 20 "
          f"(each block is N, N+1, N+11)\n")
    free, taken = [], []
    for base in range(lo, hi + 1, 20):
        ok, why = block_free(base)
        if ok:
            free.append(base)
            print(f"  FREE   {base:5d}  ({base}, {base + 1}, {base + 11})")
        else:
            taken.append((base, why))
            print(f"  taken  {base:5d}  {why}")
    print()
    if not free:
        print("NO free block in this range. Widen it.")
        return 1
    print(f"{len(free)} free block(s). First {need}: "
          f"{', '.join(str(b) for b in free[:need])}")
    print()
    print("Set a node's --port to one of these, keep every node at least 20 "
          "apart, and give each peer the P2P port (API+1) -- never the API "
          "port. test_3node_config.py asserts all of that against "
          "covenant_prod.bat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
