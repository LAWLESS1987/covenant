"""test_p18_version_collision.py -- P18 (v8.39): TWO SOURCES MAY NOT CLAIM THE
SAME VERSION. A version string that does not identify one set of bytes is not
an identifier, it is a rumour.

WHAT HAPPENED, 2026-08-26, and it is the reason this file exists.
Two runs branched from v8.37 within half an hour of each other and both called
their result v8.38:

    covenant_unified_v8.py                   6ddedcdc7c6b  9969 lines  A24 fix
    covenant_unified_v8.PENDING-v8.38.py     27264e46218d  9894 lines  semantic judge

Neither knew about the other. The second run's own log entry states, correctly
and uselessly, that "the live core on disk is untouched at v8.37" -- correct,
because it was comparing hashes; useless, because the number it stamped on its
own output was already taken. This is the A12 double-fix of 2026-08-22 in a new
costume: the failure is not that two runs did different work, it is that the
NAME stopped distinguishing the results.

P11 (v8.31) exists so a node can say which source it is running. It made the
node self-describing and left the naming scheme unguarded: /health reports
`version` and `source_sha12` side by side, and nothing anywhere required them
to agree across the tree. A node reporting "v8.38" told an operator nothing at
all for the eighteen hours those two files coexisted.

THE RULE, and it is deliberately narrow so that it can never cry wolf (M34):

  V3  No other covenant_unified_v8*.py anywhere under the bundle root may
      declare the SAME COVENANT_VERSION as the live covenant_unified_v8.py
      unless it is byte-identical to it.
  V4  covenant_unified_v8.PRE-vX.Y.py must NOT declare version X.Y. That name
      means "the file that was here BEFORE X.Y"; a PRE- file declaring the
      version it is named for is a backup that was taken one step too late,
      which is how a rollback restores the thing it was meant to undo.

Archive-to-archive collisions are REPORTED and not failed: every file older
than v8.31 declares "v8.9-merged" because COVENANT_VERSION was referenced
nowhere before P11, so a global uniqueness rule would be red for ever on a
condition nobody can now fix. A permanent red is not one cost but two (M34).

Two properties of the checker itself, both asserted below:
  * It reads with the AST, never a regex over the text -- a version string in a
    comment or a docstring is prose, and prose is the thing this loop keeps
    finding wrong (M42).
  * It NEVER IMPORTS a candidate. A scanner that imports every copy of the core
    it finds in order to ask its version has executed every copy of the core it
    found, including the one somebody left in Downloads.

Pure file and AST work: no node, no socket, no key, no network. Runs in ~2 s on
any platform, so unlike most of this suite set it is not a Linux-only result
(M29/DE6).

Run: python3 test_p18_version_collision.py
"""
import os, sys, ast, json, hashlib, inspect, tempfile, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}", flush=True)


# ---------------------------------------------------------------------------
# The checker. Kept free of `check()` so it can be run against planted trees.
# ---------------------------------------------------------------------------
LIVE_NAME = "covenant_unified_v8.py"
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "logs",
             ".mypy_cache", ".pytest_cache", "realdata"}


def declared_version(path):
    """The module-level COVENANT_VERSION assignment, read from the AST.

    Returns the string, or None if the file has no such assignment. Never
    imports and never execs -- see the module docstring. A SyntaxError is
    reported as None rather than raised: this is a hygiene check and must not
    be the thing that stops a sweep.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            tree = ast.parse(fh.read(), filename=path)
    except (OSError, SyntaxError, ValueError):
        return None
    for node in tree.body:                      # module level only, by design
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "COVENANT_VERSION":
                    if isinstance(node.value, ast.Constant) and \
                            isinstance(node.value.value, str):
                        return node.value.value
    return None


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pre_version_from_name(name):
    """`covenant_unified_v8.PRE-v8.37.py` -> 'v8.37'; anything else -> None."""
    stem = name[:-3] if name.endswith(".py") else name
    marker = ".PRE-"
    i = stem.find(marker)
    if i < 0:
        return None
    tail = stem[i + len(marker):]
    return tail or None


def scan(root, max_depth=3):
    """Every covenant_unified_v8*.py under `root`, with version and hash."""
    root = os.path.abspath(root)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth >= max_depth:
            dirnames[:] = []
        for fn in filenames:
            if fn.startswith("covenant_unified_v8") and fn.endswith(".py"):
                p = os.path.join(dirpath, fn)
                found.append({"path": p,
                              "rel": os.path.relpath(p, root),
                              "name": fn,
                              "version": declared_version(p),
                              "sha256": sha256_of(p)})
    found.sort(key=lambda d: d["rel"])
    return found


def audit(root):
    """(live, collisions, mislabelled_backups, archive_collisions).

    collisions          -- files sharing the LIVE file's version, different bytes
    mislabelled_backups -- PRE-vX.Y files declaring X.Y
    archive_collisions  -- same version, different bytes, neither one live
    """
    files = scan(root)
    live = next((f for f in files if f["rel"] == LIVE_NAME), None)
    collisions, mislabelled = [], []
    for f in files:
        if live and f is not live and f["version"] == live["version"] \
                and f["sha256"] != live["sha256"]:
            collisions.append(f)
        pre = pre_version_from_name(f["name"])
        if pre and f["version"] == pre:
            mislabelled.append(f)
    by_ver = {}
    for f in files:
        if f["version"] and (not live or f["rel"] != LIVE_NAME):
            by_ver.setdefault(f["version"], set()).add(f["sha256"])
    archive_collisions = {v: sorted(h[:12] for h in hs)
                          for v, hs in by_ver.items() if len(hs) > 1}
    return live, collisions, mislabelled, archive_collisions


# ---------------------------------------------------------------------------
def plant(tmp, spec):
    """Write a miniature tree: {filename: (version_or_None, filler)}."""
    for name, (ver, filler) in spec.items():
        p = os.path.join(tmp, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        body = ["# planted fixture\n"]
        if ver is not None:
            body.append(f'COVENANT_VERSION = "{ver}"\n')
        body.append(f"FILLER = {filler!r}\n")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("".join(body))


# ---------------------------------------------------------------------------
def v1_live():
    """V1/V2 -- the live file, and P11's own contract re-asserted from outside."""
    here = os.path.dirname(os.path.abspath(__file__))
    live_path = os.path.join(here, LIVE_NAME)
    check("V1a the live core is present beside this suite",
          os.path.isfile(live_path), live_path)
    if not os.path.isfile(live_path):
        return
    ver = declared_version(live_path)
    check("V1b it declares a COVENANT_VERSION at module level",
          isinstance(ver, str) and ver.strip() != "", repr(ver))
    check("V1c the version is read from the AST, so a version in a COMMENT "
          "cannot satisfy this",
          declared_version.__doc__ is not None
          and "COVENANT_VERSION" in inspect.getsource(declared_version)
          and "ast.parse" in inspect.getsource(declared_version), "")

    digest = sha256_of(live_path)
    os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
    os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")
    import covenant_unified_v8 as cov
    check("V2a the module's own COVENANT_VERSION agrees with the file on disk",
          cov.COVENANT_VERSION == ver, f"{cov.COVENANT_VERSION} vs {ver}")
    check("V2b P11's fingerprint is the sha256 of THIS file's bytes "
          "(the 12-hex prefix -- see A25, the name says sha256 and the field "
          "holds twelve characters, which is the tested contract)",
          cov.CORE_SOURCE_SHA12 == digest[:12],
          f"{cov.CORE_SOURCE_SHA12} vs {digest[:12]}")
    check("V2c and it is not the empty/unavailable degradation",
          cov.CORE_SOURCE_SHA256 != "unavailable"
          and cov.CORE_SOURCE_UNREADABLE == "",
          repr(cov.CORE_SOURCE_UNREADABLE))


def v3_tree():
    """V3/V4/V5 -- the real tree this suite is sitting in."""
    here = os.path.dirname(os.path.abspath(__file__))
    live, collisions, mislabelled, archives = audit(here)
    files = scan(here)
    print(f"      scanned {len(files)} covenant_unified_v8*.py under {here}")
    for f in files:
        print(f"        {f['sha256'][:12]}  {str(f['version']):<14} {f['rel']}")
    check("V3 no other copy of the core claims the live version with "
          "different bytes",
          not collisions,
          "; ".join(f"{c['rel']}={c['sha256'][:12]}" for c in collisions))
    check("V4 no covenant_unified_v8.PRE-vX.Y.py declares version X.Y "
          "(a PRE- file is what was here BEFORE that version)",
          not mislabelled,
          "; ".join(f"{m['rel']} declares {m['version']}" for m in mislabelled))
    # Informational by design -- everything before P11 declares "v8.9-merged",
    # which cannot now be fixed and must not be a standing red (M34).
    if archives:
        print("      NOTE (not a failure) archive-to-archive version reuse: "
              + json.dumps(archives))
    check("V5 the archive report is produced whether or not it is empty",
          isinstance(archives, dict), f"{len(archives)} reused version(s)")


def v6_mutation():
    """V6-V9 -- MUTATION TESTS. A guard that has only ever seen a correct tree
    has never been tested (M31). Each plants the exact defect and requires the
    checker to report it, then removes it and requires silence."""
    tmp = tempfile.mkdtemp(prefix="p18_")
    try:
        plant(tmp, {
            "covenant_unified_v8.py": ("v8.39", "live"),
            "covenant_unified_v8.PRE-v8.37.py": ("v8.35", "old"),
        })
        live, col, mis, arch = audit(tmp)
        check("V6a a clean tree reports no collision and no mislabel",
              live is not None and not col and not mis,
              f"col={len(col)} mis={len(mis)}")

        # THE 2026-08-26 DEFECT, planted: a second file, elsewhere in the tree,
        # claiming the live version with different bytes.
        plant(tmp, {os.path.join("pending-v8.39", "covenant_unified_v8.py"):
                    ("v8.39", "a different implementation entirely")})
        live, col, mis, arch = audit(tmp)
        check("V6b the planted collision IS detected, including in a "
              "subdirectory",
              len(col) == 1 and col[0]["rel"].endswith("covenant_unified_v8.py")
              and os.sep in col[0]["rel"], str([c["rel"] for c in col]))
        check("V6c a byte-IDENTICAL copy is not a collision -- the rule is "
              "about bytes, not about filenames",
              True, "")
        shutil.copyfile(os.path.join(tmp, "covenant_unified_v8.py"),
                        os.path.join(tmp, "pending-v8.39",
                                     "covenant_unified_v8.py"))
        live, col, mis, arch = audit(tmp)
        check("V6d ...and it is measured: same version, same bytes, no failure",
              not col, str([c["rel"] for c in col]))

        # V7 -- the mislabelled backup.
        plant(tmp, {"covenant_unified_v8.PRE-v8.40.py": ("v8.40", "oops")})
        live, col, mis, arch = audit(tmp)
        check("V7 a PRE-vX.Y file declaring X.Y IS detected",
              len(mis) == 1 and mis[0]["name"] == "covenant_unified_v8.PRE-v8.40.py",
              str([m["name"] for m in mis]))
        os.remove(os.path.join(tmp, "covenant_unified_v8.PRE-v8.40.py"))
        live, col, mis, arch = audit(tmp)
        check("V7b and removing it clears the finding", not mis, "")

        # V8 -- prose must not satisfy the check.
        with open(os.path.join(tmp, "covenant_unified_v8.PRE-v8.38.py"),
                  "w", encoding="utf-8") as fh:
            fh.write('"""A docstring mentioning COVENANT_VERSION = "v8.39"."""\n'
                     '# COVENANT_VERSION = "v8.39"\n'
                     'CFG = {"COVENANT_VERSION": "v8.39"}\n')
        live, col, mis, arch = audit(tmp)
        check("V8 a version in a docstring, a comment or a dict does NOT count "
              "as a declaration (AST, not grep)",
              not col and declared_version(os.path.join(
                  tmp, "covenant_unified_v8.PRE-v8.38.py")) is None,
              str([c["rel"] for c in col]))

        # V9 -- archive-to-archive reuse is reported, never failed.
        plant(tmp, {"covenant_unified_v8.PRE-v8.30.py": ("v8.9-merged", "a"),
                    "covenant_unified_v8.PRE-v8.31.py": ("v8.9-merged", "b")})
        live, col, mis, arch = audit(tmp)
        check("V9 two archives sharing a version are REPORTED, not failed",
              "v8.9-merged" in arch and len(arch["v8.9-merged"]) == 2
              and not col and not mis, json.dumps(arch))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def v10_scanner_is_inert():
    """V10 -- the scanner must not RUN what it scans. A version checker that
    imports every copy of the core it finds has executed every copy of the core
    it found, including one an attacker dropped in the folder."""
    src = inspect.getsource(sys.modules[__name__])
    body = "".join(inspect.getsource(f) for f in
                   (declared_version, scan, audit, sha256_of,
                    pre_version_from_name))
    banned = ["exec(", "eval(", "__import__", "importlib", "runpy",
              "subprocess", "Popen", "compile("]
    hits = [b for b in banned if b in body]
    check("V10a the scanning path never executes a candidate file",
          not hits, str(hits))
    check("V10b it opens candidates for READING only",
          ', "w"' not in body and "'w'" not in body, "")
    # Over the AST, not by counting the text: the first version of this check
    # did `src.count("import covenant_unified_v8") == 1` and failed, because
    # the literal inside the check is itself an occurrence in the source it is
    # counting. A check that reads its own input is not a check (M43).
    tree = ast.parse(src)
    imports = [n for n in ast.walk(tree) if isinstance(n, ast.Import)
               and any(a.name == "covenant_unified_v8" for a in n.names)]
    fn_v1 = next((n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "v1_live"), None)
    check("V10c the core is imported exactly ONCE in this suite, and only in "
          "the section that asserts P11's contract",
          len(imports) == 1 and fn_v1 is not None
          and fn_v1.lineno <= imports[0].lineno <= fn_v1.end_lineno,
          f"{len(imports)} import(s) at {[n.lineno for n in imports]}")


if __name__ == "__main__":
    print("P18 -- two sources may not claim the same version\n")
    for fn in (v1_live, v3_tree, v6_mutation, v10_scanner_is_inert):
        try:
            fn()
        except Exception as e:
            check(f"{fn.__name__} raised", False, f"{type(e).__name__}: {e}")
        print()
    p = sum(1 for _, ok in results if ok)
    print(f"P18: {p}/{len(results)} passed")
    sys.exit(0 if p == len(results) else 1)
