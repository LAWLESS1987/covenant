#!/usr/bin/env python3
"""test_pv1_provenance.py -- A217: when the antivirus flags a file, the system
decides ours-verified / ours-unaccounted / foreign by HASH, and only ever
settles a hit for itself when both halves hold.

His words, 2026-09-21: "Delete the anti-virus and have the system act as one."
The antivirus stays -- nothing in this repository scans a file as it executes,
and its own security module says "Nothing here reads the operating system".
What the covenant takes over is the judgement, and these checks are about the
line between settling a hit and handing it to him. Every check that could
wave something through is driven the other way too.
LICENCE: public domain.
"""
import hashlib
import json
import os
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
sys.path.insert(0, HERE)
import covenant_provenance as P                                       # noqa: E402

ok = []
NOT_RUN = []


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:200]) if note and not cond else ""))


def not_run(name, why):
    """A232: said, and counted neither way. Only for a state this tree cannot hold --
    never for one it holds and gets wrong."""
    NOT_RUN.append(name)
    print("NOT RUN  %s  -- %s" % (name, why))


# A232: a foreign path must be ABSOLUTE on the platform running this. The Windows
# form on Linux is a relative name, resolves under the working directory -- the
# staged copy, named covenant_one_* -- and reads as inside the tree (PV1.6 red on
# every Linux CI run from fc551b5 on).
FOREIGN = r"C:\Users\Someone\Downloads\invoice.exe" if os.name == "nt" else "/home/someone/Downloads/invoice.exe"

print("PV1 -- provenance: foreign, or ours and accounted for")

# ---- a fixture tree: an archive, its member on disk, and a registry
root = tempfile.mkdtemp(prefix="pv1_")
os.makedirs(os.path.join(root, "ops"), exist_ok=True)
os.makedirs(os.path.join(root, "bin"), exist_ok=True)
GOOD = b"the real binary, byte for byte what upstream published"
member = os.path.join(root, "bin", "tool.exe")
with open(member, "wb") as fh:
    fh.write(GOOD)
arc = os.path.join(root, "bin", "release.zip")
with zipfile.ZipFile(arc, "w") as z:
    z.writestr("bin/tool.exe", GOOD)
arc_sha = hashlib.sha256(open(arc, "rb").read()).hexdigest()
REG = os.path.join(root, "ops", "known_artifacts.json")


def write_registry(sha):
    json.dump({"artifacts": [{"archive": "bin/release.zip", "sha256": sha,
                              "source": "example.test release v1"}]},
              open(REG, "w", encoding="utf-8"))


write_registry(arc_sha)

c = P.classify(member, REG, root)
check("PV1.1 a file that IS the archive's member, with the archive still matching upstream, is ours:verified",
      c["verdict"] == "ours:verified" and "byte for byte" in c["why"], c)

# ---- THE ATTACK: right name, wrong bytes
with open(member, "wb") as fh:
    fh.write(b"swapped for something else")
c = P.classify(member, REG, root)
check("PV1.2 broken the other way: the same NAME with different bytes is NOT verified -- a swapped file is not a false positive",
      c["verdict"] == "ours:unverified" and "swapped file" in c["why"], c)
with open(member, "wb") as fh:
    fh.write(GOOD)

# ---- the file the antivirus already deleted
os.remove(member)
c = P.classify(member, REG, root)
check("PV1.3 a member the antivirus already removed is still ours:verified, and says its bytes could not be re-read",
      c["verdict"] == "ours:verified" and "could not be re-read" in c["why"], c)

# ---- the archive itself no longer matching upstream
write_registry("0" * 64)
c = P.classify(member, REG, root)
check("PV1.4 broken the other way: if the ARCHIVE no longer matches what upstream published, nothing inside it is vouched for",
      c["verdict"] != "ours:verified", c)
write_registry(arc_sha)

# ---- in our tree but unaccounted for, and plainly foreign
c = P.classify(os.path.join(root, "ops", "mystery.exe"), REG, root)
check("PV1.5 a file in the tree belonging to no registered archive is unaccounted for, never dismissed",
      c["verdict"] == "ours:unverified" and "unaccounted for" in c["why"], c)
c = P.classify(FOREIGN, REG, root)
check("PV1.6 a file outside the tree entirely is foreign", c["verdict"] == "foreign", c)

# ---- the judgement: BOTH halves must hold before a hit is settled
with open(member, "wb") as fh:
    fh.write(GOOD)


def judged(threat, path):
    return P.judge_detection({"threat": threat, "resources": "file:_" + path}, REG, root)


j = judged("Trojan:Win32/Wacatac.B!ml", member)
check("PV1.7 a machine-learning verdict on a verified file is settled, and says why", j["settled"] is True and "false positive" in j["says"], j["says"])
j = judged("Trojan:Win32/Emotet.A", member)
check("PV1.8 broken the other way: a SIGNATURE match on the SAME verified file is NEVER settled -- named malware inside a file we vouch for is the one case that must reach him",
      j["settled"] is False and "SIGNATURE" in j["says"], j["says"])
j = judged("Trojan:Win32/Wacatac.B!ml", FOREIGN)
check("PV1.9 a machine-learning verdict on a FOREIGN file is never settled", j["settled"] is False and "NEEDS YOU" in j["says"], j["says"])
j = judged("", member)
check("PV1.10 a verdict with no name is not assumed heuristic", j["settled"] is False)

# ---- the real registry and the real detections, read-only
real = P.registry()
check("PV1.11 the real registry names at least one archive, each with a source and a 64-hex digest",
      real and all(len(str(e.get("sha256", ""))) == 64 and e.get("source") for e in real), real)


def _on_disk(e):
    p = e.get("archive") or ""
    return os.path.isfile(p if os.path.isabs(p) else os.path.join(P.HERE, p))


# A232: the archives are the OPERATOR's -- tools/llama/ is gitignored, and the sweep
# never stages it (A201: a staged copy tripped Defender). So in the sweep, on this PC
# and on CI alike, and on any fresh clone, the tree holds none of them and PV1.12-13
# failed on every run since they were written, while the live folder read MATCHES.
# Where NONE is on disk they are said as NOT RUN; where any is, they run unchanged,
# and a missing or altered archive still fails (as G4.4b, A171).
ARCHIVES_HERE = real and any(_on_disk(e) for e in real)
NO_ARCHIVE = ("none of the %d registered archive(s) is on disk in this tree (%s): the operator's, "
              "gitignored and never staged (A201) -- measured by running this suite in the live folder"
              % (len(real), ", ".join(str(e.get("archive")) for e in real)[:120]))
if ARCHIVES_HERE:
    good = {e.get("archive") for e, _m in P.verified_archives()}
    check("PV1.12 and every archive it names still hashes to what its publisher published",
          good and len(good) == len(real), (sorted(good), len(real)))
    j = P.judge_detection({"threat": "Trojan:Win32/Wacatac.B!ml",
                           "resources": r"file:_C:\Users\Lawre\covenant\tools\llama\llama-gguf-split.exe"})
    check("PV1.13 the real detection from 2026-09-21 settles as a false positive, by hash",
          j["settled"] is True and "still hashes to what" in j["says"], j["says"][:150])
else:
    not_run("PV1.12 and every archive it names still hashes to what its publisher published", NO_ARCHIVE)
    not_run("PV1.13 the real detection from 2026-09-21 settles as a false positive, by hash", NO_ARCHIVE)

# ---- and the detector the watchdog runs
import covenant_highway as HW                                         # noqa: E402
# A232: this reads the REAL machine, and on 2026-09-26 it failed on this PC too:
# Defender had recorded nothing in 24 h, so there was no detection to settle and the
# condition said {"detections_24h": 0}. It is measured only where it can be -- Windows,
# a detection in the window, and the archives on disk to judge it by. PV1.15-16 drive
# the same detector with the same kind of detection on every platform, both ways.
if os.name != "nt":
    not_run("PV1.14 with every detection settled the condition is ABSENT and says nothing was waved through blind",
            "no Windows Defender on this platform (%s): there is no detection history to read" % sys.platform)
else:
    d = HW.detect_defender_threat()
    if d["state"] == HW.ABSENT and d["measured"].get("detections_24h") == 0:
        not_run("PV1.14 with every detection settled the condition is ABSENT and says nothing was waved through blind",
                "Defender recorded no detection in the last 24 h, so there is nothing on this machine to settle")
    elif d["state"] != HW.UNKNOWN and not ARCHIVES_HERE:
        not_run("PV1.14 with every detection settled the condition is ABSENT and says nothing was waved through blind",
                "%s detection(s) in 24 h, but %s" % (d["measured"].get("detections_24h"), NO_ARCHIVE))
    else:
        check("PV1.14 with every detection settled the condition is ABSENT and says nothing was waved through blind",
              d["state"] == HW.ABSENT and d["measured"].get("all_settled") is True
              and "waved through blind" in d["measured"].get("note", ""), d["measured"])

# ---- the same detector, driven with a detection like the one it was written for, on
#      the fixture tree above: settled when it should be, and never when it must not be
_real = (HW._defender_detections, HW.THREATS, P.REGISTRY, P.HERE)
try:
    P.REGISTRY, P.HERE = REG, root
    HW.THREATS = os.path.join(root, "ops", "security_threats.jsonl")
    ROW = {"t": "fixture", "id": "fixture", "ok": True, "process": "fixture",
           "threat": "Trojan:Win32/Wacatac.B!ml", "resources": "file:_" + member}
    HW._defender_detections = lambda hours=24: [dict(ROW)]
    d = HW.detect_defender_threat()
    check("PV1.15 a machine-learning hit on a verified member: the detector says ABSENT, all settled, nothing waved through blind",
          d["state"] == HW.ABSENT and d["measured"].get("all_settled") is True
          and "waved through blind" in d["measured"].get("note", ""), d["measured"])
    HW._defender_detections = lambda hours=24: [dict(ROW, threat="Trojan:Win32/Emotet.A")]
    d = HW.detect_defender_threat()
    check("PV1.16 broken the other way: a SIGNATURE hit on the same file keeps the condition PRESENT and hands it to him",
          d["state"] == HW.PRESENT and d["measured"].get("needs_you") == 1, d["measured"])
finally:
    HW._defender_detections, HW.THREATS, P.REGISTRY, P.HERE = _real

print("\nnot measured here: that upstream itself was honest. A hash proves we hold exactly what a project "
      "published; if the project were compromised the hash matches the compromised file. That is the bar, and "
      "this suite claims nothing above it.")
for n in NOT_RUN:
    print("  NOT RUN  %s" % n)
print("\nPV1: %d/%d passed%s" % (sum(ok), len(ok),
                                 (" (%d NOT RUN, not counted)" % len(NOT_RUN)) if NOT_RUN else ""))
sys.exit(0 if all(ok) else 1)
