#!/usr/bin/env python3
"""Who is holding the RAM on this box. Read-only.

Written 2026-08-22 because the fit check now reports FREE memory and said
2.8 GB free against a 5.2 GB judge model -- so the question stopped being
"tune the node" and became "what else is resident".

Lives in a .py and not inlined in a .bat on purpose: cmd expands % in a
string, so a python one-liner full of %-format specifiers silently produces
nothing. That is how the first version of this failed.
"""
import collections, re, subprocess, sys

out = subprocess.run(["tasklist", "/fo", "csv", "/nh"],
                     capture_output=True, text=True).stdout
mem, cnt = collections.Counter(), collections.Counter()
for line in out.splitlines():
    if not line.strip():
        continue
    cols = [c.strip('"') for c in line.split('","')]
    if len(cols) < 5:
        continue
    kb = re.sub(r"[^0-9]", "", cols[4])
    if not kb:
        continue
    mem[cols[0]] += int(kb)
    cnt[cols[0]] += 1

print("{:<30}{:>10}{:>8}".format("image", "MB", "count"))
print("-" * 48)
for name, kb in mem.most_common(22):
    print("{:<30}{:>10.0f}{:>8d}".format(name, kb / 1024.0, cnt[name]))
print()
print("tracked total: {:.1f} GB across {} processes".format(
    sum(mem.values()) / 1024.0 / 1024.0, sum(cnt.values())))
print()
print("covenant's own share:")
own = 0
for n in ("python.exe", "python3.12.exe", "ollama.exe", "ollama app.exe", "cmd.exe"):
    if n in mem:
        print("  {:<28}{:>10.0f} MB  x{}".format(n, mem[n] / 1024.0, cnt[n]))
        own += mem[n]
print("  {:<28}{:>10.0f} MB".format("subtotal", own / 1024.0))
