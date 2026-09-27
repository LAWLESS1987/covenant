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

--pre-push scans every OBJECT the push would send that the remote does not already hold:
file contents (read as UTF-8 and, where git would call the file binary, as UTF-16), commit
and tag text (message, author, committer, tagger), and every file and directory name. So a
value added and removed inside one push is still caught, because both versions would be
public. What the remote already holds is asked of the remote itself, plus this clone's
copies of that remote's branches, never another remote's. A hit refuses the push and names
path:line, masked. The commit stays local; nothing is lost. A push it cannot read (a line
from git that does not parse, objects git cannot list) is refused, not waved through.
COVENANT_OPSEC_ALLOW=1 lets one push through on his say, and the override is logged,
masked, to ops/opsec_overrides.jsonl (gitignored). Until 2026-09-26 (A231) it read diff text
from `git log -p`, and an adversarial review reproduced eight ways past that. The ways were
tag messages, non-branch refs, merges, UTF-16 and binary files, form feeds and bare CRs,
lines starting '++', file names, and a hook input read in the wrong code page.

WHAT IT CANNOT SEE, named:
  - a value from a source it does not read: an e-mail address typed into a chat, a person
    not listed in bystanders.txt, an account figure;
  - a value written in another form: octal, NAT64, full-width digits, base64, split across
    lines, compressed or encrypted inside a binary, a name with one of its inner letters
    escaped (a review reproduced that; no serializer here writes it);
  - a name of 3 to 5 characters stored alone between NUL bytes in a binary (shorter than
    the printable run a match there needs);
  - content that leaves by another channel than git objects: Git LFS uploads its files from
    its own hook (this repository uses no LFS);
  - anything already in public history, which only a history rewrite removes; and, after
    such a rewrite, history this clone still holds in stale copies of the remote's branches
    (fetch first).
On a machine with none of these sources it finds nothing and says NOT MEASURED rather than
"clean".
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

# The hook runs one copy of this tool for every worktree and may run it from a temporary copy; it names the main
# worktree -- where the private sources and the shared repository are -- in COVENANT_OPSEC_ROOT (A231).
ROOT = os.environ.get("COVENANT_OPSEC_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


UNREADABLE = []          # private sources that exist but could not be read, from the last tokens_from_files()


def _read_text(path):
    """A private source as text, however a Windows tool saved it: UTF-8/16/32 byte-order marks honoured, else
    UTF-8, else cp1252 (Set-Content's and open()'s default here). A BOM left on the first line of the bystander
    list made that name unmatchable, and a UTF-16 list read as NUL-riddled garbage; both passed silently
    (the review, 2026-09-26, A231). The BOM character is dropped wherever it sits."""
    with open(path, "rb") as fh:
        data = fh.read()
    for bom, enc in ((b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe\x00\x00", "utf-32"), (b"\x00\x00\xfe\xff", "utf-32"),
                     (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if data.startswith(bom):
            return data.decode(enc, "replace").replace("﻿", "")
    try:
        return data.decode("utf-8").replace("﻿", "")
    except UnicodeDecodeError:
        return data.decode("cp1252", "replace").replace("﻿", "")


def tokens_from_files(root=ROOT):
    toks = []
    del UNREADABLE[:]
    cfg = os.path.join(root, "ops", "syncthing", "config.xml")
    if os.path.isfile(cfg):
        for m in re.finditer(r'<device id="([A-Z2-7]{7}(?:-[A-Z2-7]{7}){7})"', _read_text(cfg)):
            toks.append(("syncthing-device-id", m.group(1)))
    heal = os.path.join(root, "ops", "heal.jsonl")
    if os.path.isfile(heal):
        for line in _read_text(heal).splitlines():
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
            walk(json.loads(_read_text(grant)))
        except ValueError:
            # Recorded, not passed over: every wallet and account id in it would silently drop out of the check,
            # and the guard would still say "none found" on the rest. The push guard refuses while this is set.
            UNREADABLE.append("ops/earn_grant.json (not valid JSON)")
    by = os.path.join(root, "private", "bystanders.txt")
    if os.path.isfile(by):
        for line in _read_text(by).splitlines():
            # strip() leaves zero-width characters: one pasted after a name made the name unmatchable (round 3)
            line = line.translate({0x200B: None, 0x200C: None, 0x200D: None, 0x2060: None, 0xFEFF: None, 0x00AD: None}).strip()
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
            return re.compile(r"(?<![0-9A-Fa-f:])" + re.escape(v) + r"(?![0-9A-Fa-f:])", re.I)
        return re.compile(r"(?<![\d.])" + re.escape(v) + r"(?!\d|\.\d)")
    if cat in ("private-person", "device-name", "wifi-name", "tailnet-name"):
        return re.compile(r"(?<![A-Za-z0-9])" + re.escape(v) + r"(?![A-Za-z0-9])", re.I)
    # Hex and DNS forms match in any case (2026-09-26, A231): a wallet written lower-case -- covenant_earn compares
    # addresses lower-cased -- or zero-padded into a log topic with no '0x' in front, and an IPv6 address in upper
    # case, all went through when these were matched exactly. 40 hex digits are never another value by chance.
    return re.compile(re.escape(_literal(cat, v)), re.I)


def _literal(cat, v):
    """The part of a value that every match contains: what _could_match looks for before running the regex."""
    return v[2:] if cat == "wallet-address" and v[:2].lower() == "0x" else v


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
    """{file: [(line, category, masked value)]} over tracked files, each read as BYTES through the same object
    scan the push guard uses: every encoding reading, the plain reading of names, and the file's own name. A file
    that was not strict UTF-8 used to be skipped whole, and OS1g still called the tree clean (round 2 of the
    review, 2026-09-26). Line 0 = a hit in the name, in a binary, or only in the plain reading."""
    toks = gather(root) if toks is None else toks
    pats = [(c, v, _pattern(c, v)) for c, v in toks]
    report = {}
    for f in (tracked(root) if files is None else files):
        try:
            with open(os.path.join(root, f), "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        hits = []
        for _sha, where, c, m in scan_objects([(ZERO, "blob", f, data)], pats):
            ln = re.search(r":(\d+)$", where)
            hits.append((int(ln.group(1)) if ln else 0, c, m))
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
        try:
            with open(p, encoding="utf-8", newline="") as fh:
                text = fh.read()
        except UnicodeDecodeError:
            left[f] = hits                       # not UTF-8: reported for a person, never rewritten blind
            continue
        new = fix_text(text, toks)
        if new == text:
            left[f] = hits                       # found only as written another way (escaped, curly): a person's
            continue
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
_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_REMOTE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
_BATCH = 400                                   # objects per cat-file call: memory stays bounded on a large push


def _zero(sha):
    return bool(sha) and set(sha) == {"0"}


# Every git read the guard makes: never prompt (a hook waiting on a terminal nobody sees hangs the push), and never
# follow refs/replace -- a local replacement made the reader see a clean stand-in while `git push`, which sends
# the original objects, published the commit it hid (measured 2026-09-26, A231: 0 hits read, the value on the remote).
_GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1")


def _run_ok(args, timeout=15, stdin=None):
    """(ok, stdout). Unlike _run, a failure is REPORTED, not turned into an empty answer: the push guard read
    'git printed nothing' as 'nothing was added', so a git that failed let the push through (2026-09-26, A231).
    Never prompts: a push hook that waits on a terminal nobody sees would hang the push."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", input=stdin,
                           timeout=timeout, creationflags=_NO_WINDOW, env=_GIT_ENV)
        return p.returncode == 0, p.stdout
    except (OSError, subprocess.SubprocessError):
        return False, ""


def _run_bytes(args, timeout=300, stdin=b""):
    """(ok, stdout bytes). Bytes, because text mode's universal newlines turn a bare CR into a line break and
    splitlines() breaks on form feeds and U+2028 -- both cut a line before the value, and the rest went unread."""
    try:
        p = subprocess.run(args, capture_output=True, input=stdin, timeout=timeout, creationflags=_NO_WINDOW,
                           env=_GIT_ENV)
        return p.returncode == 0, p.stdout
    except (OSError, subprocess.SubprocessError, MemoryError):
        return False, b""


def present(root, shas):
    """The given shas that name a commit (or tag) in this clone. An exclusion git cannot resolve would fail the
    whole read, so an unknown tip is dropped -- which widens what is checked, never narrows it."""
    shas = sorted({s for s in shas if s and _SHA.match(s) and not _zero(s)})
    if not shas:
        return []
    ok, out = _run_ok(["git", "-C", root, "cat-file", "--batch-check=%(objectname) %(objecttype)"], timeout=60,
                      stdin="".join(s + "\n" for s in shas))
    have = {p[0] for p in (ln.split() for ln in out.splitlines()) if len(p) == 2 and p[1] in ("commit", "tag")} if ok else set()
    return [s for s in shas if s in have]


def published(root, remote, name=None):
    """(tips, how): the tips of what the remote being pushed to ALREADY holds, as far as this clone has them.

    Two sources, both about THAT remote only:
      - the remote itself (git ls-remote): this clone's copies of its branches go stale or are missing (this
        clone had no origin/main on 2026-09-26). Counting from the old tip of the one ref being updated refused
        moving a branch onto commits main had published long before (the sentinel-witness push, 2026-09-26);
      - this clone's copies of that remote's branches (refs/remotes/<name>/*): they were on that remote when
        fetched, and they cover a clone that is BEHIND the remote, whose new tips it cannot resolve (without
        them, a clean new branch was refused for history the remote already held -- the review, same day).
    Never another remote's copies: a value already pushed to a private backup is not published on the public
    one (the first version of this function excluded every refs/remotes, and let that through). Nor copies
    FETCHED from somewhere other than where this push goes: with a pushurl set apart from the url, the copies
    came from the fetch side and prove nothing about the push side (round 2 of the review reproduced exactly
    that), so they count only when fetch url, push url and the url git handed the hook are one and the same.
    After a history rewrite on the remote, fetch before pushing: stale copies still name the old history."""
    tips, reached = [], False
    if remote:
        ok, out = _run_ok(["git", "-C", root, "ls-remote", remote], timeout=60)
        if ok:
            reached = True
            tips += [ln.split()[0] for ln in out.splitlines() if ln.split()]
    copies = bool(name and _REMOTE_NAME.match(name))
    if copies:
        f_ok, fetch_url = _run_ok(["git", "-C", root, "remote", "get-url", name])
        p_ok, push_url = _run_ok(["git", "-C", root, "remote", "get-url", "--push", name])
        norm = lambda u: u.strip().rstrip("/")  # noqa: E731
        copies = (f_ok and p_ok and norm(fetch_url) == norm(push_url)
                  and (not remote or remote == name or norm(remote) == norm(push_url)))
    if copies:
        ok, out = _run_ok(["git", "-C", root, "for-each-ref", "--format=%(objectname)", "refs/remotes/" + name])
        if ok:
            tips += out.split()
    how = ("asked the remote" if reached else "remote not reached") + (
        ", and this clone's copies of %s's branches" % name if copies else "")
    return present(root, tips), how


def outgoing(root, include, exclude=()):
    """[(sha, type, path, content)] for every object reachable from include and not from exclude: what the push
    would send. None when git could not list or read them -- the caller refuses; None is never 'nothing'.

    Objects, not diff text (2026-09-26, A231, after an adversarial review reproduced eight ways past `git log -p`):
    annotated tag messages (git log peels a tag to its commit), objects pushed to non-branch refs (git log of a
    blob prints nothing and succeeds), lines a merge adds (git log -p shows no merge diff), binary and UTF-16
    files ('Binary files differ'), lines cut at a form feed or bare CR, added lines starting with '++' (read as
    a '+++' header), and names of files. rev-list --objects lists every new commit, tree, blob and tag."""
    ok, out = _run_bytes(["git", "-C", root, "rev-list", "--objects", "--stdin"],
                         stdin=("".join(s + "\n" for s in include) + "".join("^" + s + "\n" for s in exclude)).encode())
    if not ok:
        return None
    listed = []
    for raw in out.split(b"\n"):
        if not raw:
            continue
        head, _sp, rest = raw.partition(b" ")
        h = head.decode("ascii", "replace")
        if _SHA.match(h):
            listed.append([h, rest.decode("utf-8", "replace")])
        elif listed:                                  # a path that itself held a newline
            listed[-1][1] += "\n" + raw.decode("utf-8", "replace")
        else:
            return None
    objs = []
    for k in range(0, len(listed), _BATCH):
        part = listed[k:k + _BATCH]
        ok, data = _run_bytes(["git", "-C", root, "cat-file", "--batch"], stdin="".join(s + "\n" for s, _p in part).encode())
        if not ok:
            return None
        i = 0
        for sha, path in part:
            nl = data.find(b"\n", i)
            hdr = data[i:nl].decode("ascii", "replace").split() if nl >= 0 else []
            if len(hdr) != 3 or hdr[0] != sha or not hdr[2].isdigit():      # 'missing', or out of step
                return None
            size, start = int(hdr[2]), nl + 1
            objs.append((sha, hdr[1], path, data[start:start + size]))
            i = start + size + 1
    return objs


def _decodings(kind, data):
    """[(text, binary)]: every reading of an object a person could see.
      - UTF-8, the default; and cp1252 when the bytes are not valid UTF-8 (open() with no encoding and
        PowerShell's Set-Content write cp1252 on this PC -- an accented name in one went through);
      - UTF-32 when it starts with a UTF-32 byte-order mark (its FF FE prefix was read as UTF-16 and missed);
      - UTF-16 both ways and at both byte offsets for a blob with NUL bytes or a UTF-16 mark (PowerShell 5.1's
        default; git calls such a file binary, and a value in one went through).
    `binary` marks a reading of NUL-containing bytes, where only matches inside printable text count. Commit and
    tag text are read the same way: a message stored under an 'encoding UTF-16' header is NUL-riddled too."""
    binary = b"\x00" in data
    if data.startswith(b"\xff\xfe\x00\x00") or data.startswith(b"\x00\x00\xfe\xff"):
        return [(data.decode("utf-32", "replace"), False), (data.decode("utf-8", "replace"), True)]
    out = []
    try:
        out.append((data.decode("utf-8"), binary))
    except UnicodeDecodeError:
        out += [(data.decode("utf-8", "replace"), binary), (data.decode("cp1252", "replace"), binary)]
    if binary or data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        for enc in ("utf-16-le", "utf-16-be"):
            out += [(data.decode(enc, "replace"), True), (data[1:].decode(enc, "replace"), True)]
    return out


_PLAIN_MAP = {0x2018: "'", 0x2019: "'", 0x02BC: "'", 0x2032: "'", 0x00B4: "'", 0x2010: "-", 0x2011: "-",
              0x2012: "-", 0x2013: "-", 0x00A0: " ", 0x2007: " ", 0x202F: " ", 0x00AD: None, 0x200B: None,
              0x200C: None, 0x200D: None, 0x2060: None, 0xFEFF: None}
_UESC = re.compile(r"\\u([0-9a-fA-F]{4})")


def _plain(text):
    """The same text as a reader sees it: JSON \\u escapes decoded (json.dumps writes every non-ASCII character
    that way by default -- 654 json.dumps lines here, 79 of them ensure_ascii=False), HTML entities decoded, NFKC,
    curly apostrophes and non-breaking hyphens and spaces made plain, invisible characters dropped, and a quoted
    apostrophe (\\' or '') collapsed. A name written through any of these went through (the review, 2026-09-26)."""
    import html
    import unicodedata
    s = _UESC.sub(lambda m: chr(int(m.group(1), 16)), text)
    s = s.encode("utf-16", "surrogatepass").decode("utf-16", "replace")          # rejoin escaped surrogate pairs
    s = unicodedata.normalize("NFKC", html.unescape(s)).translate(_PLAIN_MAP)
    return s.replace("\\'", "'").replace("''", "'")


_NAMELIKE = ("private-person", "device-name", "wifi-name", "tailnet-name", "tailnet-dns-name")


def _anchor(v):
    """The longest run of 3+ ASCII letters or digits in a value: every written form of a name keeps it, so the
    plain reading is computed only for a text that contains it."""
    runs = re.findall(r"[A-Za-z0-9]{3,}", v)
    return max(runs, key=len) if runs else None


def _printable_run(text, a, b):
    """Length of the run of printable characters around text[a:b] (U+FFFD, controls and NUL end a run)."""
    ok = lambda ch: ch.isprintable() and ch != "�"  # noqa: E731
    while a > 0 and ok(text[a - 1]):
        a -= 1
    while b < len(text) and ok(text[b]):
        b += 1
    return b - a


def _tree_names(data, sha):
    """The entry names of a raw tree object (a rename changes only these: the blob is the same object)."""
    names, i, n = [], 0, 20 if len(sha) == 40 else 32
    while i < len(data):
        sp = data.find(b" ", i)
        nul = data.find(b"\0", sp + 1) if sp >= 0 else -1
        if sp < 0 or nul < 0:
            break
        names.append(data[sp + 1:nul].decode("utf-8", "replace"))
        i = nul + 1 + n
    return names


def _masked(text, pats):
    """A path or name as it may be printed and logged: every value in it masked (the review found raw names in
    the override log)."""
    for _c, v, p in pats:
        text = p.sub(lambda _m, v=v: mask(v), text)
    return text


_FOLD = {0x131: "i", 0x130: "i", 0x17F: "s", 0x212A: "k", 0x212B: "å"}


def _fold(s):
    """A case fold at least as loose as re.IGNORECASE: measured over every code point (2026-09-26), no character
    that re.I matches to an ASCII letter, or to its own upper case, folds apart under this. Used only to SKIP a
    regex that could not match, so it may be looser than the regex, never stricter. ASCII text takes the fast
    path: translate() did nothing there and cost 39 of 66 seconds over the whole history (the review)."""
    return s.casefold() if s.isascii() else s.translate(_FOLD).casefold()


def _could_match(text, lit, p, folded):
    """False only when p cannot match text: every pattern is a literal inside boundaries. Without this, 43
    patterns over the whole history (5728 objects, 277 MB) took 416 s; a first push would have hung."""
    if p.flags & re.I:
        if folded[0] is None:
            folded[0] = _fold(text)
        return _fold(lit) in folded[0]
    return lit in text


def scan_objects(objs, pats):
    """[(sha7, where, category, masked value)] for every value in every object: blob contents (with line
    numbers; byte-offset-like positions in binaries), commit and tag text (message, author, committer, tagger),
    tree entry names, object paths, and for names the plain reading of each text (_plain)."""
    hits, seen = [], set()
    lits = [(c, v, p, _literal(c, v)) for c, v, p in pats]
    plains = [(c, v, re.compile(p.pattern.replace(re.escape(v), re.escape(_plain(v))), p.flags), _anchor(v))
              for c, v, p in pats if c in _NAMELIKE and _anchor(v)]

    def hit(sha, where, c, v):
        key = (sha, where, c, v)
        if key not in seen:
            seen.add(key)
            hits.append((sha[:7], _masked(where, pats), c, mask(v)))

    def scan(sha, text, binary, where):
        """where(match_start or None) -> the location printed for a hit in this text."""
        folded = [None]
        for c, v, p, lit in lits:
            if not _could_match(text, lit, p, folded):
                continue
            # In NUL-containing bytes a match counts only inside printable text: 8 characters of it, or the whole
            # value when that is 6 or longer -- a device name stored alone between NULs (a C string) still counts,
            # while a 3-letter name met by chance inside compressed bytes does not (rounds 2 and 3 of the review).
            need = 8 if len(v) < 6 else min(8, len(v))
            for m in p.finditer(text):
                if binary and _printable_run(text, m.start(), m.end()) < need:
                    continue
                hit(sha, where(m.start()), c, v)
        if binary or not plains:
            return
        if folded[0] is None:
            folded[0] = _fold(text)
        live = [(c, v, pp) for c, v, pp, a in plains if _fold(a) in folded[0]]
        if live:
            plain = _plain(text)
            if plain != text:
                for c, v, pp in live:
                    if pp.search(plain):
                        hit(sha, where(None) + " (as written: escaped, curly or accented)", c, v)

    for sha, kind, path, data in objs:
        if path:
            scan(sha, path, False, lambda _i, path=path: "(path) " + path)
        if kind == "tree":
            for name in _tree_names(data, sha):
                scan(sha, name, False, lambda _i, name=name, path=path: "(name in %s) %s" % (path or "/", name))
            continue
        for text, binary in _decodings(kind, data):
            if kind != "blob":
                scan(sha, text, binary, lambda _i, kind=kind: "(%s)" % kind)
            elif binary:
                scan(sha, text, True, lambda i, path=path: "%s@%s" % (path or "(blob)", "?" if i is None else i))
            else:
                scan(sha, text, False, lambda i, path=path, text=text: "%s:%s" % (
                    path or "(blob)", "?" if i is None else text.count("\n", 0, i) + 1))
    return hits


def parse_push_lines(data):
    """(refs, unparsed) from the bytes git writes to a pre-push hook: '<local ref> <local sha> <remote ref>
    <remote sha>', one per line. UTF-8, never the console code page: read as cp1252, a branch named with U+00E0
    split into five fields, the line was dropped, and nothing was checked (the review, 2026-09-26). A line that
    does not parse is returned so the caller refuses; a deletion (local sha all zeros) carries nothing."""
    text = data.decode("utf-8", "surrogateescape") if isinstance(data, bytes) else data
    refs, unparsed = [], []
    for raw in text.split("\n"):
        raw = raw.rstrip("\r")
        if not raw.strip():
            continue
        p = raw.rsplit(" ", 3)        # from the right: the local side is written as typed, and may hold a space
        # (':/fix typo:refs/heads/x', 'main@{1 hour ago}:snap' were refused as unreadable -- round 2 of the review)
        if len(p) != 4 or not _SHA.match(p[1]) or not _SHA.match(p[3]):
            unparsed.append(raw[:120])
        elif not _zero(p[1]):
            refs.append(p)
    return refs, unparsed


def pre_push(stdin_lines, root=ROOT, toks=None, env=None, say=print, remote=None, remote_name=None):
    """0 to let the push through, 1 to refuse. git gives the hook the remote's name and its url: `remote` is the
    url (or the name), `remote_name` the name (taken from `remote` when that is a plain name).

    What is checked: every object the push would send that the remote does not already hold (published()) --
    blob contents, commit and tag text, tree entry names, paths. Fails CLOSED: an old tip this clone does not
    have is not trusted as an exclusion; a push line that does not parse, or objects git could not list or read,
    refuse the push rather than read as 'nothing added' (all three failed open until 2026-09-26, A231)."""
    env = os.environ if env is None else env
    unreadable = []
    if toks is None:
        toks = gather(root)
        unreadable = list(UNREADABLE)             # a source that exists but could not be read: not 'nothing of his'
    if not toks and not unreadable:
        say("opsec pre-push: NOT MEASURED -- none of his private sources exist on this machine; nothing of his to check for")
        return 0
    pats = [(c, v, _pattern(c, v)) for c, v in toks]
    if remote_name is None and remote and _REMOTE_NAME.match(remote):
        remote_name = remote
    refs, unparsed = parse_push_lines("\n".join(stdin_lines))
    tips, how = published(root, remote, remote_name) if refs else ([], "")
    hits, unread, commits, done = [], [], set(), set()
    for parts in refs:
        objs = outgoing(root, [parts[1]], sorted(set(tips) | set(present(root, [parts[3]]))))
        if objs is None:
            unread.append(parts[2])
            continue
        objs = [o for o in objs if o[0] not in done]   # branches sharing history are read once, not once each
        done.update(o[0] for o in objs)
        commits.update(sha for sha, kind, _p, _d in objs if kind == "commit")
        hits += scan_objects(objs, pats)
    if not hits and not unread and not unparsed and not unreadable:
        say("opsec pre-push: %d of his identifiers checked against every object %d outgoing commit(s) bring -- the "
            "ones the remote does not already hold (%s); none found" % (len(toks), len(commits), how))
        return 0
    if unreadable:
        say("opsec pre-push: REFUSED -- NOT MEASURED: a private source exists but could not be read, so what it "
            "holds is not being checked: %s" % "; ".join(unreadable))
    if unparsed:
        say("opsec pre-push: REFUSED -- NOT MEASURED: git's list of what is being pushed could not be read: %s"
            % "; ".join(_masked(u, pats) for u in unparsed[:3]))
    if unread:
        say("opsec pre-push: REFUSED -- NOT MEASURED: the outgoing objects of %s could not be read (git failed or "
            "timed out), and a push that cannot be checked is not let through" % ", ".join(_masked(u, pats) for u in unread))
    if hits:
        say("opsec pre-push: REFUSED -- the push would publish %d of his identifier(s) (%s):" % (len(hits), how))
    for sha, where, c, m in hits[:30]:
        say("  %s %s  %s %s" % (sha, where, c, m))
    if str(env.get("COVENANT_OPSEC_ALLOW", "")) == "1":
        os.makedirs(os.path.dirname(OVERRIDES), exist_ok=True)
        with open(OVERRIDES, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": int(time.time()), "hits": [list(h) for h in hits[:30]],
                                 "unread": [_masked(u, pats) for u in unread], "unreadable": unreadable,
                                 "unparsed": [_masked(u, pats) for u in unparsed[:3]]}) + "\n")
        say("opsec pre-push: COVENANT_OPSEC_ALLOW=1 -- let through on his say, and logged")
        return 0
    say("Nothing was lost: the commit is still here. Remove the value (python tools/opsec_scan.py --fix does records"
        " and docs), amend or add a commit, and push again. If it is in history the remote already has, fetch"
        " first: this clone may be behind." if hits else
        "Nothing was lost. Repair the private source named above (a BOM or a stray comma is enough), then push again."
        if unreadable else
        "Nothing was lost. Push again; if the read keeps failing, COVENANT_OPSEC_ALLOW=1 is his, for one push.")
    return 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    for stream in (sys.stdout, sys.stderr):
        # A pipe here is cp1252: one path outside it crashed the report before the override was read, turning an
        # allowed push into a traceback (round 2 of the review). Unprintable characters are escaped, never fatal.
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    if "--pre-push" in argv:
        rest = argv[argv.index("--pre-push") + 1:]          # git passes the hook: <remote name> <remote url>
        raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
        return pre_push(raw.decode("utf-8", "surrogateescape").split("\n"),
                        remote=(rest[1] if len(rest) > 1 else rest[0] if rest else None),
                        remote_name=(rest[0] if rest else None))
    toks = gather()
    cats = sorted({c for c, _ in toks})
    print("opsec: %d identifier(s) read from private sources (%s)" % (len(toks), ", ".join(cats) or "NONE -- NOT MEASURED"))
    for u in UNREADABLE:
        print("opsec: NOT MEASURED -- a private source could not be read: %s" % u)
    if "--fix" in argv:
        _fixed, left = fix_tree(toks=toks)
        rep = left
    else:
        rep = scan_tree(toks=toks)
    for f, hits in sorted(rep.items()):
        kinds = sorted({c for _n, c, _m in hits})
        print("  %-48s %3d line(s)  %s  e.g. line %d" % (f, len(hits), ",".join(kinds), hits[0][0]))
    print("opsec: %d file(s) %s" % (len(rep), "left for a person (code/config)" if "--fix" in argv else "carry his identifiers"))
    return 1 if rep or UNREADABLE else 0


if __name__ == "__main__":
    sys.exit(main())
