#!/usr/bin/env python3
"""Establish which of the A1-A46 second-operator audit findings are still real.

WHY THIS EXISTS. docs/KNOWN_ISSUES.md carries 128 A-items. The later ones state
their status in the heading (OPEN / DONE / RESOLVED). A1-A46 were written under
an older convention -- Evidence / Repro / Fix, where "Fix" is a PRESCRIPTION,
not a record that anyone carried it out. So for 46 findings, nine of them
labelled [blocker], the register cannot say whether the problem is still there.
Nine blockers of unknown status is worse than nine known ones.

WHAT THIS DOES. Re-tests each finding's own assertion against the tree as it is
now. It does NOT read the prose and believe it.

WHAT IT REFUSES TO DO. Guess. Every check returns one of:
    FIXED       -- the condition the finding describes is demonstrably gone
    STILL OPEN  -- the condition is demonstrably still present
    UNDETERMINED-- a static check cannot settle it (needs a fresh clone, a
                   running node, a second machine, or the operator's decision)
UNDETERMINED is a real answer here, not a failure. A checker that resolved all
46 from greps would be lying about the runtime ones, and this project has
already been bitten by a guard that reports success by construction (A74:
35 of 36 suspected guards were fake because they grepped source text instead
of running the code). These checks grep too -- so each one is written to test
a FILE-LEVEL fact that is genuinely file-level, and anything behavioural is
marked UNDETERMINED rather than dressed up.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) or "."

FIXED, OPEN, UNDET = "FIXED", "STILL OPEN", "UNDETERMINED"
PARTIAL = "PARTLY FIXED"
RESULTS = []


def rec(aid, verdict, why):
    RESULTS.append((aid, verdict, why))


def read(rel):
    p = os.path.join(HERE, rel)
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def exists(rel):
    return os.path.exists(os.path.join(HERE, rel))


def tracked(rel):
    """Is this path tracked by git? Returns None when git cannot answer."""
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                           cwd=HERE, capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except Exception:                                          # noqa: BLE001
        return None


def any_file_has(rels, needle):
    """(hits, missing_files) -- which named files contain needle."""
    hits, missing = [], []
    for rel in rels:
        t = read(rel)
        if t is None:
            missing.append(rel)
        elif needle in t:
            hits.append(rel)
    return hits, missing


# --------------------------------------------------------------- docs group
def check_genesis_docs():
    """A1 / A6 / A28: quick starts tell a joiner to --export-genesis over the
    canonical file."""
    rels = ["README.md", "DEPLOYMENT.md", "HANDOFF.md", "docs/DEPLOYMENT.md"]
    # A mention is not an instruction. HANDOFF.md:111 carries the string inside
    # a ~~strikethrough~~ annotated "superseded 2026-09-05" -- a correction
    # kept visible on purpose, which is this project's whole documentation
    # habit. An earlier version of this check reported that as the defect it
    # is the repair of. Only count a line that still TELLS someone to run it.
    hits, missing = [], []
    for rel in rels:
        t = read(rel)
        if t is None:
            missing.append(rel)
            continue
        live = [ln for ln in t.splitlines()
                if "--export-genesis" in ln
                and "~~" not in ln
                and not re.search(r"superseded|no longer|never mints|do not run",
                                  ln, re.I)]
        if live:
            hits.append(rel)
    # The findings name the README quick start as the path a joiner follows.
    # HANDOFF.md is in the prescribed fix too, but a joiner does not boot from
    # it -- so "only HANDOFF.md left" is a different state from "still in the
    # README", and collapsing them would overstate the danger and understate
    # the work already done.
    entry = [r for r in hits if r != "HANDOFF.md"]
    for aid in ("A1", "A6", "A28"):
        if entry:
            rec(aid, OPEN, "--export-genesis still on a joiner's path: %s"
                % ", ".join(entry))
        elif hits:
            rec(aid, PARTIAL,
                "gone from every joiner-facing doc; still in %s, which the "
                "prescribed fix also named" % ", ".join(hits))
        else:
            rec(aid, FIXED, "no --export-genesis in %s"
                % ", ".join(r for r in rels if r not in missing))


def check_export_refuses_overwrite():
    """A6/A28 second half: export_genesis must refuse to clobber."""
    for cand in ("covenant_unified_v8.py",):
        t = read(cand)
        if t is None:
            continue
        m = re.search(r"def export_genesis\b.*?(?=\ndef |\nclass )", t, re.S)
        if not m:
            rec("A28b", UNDET, "export_genesis not found in %s" % cand)
            return
        body = m.group(0)
        guards = ("exists(" in body and
                  re.search(r"refus|already exists|will not overwrite|FileExists",
                            body, re.I))
        rec("A28b", FIXED if guards else OPEN,
            "export_genesis %s an overwrite guard"
            % ("has" if guards else "still has no"))
        return
    rec("A28b", UNDET, "covenant_unified_v8.py not readable")


def check_partner_docs():
    """A3 (how to peer), A15 (what the gate does), A13 (staying in consensus),
    A11 (GitHub egress disclosure), A18 (PC runbook)."""
    partner = read("docs/PARTNER.md")
    if partner is None:
        for aid in ("A3", "A13", "A15", "A11"):
            rec(aid, OPEN, "docs/PARTNER.md does not exist")
    else:
        low = partner.lower()
        rec("A3", FIXED if ("peer" in low and "--peers" in partner) else OPEN,
            "PARTNER.md %s a concrete --peers instruction"
            % ("carries" if "--peers" in partner else "still lacks"))
        rec("A15", FIXED if ("held" in low and "gate" in low) else OPEN,
            "PARTNER.md %s what the gate does / what held means"
            % ("describes" if ("held" in low and "gate" in low) else "still omits"))
        rec("A13", FIXED if "consensus" in low else OPEN,
            "PARTNER.md %s a stay-in-consensus note"
            % ("has" if "consensus" in low else "lacks"))
        discloses = bool("github" in low and
                         re.search(r"egress|sent off|leaves your machine|"
                                   r"off-machine|to github", low))
        rec("A11", FIXED if discloses else OPEN,
            "PARTNER.md %s the GitHub egress disclosure%s"
            % ("carries" if discloses else "lacks",
               "" if discloses or "github" not in low
               else " (it mentions GitHub, but never says the text leaves the machine)"))
    rec("A18", FIXED if exists("docs/PARTNER_NODE.md") else OPEN,
        "docs/PARTNER_NODE.md %s" % ("exists" if exists("docs/PARTNER_NODE.md")
                                     else "does not exist"))


def check_unison():
    """A17: UNISON.md claims the repo is private."""
    t = read("UNISON.md") or read("docs/UNISON.md")
    if t is None:
        rec("A17", FIXED, "UNISON.md no longer present")
        return
    claims_private = re.search(r"repositor\w+ is private|must stay private", t, re.I)
    rec("A17", OPEN if claims_private else FIXED,
        "UNISON.md %s the repo is private" % ("still says" if claims_private
                                              else "no longer says"))


def check_stop_section():
    """A14: no 'how to stop / remove' for the laptop and phone paths."""
    hits, missing = any_file_has(
        ["mobile/TERMUX_SETUP.md", "README.md", "docs/PARTNER.md"], "wake-unlock")
    stop = []
    for rel in ("mobile/TERMUX_SETUP.md", "README.md", "docs/PARTNER.md"):
        t = read(rel)
        # stop / stopping / remove / removing / uninstall. The first version
        # demanded \bstop\b and so missed a heading that reads "Stopping it,
        # and removing it" -- a check that only recognises one inflection of
        # the word it is looking for.
        if t and re.search(r"^#+.*\b(stop|stopping|remove|removing|removal|"
                           r"uninstall|uninstalling)\b", t, re.I | re.M):
            stop.append(rel)
    rec("A14", FIXED if stop else OPEN,
        "stop/remove heading in: %s" % (", ".join(stop) if stop else "none of the docs"))


def check_phone_docs():
    """A32 (bridge port off by one), A33 (three competing phone docs)."""
    t = read("mobile/TERMUX_SETUP.md")
    if t is None:
        rec("A32", UNDET, "mobile/TERMUX_SETUP.md not found")
    else:
        rec("A32", FIXED if "5011" in t else OPEN,
            "TERMUX_SETUP.md %s port 5011" % ("names" if "5011" in t else "does not name"))
    stale = [p for p in ("INDEX.md", "PHONE_NODE.md", "phone/PHONE_SETUP.md")
             if exists(p)]
    if not stale:
        rec("A33", FIXED, "the competing phone docs are gone")
    else:
        marked = []
        for p in stale:
            t = read(p) or ""
            if re.search(r"historical|superseded|obsolete|do not use", t[:2000], re.I):
                marked.append(p)
        rec("A33", FIXED if len(marked) == len(stale) else OPEN,
            "still present: %s; marked historical: %s"
            % (", ".join(stale), ", ".join(marked) or "none"))


def check_readme_ten_minutes():
    """A36: README calls the one-command check ten minutes; it is seconds."""
    t = read("README.md")
    if t is None:
        rec("A36", UNDET, "README.md not readable")
        return
    # The finding is specifically that the ONE-COMMAND CHECK is billed as ten
    # minutes when it takes seconds. The prescribed fix explicitly KEEPS a
    # ten-minute figure for the sweep. So a blanket search for "ten minutes"
    # convicts the corrected text -- which is what it did on the first run.
    head = re.search(r"^#+ .*one[ -]command.*$", t, re.I | re.M)
    if not head:
        rec("A36", UNDET, "no one-command heading found in README")
        return
    line = head.group(0)
    bad = re.search(r"(ten|10)[\s-]*minute", line, re.I)
    rec("A36", OPEN if bad else FIXED,
        "the one-command heading reads: %s" % line.strip().lstrip("# "))


# ------------------------------------------------------------- code group
def check_leet_repair():
    """A4 / A7: the in-word digit repair drops unmapped digits, so a hex 'root'
    hash mutates and the judge vetoes block 2."""
    found = None
    for rel in ("covenant_semantic_judge.py", "semantic_judge.py",
                "covenant_unified_v8.py"):
        t = read(rel)
        if t and "_LEET" in t:
            found = (rel, t)
            break
    if not found:
        rec("A4", UNDET, "_LEET table not located by name")
        rec("A7", UNDET, "_LEET table not located by name")
        return
    rel, t = found
    # The finding allowed EITHER remedy: a total mapping, or skipping
    # hex-looking tokens. An earlier version of this check tested only the
    # first, and only in the shape `_LEET.get(ch, ch)` -- so it reported a
    # live blocker against code that carries BOTH fixes, because the real key
    # is an `or` chain over regex groups. Testing one spelling of one of two
    # permitted fixes is not testing the finding.
    subscripted = re.search(r"_LEET\[", t)
    uses_get = re.search(r"_LEET\.get\(", t)
    hex_skip = re.search(r"_HEXTOKEN|hexdigits|is_hex", t)
    fixed = bool(uses_get and not subscripted) or bool(hex_skip)
    how = []
    if uses_get and not subscripted:
        how.append("_LEET.get() with a default, never subscripted")
    if hex_skip:
        how.append("hash-shaped tokens skipped outright")
    rec("A4", FIXED if fixed else OPEN,
        "%s: %s" % (rel, "; ".join(how) if how
                    else "neither remedy present -- digits still raise KeyError"))
    rec("A7", UNDET,
        "convergence is a two-node runtime fact; its static half (the digit "
        "repair) is %s" % ("fixed" if fixed else "open"))


def check_api_host():
    """A30 / A46: the API always binds 0.0.0.0."""
    for rel in ("covenant_unified_v8.py",):
        t = read(rel)
        if t is None:
            continue
        # This check used to be `"COVENANT_API_HOST" in t` -- the presence of a
        # STRING taken as proof of a behaviour. It marked A30 FIXED while the
        # node still bound 0.0.0.0 on every stock start, and stamped that
        # verdict into docs/KNOWN_ISSUES.md over a body that still read
        # "**Status:** open". That is the A74 fake-guard family, committed by
        # the tool built to find it. The finding is about the DEFAULT, so test
        # the default.
        has_opt = "COVENANT_API_HOST" in t
        default_open = bool(re.search(r'host:\s*str\s*=\s*"0\.0\.0\.0"', t))
        setters = []
        for _pat in ("*.bat", "*.ps1", "*.sh"):
            import glob as _glob
            for _f in _glob.glob(os.path.join(HERE, "**", _pat), recursive=True):
                if os.sep + ".venv" + os.sep in _f:
                    continue
                try:
                    if "COVENANT_API_HOST" in open(_f, encoding="utf-8",
                                                   errors="replace").read():
                        setters.append(os.path.relpath(_f, HERE))
                except OSError:
                    pass
        if not has_opt:
            rec("A30", OPEN, "%s has no host/bind option at all" % rel)
        elif default_open and not setters:
            rec("A30", PARTIAL,
                "COVENANT_API_HOST exists, but the default is still 0.0.0.0 and "
                "no launcher sets it -- a stock start binds every interface. The "
                "prescribed fix was default 127.0.0.1. NOTE: that default would "
                "cut off the phone node over Tailscale, so this is a real "
                "trade-off, not neglect -- the operator decides.")
        else:
            rec("A30", FIXED,
                "COVENANT_API_HOST exists; default_open=%s, launchers setting it: %s"
                % (default_open, ", ".join(setters) or "none"))
        rec("A46", UNDET,
            "endpoint disclosure depends on the bind decision above (%s) and on "
            "a live /health body" % ("host option present" if has_opt else "no host option"))
        return
    rec("A30", UNDET, "core file not readable")
    rec("A46", UNDET, "core file not readable")


def check_propose_code():
    """A31: /propose_code runs submitted code for an unauthenticated caller."""
    t = read("covenant_unified_v8.py")
    if t is None:
        rec("A31", UNDET, "core file not readable")
        return
    if "/propose_code" not in t:
        rec("A31", FIXED, "no /propose_code endpoint in the core")
        return
    m = re.search(r"PROTECTED_OPERATOR_ENDPOINTS\s*=\s*[\[{](.*?)[\]}]", t, re.S)
    guarded = bool(m and "propose_code" in m.group(1))
    rec("A31", FIXED if guarded else OPEN,
        "/propose_code %s in PROTECTED_OPERATOR_ENDPOINTS"
        % ("is" if guarded else "is NOT"))


def check_peers_parsing():
    """A41: --peers splits on every colon, so host:port with extra colons dies."""
    t = read("covenant_unified_v8.py")
    if t is None:
        rec("A41", UNDET, "core file not readable")
        return
    safe = re.search(r'rsplit\(\s*["\']:["\']\s*,\s*1\s*\)', t)
    rec("A41", FIXED if safe else OPEN,
        "peer parsing %s rsplit(':', 1)" % ("uses" if safe else "does not use"))


def _runtime_rows_added():
    """Do the newly appended corpus rows come from a NON-shareable source?

    "The tracked file is dirty" is not the harm. A20 is about RUNTIME judging
    dirtying it; the teacher appending shareable rows is what the membrane
    routes there on purpose. The first version of this check saw 37 new rows
    from `generated+judged` -- the teacher -- and reported A20 open. Dirty and
    dirty-from-runtime are different counts, and conflating them is the same
    units error this tool exists to catch.

    Unknown sources are treated as NOT runtime: a check should not convict on
    a row it could not read."""
    try:
        r = subprocess.run(["git", "diff", "--unified=0", "--", "ops/verdicts.jsonl"],
                           cwd=HERE, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return False
        try:
            sys.path.insert(0, HERE)
            import covenant_judge_defer as D
            shareable = set(getattr(D, "SHAREABLE_SOURCES", ()) or ())
        except Exception:                                        # noqa: BLE001
            shareable = {"generated+judged", "github", "study", "seed"}
        for line in (r.stdout or "").splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            try:
                src = json.loads(line[1:]).get("source")
            except ValueError:
                continue
            if src and src not in shareable:
                return True
    except Exception:                                            # noqa: BLE001
        return False
    return False


def check_verdicts_tracked():
    """A20: runtime verdicts append to a TRACKED file, so git pull --ff-only
    aborts and the node can never update."""
    # This used to ask "is ops/verdicts.jsonl tracked?" and report OPEN if so.
    # That is a PROXY, and the wrong one: the file is tracked ON PURPOSE -- it
    # is the teacher's corpus and part of the delivery. The finding's actual
    # harm is that RUNTIME judging appends to it, dirtying a tracked file so a
    # node can never `git pull --ff-only` again. Test the harm.
    #
    # covenant_judge_defer.py's MEMBRANE (2026-09-11) routes by source:
    # shareable corpus rows to the tracked ledger, everything a live node
    # decides to ops/verdicts_live.jsonl, which .gitignore covers. Measured
    # 2026-09-17 with three nodes judging: tracked file CLEAN, live file 164
    # rows. The check reported OPEN for six days against a fix that worked.
    defer = read("covenant_judge_defer.py") or ""
    has_membrane = "verdicts_live.jsonl" in defer
    ignored = tracked("ops/verdicts_live.jsonl")
    dirty = None
    try:
        r = subprocess.run(["git", "status", "--porcelain", "ops/verdicts.jsonl"],
                           cwd=HERE, capture_output=True, text=True, timeout=30)
        dirty = bool((r.stdout or "").strip()) if r.returncode == 0 else None
    except Exception:                                          # noqa: BLE001
        dirty = None

    if not has_membrane:
        rec("A20", OPEN, "no separate runtime ledger: covenant_judge_defer.py "
                         "does not mention verdicts_live.jsonl")
    elif ignored:
        rec("A20", OPEN, "the runtime ledger exists but is TRACKED, so it "
                         "dirties the tree exactly like the corpus did")
    elif dirty and _runtime_rows_added():
        rec("A20", OPEN, "ops/verdicts.jsonl carries newly appended rows whose "
                         "source is NOT shareable -- runtime judging is reaching "
                         "the tracked corpus")
    elif dirty:
        rec("A20", FIXED,
            "runtime rows go to ops/verdicts_live.jsonl (gitignored). The "
            "tracked corpus IS dirty, but every appended row is a shareable "
            "TEACHER row, which is what the membrane routes there on purpose")
    else:
        rec("A20", FIXED,
            "runtime rows go to ops/verdicts_live.jsonl (gitignored); the "
            "tracked corpus is %s, so `git pull --ff-only` survives judging"
            % ("clean" if dirty is False else "not reported dirty"))


def check_fallback_model_committed():
    """A26: the student a clone receives is not the one the nodes run."""
    t = tracked("fallback_model.json")
    if t is None:
        rec("A26", UNDET, "git could not answer")
    elif t:
        rec("A26", FIXED, "fallback_model.json is tracked (a clone gets a student)")
    else:
        rec("A26", OPEN, "fallback_model.json is NOT tracked; a clone gets none")


def check_github_rung():
    """A21 / A43: the node runs `git credential fill` and dispatches on the
    owner's repo when the local judge is down."""
    pol = read("ops/quorum_policy.json")
    if pol is None:
        rec("A43", UNDET, "ops/quorum_policy.json not readable")
    else:
        try:
            data = json.loads(pol)
            flat = json.dumps(data)
        except ValueError:
            flat = pol
        m = re.search(r'"github_when_local_down"\s*:\s*(true|false)', flat)
        if not m:
            rec("A43", FIXED, "github_when_local_down no longer in the tracked policy")
        else:
            rec("A43", FIXED if m.group(1) == "false" else OPEN,
                "tracked policy has github_when_local_down=%s" % m.group(1))
    hits, _ = any_file_has(
        ["covenant_github_judge.py", "covenant_unified_v8.py"], "credential fill")
    if not hits:
        rec("A21", FIXED, "no implicit `git credential fill` call found")
    else:
        opt_in, _ = any_file_has(hits, "COVENANT_GITHUB_JUDGE")
        rec("A21", FIXED if opt_in else OPEN,
            "`git credential fill` in %s; explicit opt-in %s"
            % (", ".join(hits), "present" if opt_in else "ABSENT"))


def check_key_acl():
    """A44: NTFS ignores 0o600, so the key is readable."""
    hits, _ = any_file_has(
        ["covenant_unified_v8.py", "ops/owner_only.py"], "require_owner_only")
    wired = "covenant_unified_v8.py" in hits
    rec("A44", FIXED if wired else OPEN,
        "require_owner_only %s wired into the core key path"
        % ("is" if wired else "is NOT"))


def check_p2p_rate_limit():
    """A45: the raw P2P listener has no rate limiter."""
    t = read("covenant_unified_v8.py")
    if t is None:
        rec("A45", UNDET, "core file not readable")
        return
    rec("A45", UNDET,
        "RateLimiter is %s in the core, but whether the P2P ACCEPT path uses it "
        "is a call-graph fact a grep cannot settle"
        % ("present" if "RateLimiter" in t else "absent"))


def check_genesis_mismatch_guard():
    """A27: a self-minted genesis persists silently forever."""
    t = read("covenant_unified_v8.py")
    if t is None:
        rec("A27", UNDET, "core file not readable")
        return
    m = re.search(r"def load_canonical_genesis\b.*?(?=\ndef |\nclass )", t, re.S)
    if not m:
        rec("A27", UNDET, "load_canonical_genesis not found")
        return
    body = m.group(0)
    guards = re.search(r"mismatch|refus|does not match|!=", body)
    rec("A27", FIXED if guards else OPEN,
        "load_canonical_genesis %s a mismatch check"
        % ("has" if guards else "has no"))


# ------------------------------------------- findings a grep cannot settle
RUNTIME_ONLY = {
    "A2":  "needs a fresh clone booted by the README path to see what the gate does",
    "A5":  "needs a PC without Ollama, peering",
    "A8":  "an address/reachability fact about the owner's network, not the tree",
    "A9":  "a REMOTE git-history fact -- measure the remote, never git log "
           "(see memory: public-repo-portfolio-exposure, closed 2026-09-12)",
    "A10": "needs DEPLOYMENT.md read against the 7 named commands, one by one",
    "A12": "needs the phone doc's tier table compared against the running seat",
    "A16": "an editorial decision about HANDOFF.md / LAUNCH.md",
    "A19": "needs a real second peer to stay peered across a watchdog round",
    "A22": "needs three live status surfaces compared on a fresh node",
    "A23": "needs /health on a fresh keyless node",
    "A24": "a timing fact (7.6 s measured) -- needs the probe path timed",
    "A25": "needs both seats judging the same held-band transaction",
    "A29": "needs a running node and a scripted peer add",
    "A34": "needs /health on the owner's own node",
    "A35": "needs a partner log with an unjudged block",
    "A37": "a verdict fact -- needs the fresh-node gate run over the payloads",
    "A38": "needs the shipped kit booted",
    "A39": "needs boot output from a keyless node",
    "A40": "needs /health on the founder node",
    "A42": "needs /health polled at 0.5 Hz for ~40 s",
}


def main():
    check_genesis_docs()
    check_export_refuses_overwrite()
    check_partner_docs()
    check_unison()
    check_stop_section()
    check_phone_docs()
    check_readme_ten_minutes()
    check_leet_repair()
    check_api_host()
    check_propose_code()
    check_peers_parsing()
    check_verdicts_tracked()
    check_fallback_model_committed()
    check_github_rung()
    check_key_acl()
    check_p2p_rate_limit()
    check_genesis_mismatch_guard()
    for aid, why in RUNTIME_ONLY.items():
        rec(aid, UNDET, why)

    def key(row):
        m = re.match(r"A(\d+)", row[0])
        return (int(m.group(1)) if m else 999, row[0])

    RESULTS.sort(key=key)
    order = {OPEN: 0, UNDET: 1, FIXED: 2}
    counts = {OPEN: 0, PARTIAL: 0, UNDET: 0, FIXED: 0}
    for aid, verdict, why in RESULTS:
        counts[verdict] = counts.get(verdict, 0) + 1

    print("A1-A46 STATUS, re-tested against the tree (not read from prose)")
    print("=" * 78)
    for want in (OPEN, PARTIAL, UNDET, FIXED):
        rows = [r for r in RESULTS if r[1] == want]
        print("\n--- %s (%d) ---" % (want, len(rows)))
        for aid, _v, why in rows:
            print("  %-5s %s" % (aid, why))
    print("\n" + "=" * 78)
    print("STILL OPEN %d   PARTLY FIXED %d   UNDETERMINED %d   FIXED %d   (of %d checks)"
          % (counts[OPEN], counts[PARTIAL], counts[UNDET], counts[FIXED], len(RESULTS)))
    print("UNDETERMINED is an answer: those need a fresh clone, a running node,")
    print("a second machine, or a decision -- not a grep.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
