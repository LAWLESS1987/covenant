#!/usr/bin/env python3
"""tools/opsec_scan.py -- keep his identifiers out of the public repository, by default.

HIS WORDS, 2026-09-26: "take the portfolio id out of the public file protect operation
security in all we do by default".

WHY IT EXISTS. The same day's sweep found his home internet address in a test, the
phone's and the PC's tailnet addresses and device names in a dozen public files, a
Syncthing device id and his Wi-Fi name in the issue register, and 101 rows of his own
conversations one `git add` from the public tree. Every one of them got there the same
way: something private was copied into a tracked file and nothing looked before it was
pushed. Name-based .gitignore rules cannot see content, and the earlier purge tool
reads numbers only.

THE VALUES ARE READ, NEVER WRITTEN DOWN. What it looks for is gathered at run time from
where each value already lives privately:
  * Tailscale's own status (this PC's and every peer's tailnet addresses, device and
    tailnet names, and the public/LAN endpoints Tailscale discovered for this PC);
  * ops/syncthing/config.xml (device ids);
  * the Wi-Fi interface's network name (netsh);
  * this PC's LAN addresses (ipconfig) and the LAN callers in ops/heal.jsonl;
  * the gitignored money grant ops/earn_grant.json (account ids, wallet addresses);
  * private/bystanders.txt (people who are never named in any file).
A file listing the values would itself be the leak, so none exists. Output masks every
value (first four and last two characters).

    python tools/opsec_scan.py --scan          tracked files, as they are on disk now
    python tools/opsec_scan.py --fix           replace hits in records and docs with a label
    python tools/opsec_scan.py --pre-push      git's pre-push hook (reads refs on stdin)

--fix rewrites records and docs only (.md .txt .jsonl .csv .log). Code, scripts and test
fixtures are REPORTED, never rewritten: the running system reads some of those values
(the watchdog's peer list, the cloud's listen address), and a label there would stop a
node. Those are for a person to move.

--pre-push scans every line the outgoing commits ADD, commit by commit, and their
messages -- so a value added and removed inside one push is still caught, because both
commits would be public. A hit refuses the push and names file:line, masked. The commit
stays local; nothing is lost. COVENANT_OPSEC_ALLOW=1 lets one push through on his say,
and the override is logged to ops/opsec_overrides.jsonl (gitignored).

WHAT IT CANNOT SEE, named: a value from a source it does not read (an e-mail address
typed into a chat, a person not listed in bystanders.txt, an account figure); a value
written in another form (octal, NAT64, split across lines); anything already in public
history, which only a history rewrite removes. On a machine with none of these sources
it finds nothing and says NOT MEASURED rather than "clean".
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX_EXT = (".md", ".txt", ".jsonl", ".csv", ".log")
OVERRIDES = os.path.join(ROOT, "ops", "opsec_overrides.jsonl")
LABEL = {"pc-tailnet-ip": "<pc-tailnet-ip>", "tailnet-ip": "<tailnet-ip>", "home-public-ip": "<home-public-ip>",
         "lan-ip": "<lan-ip>", "tailnet-dns-name": "<tailnet-dns-name>", "tailnet-name": "<tailnet-name>",
         "device-name": "<device-name>", "syncthing-device-id": "<syncthing-device-id>", "wifi-name": "<wifi-name>",
         "account-id": "<account-id>", "wallet-address": "<wallet-address>", "private-person": "[a private person]"}
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_EVM = re.compile(r"^0x[0-9a-fA-F]{40}$")
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def mask(v):
    v = str(v)
    return v[:4] + "..." + v[-2:] if len(v) > 8 else v[:1] + "..."


def _run(args, timeout=15):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, creationflags=_NO_WINDOW)
        return p.stdout if p.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _ip_kind(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if a.is_loopback or a.is_unspecified or a.is_link_local or a.is_multicast:
        return None
    if a.version == 4 and a in ipaddress.ip_network("100.64.0.0/10"):
        return "tailnet"
    if a.version == 6 and a in ipaddress.ip_network("fd7a:115c:a1e0::/48"):
        return "tailnet"
    # LAN means the home/office ranges only; Python's is_private also counts the
    # documentation ranges, which are nobody's network (found by OS1a).
    lan = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16") if a.version == 4 else ("fc00::/7",)
    if any(a in ipaddress.ip_network(n) for n in lan):
        return "lan"
    return "public" if a.is_global else None


def tailscale_status():
    exe = shutil.which("tailscale") or r"C:\Program Files\Tailscale\tailscale.exe"
    out = _run([exe, "status", "--json"]) if (shutil.which("tailscale") or os.path.isfile(exe)) else ""
    try:
        return json.loads(out) if out else {}
    except ValueError:
        return {}


def tokens_from_tailscale(st):
    toks = []
    if not st:
        return toks

    def device(node, ip_cat):
        for ip in node.get("TailscaleIPs") or []:
            toks.append((ip_cat, ip))
        dns = str(node.get("DNSName") or "").rstrip(".")
        if dns:
            toks.append(("tailnet-dns-name", dns))
            if len(dns.split(".")[0]) >= 6:
                toks.append(("device-name", dns.split(".")[0]))
        host = str(node.get("HostName") or "")
        if len(host) >= 6:
            toks.append(("device-name", host))
    self_ = st.get("Self") or {}
    device(self_, "pc-tailnet-ip")
    for ep in self_.get("Addrs") or []:
        ip = ep.rsplit(":", 1)[0].strip("[]")
        k = _ip_kind(ip)
        if k == "public":
            toks.append(("home-public-ip", ip))
        elif k == "lan":
            toks.append(("lan-ip", ip))
    for peer in (st.get("Peer") or {}).values():
        device(peer, "tailnet-ip")
    for name in (st.get("MagicDNSSuffix"), (st.get("CurrentTailnet") or {}).get("Name")):
        if name and len(str(name)) >= 6:
            toks.append(("tailnet-name", str(name).rstrip(".")))
    return toks


def tokens_from_files(root=ROOT):
    toks = []
    cfg = os.path.join(root, "ops", "syncthing", "config.xml")
    if os.path.isfile(cfg):
        for m in re.finditer(r'<device id="([A-Z2-7]{7}(?:-[A-Z2-7]{7}){7})"', open(cfg, encoding="utf-8", errors="replace").read()):
            toks.append(("syncthing-device-id", m.group(1)))
    heal = os.path.join(root, "ops", "heal.jsonl")
    if os.path.isfile(heal):
        for line in open(heal, encoding="utf-8", errors="replace"):
            for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", line):
                if _ip_kind(ip) == "lan":
                    toks.append(("lan-ip", ip))
    grant = os.path.join(root, "ops", "earn_grant.json")
    if os.path.isfile(grant):
        def walk(o):
            if isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            elif isinstance(o, str):
                if _UUID.match(o):
                    toks.append(("account-id", o))
                elif _EVM.match(o):
                    toks.append(("wallet-address", o))
        try:
            walk(json.load(open(grant, encoding="utf-8")))
        except ValueError:
            pass
    by = os.path.join(root, "private", "bystanders.txt")
    if os.path.isfile(by):
        for line in open(by, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line and not line.startswith("#") and len(line) >= 3:
                toks.append(("private-person", line))
    return toks


def tokens_from_system():
    toks = []
    for line in _run(["netsh", "wlan", "show", "interfaces"]).splitlines():
        m = re.match(r"^\s*SSID\s*:\s*(.+?)\s*$", line)
        if m and len(m.group(1)) >= 6:
            toks.append(("wifi-name", m.group(1)))
    for ip in re.findall(r"IPv4 Address[ .]*:\s*([\d.]+)", _run(["ipconfig"])):
        if _ip_kind(ip) == "lan":
            toks.append(("lan-ip", ip))
    return toks


PUBLIC_OK = os.path.join(ROOT, "ops", "opsec_public.json")


def _sha(v):
    import hashlib
    return hashlib.sha256(str(v).strip().lower().encode("utf-8")).hexdigest()


def public_by_choice(path=PUBLIC_OK):
    """Values he publishes on purpose (his contact address is also his tailnet's name).
    Kept as sha256 of the lowercased value, so this tracked list republishes nothing."""
    try:
        return {e["sha256"] for e in json.load(open(path, encoding="utf-8")).get("public", [])}
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def gather(root=ROOT, status=None, system=True, public=None):
    toks = tokens_from_tailscale(tailscale_status() if status is None else status) + tokens_from_files(root)
    if system:
        toks += tokens_from_system()
    public = public_by_choice() if public is None else public
    seen, out = set(), []
    for cat, v in toks:
        if v and v not in seen and _sha(v) not in public:
            seen.add(v)
            out.append((cat, v))
    # longest first, so a DNS name is replaced before the device label inside it
    return sorted(out, key=lambda t: -len(t[1]))


def _pattern(cat, v):
    if cat.endswith("-ip"):
        # Only a neighbouring digit (or hex digit, for IPv6) makes it a different address.
        # peer_<ip>_5001 and <ip>:5001 are the same address -- an earlier \w/: boundary
        # missed both, found when a second count disagreed with the first (2026-09-26).
        if ":" in v:
            return re.compile(r"(?<![0-9A-Fa-f:])" + re.escape(v) + r"(?![0-9A-Fa-f:])")
        return re.compile(r"(?<![\d.])" + re.escape(v) + r"(?!\d|\.\d)")
    if cat in ("private-person", "device-name", "wifi-name", "tailnet-name"):
        return re.compile(r"(?<![A-Za-z0-9])" + re.escape(v) + r"(?![A-Za-z0-9])", re.I)
    return re.compile(re.escape(v))


def scan_text(text, toks):
    """[(line_no, category, masked_value)] for every token found."""
    pats = [(c, v, _pattern(c, v)) for c, v in toks]
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for c, v, p in pats:
            if p.search(line):
                hits.append((n, c, mask(v)))
    return hits


def fix_text(text, toks):
    for c, v in toks:
        text = _pattern(c, v).sub(LABEL[c], text)
    return text


def tracked(root=ROOT):
    out = _run(["git", "-C", root, "ls-files", "-z"], timeout=60)
    return [f for f in out.split("\0") if f]


def scan_tree(root=ROOT, toks=None, files=None):
    toks = gather(root) if toks is None else toks
    report = {}
    for f in (tracked(root) if files is None else files):
        p = os.path.join(root, f)
        try:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        hits = scan_text(text, toks)
        if hits:
            report[f] = hits
    return report


def fix_tree(root=ROOT, toks=None, files=None, say=print):
    toks = gather(root) if toks is None else toks
    fixed, left = {}, {}
    for f, hits in scan_tree(root, toks, files).items():
        if not f.lower().endswith(FIX_EXT):
            left[f] = hits
            continue
        p = os.path.join(root, f)
        with open(p, encoding="utf-8", newline="") as fh:
            text = fh.read()
        new = fix_text(text, toks)
        if new != text:
            tmp = p + ".opsec.tmp"
            with open(tmp, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)
            os.replace(tmp, p)
            fixed[f] = len(hits)
    say("opsec --fix: %d record/doc file(s) rewritten (%d line hits); %d code/config file(s) left for a person"
        % (len(fixed), sum(fixed.values()), len(left)))
    return fixed, left


ZERO = "0" * 40


def added_lines(root, rng):
    """[(commit, file, line_text)] for every line the commits in rng add, plus their messages."""
    # %w(0,4,4)%B prints the message indented four spaces -- a bare --format prints no
    # message at all, which OS1f caught the first time it ran.
    out = _run(["git", "-C", root, "log", "-p", "-U0", "--no-color", "--no-ext-diff",
                "--format=@@@COMMIT %H%n%w(0,4,4)%B", *rng], timeout=120)
    rows, commit, f = [], "?", "?"
    for line in out.splitlines():
        if line.startswith("@@@COMMIT "):
            commit, f = line[10:17], "(message)"
            continue
        if line.startswith("+++ "):
            f = line[6:] if line.startswith("+++ b/") else line[4:]
            continue
        if line.startswith("+") and not line.startswith("+++"):
            rows.append((commit, f, line[1:]))
        elif f == "(message)" and line.startswith("    "):
            rows.append((commit, f, line[4:]))
    return rows


def pre_push(stdin_lines, root=ROOT, toks=None, env=None, say=print):
    env = os.environ if env is None else env
    toks = gather(root) if toks is None else toks
    if not toks:
        say("opsec pre-push: NOT MEASURED -- none of his private sources exist on this machine; nothing of his to check for")
        return 0
    pats = [(c, v, _pattern(c, v)) for c, v in toks]
    hits = []
    for raw in stdin_lines:
        parts = raw.split()
        if len(parts) != 4 or parts[1] == ZERO:
            continue
        local, remote = parts[1], parts[3]
        rng = [local, "--not", "--remotes"] if remote == ZERO else ["%s..%s" % (remote, local)]
        for commit, f, text in added_lines(root, rng):
            for c, v, p in pats:
                if p.search(text):
                    hits.append((commit, f, c, mask(v)))
    if not hits:
        say("opsec pre-push: %d of his identifiers checked against every added line; none found" % len(toks))
        return 0
    say("opsec pre-push: REFUSED -- the push would publish %d of his identifier(s):" % len(hits))
    for commit, f, c, m in hits[:30]:
        say("  %s %s  %s %s" % (commit, f, c, m))
    if str(env.get("COVENANT_OPSEC_ALLOW", "")) == "1":
        os.makedirs(os.path.dirname(OVERRIDES), exist_ok=True)
        with open(OVERRIDES, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": int(time.time()), "hits": [list(h) for h in hits[:30]]}) + "\n")
        say("opsec pre-push: COVENANT_OPSEC_ALLOW=1 -- let through on his say, and logged")
        return 0
    say("Nothing was lost: the commit is still here. Remove the value (python tools/opsec_scan.py --fix does records"
        " and docs), amend or add a commit, and push again.")
    return 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--pre-push" in argv:
        return pre_push(sys.stdin.read().splitlines())
    toks = gather()
    cats = sorted({c for c, _ in toks})
    print("opsec: %d identifier(s) read from private sources (%s)" % (len(toks), ", ".join(cats) or "NONE -- NOT MEASURED"))
    if "--fix" in argv:
        _fixed, left = fix_tree(toks=toks)
        rep = left
    else:
        rep = scan_tree(toks=toks)
    for f, hits in sorted(rep.items()):
        kinds = sorted({c for _n, c, _m in hits})
        print("  %-48s %3d line(s)  %s  e.g. line %d" % (f, len(hits), ",".join(kinds), hits[0][0]))
    print("opsec: %d file(s) %s" % (len(rep), "left for a person (code/config)" if "--fix" in argv else "carry his identifiers"))
    return 1 if rep else 0


if __name__ == "__main__":
    sys.exit(main())
