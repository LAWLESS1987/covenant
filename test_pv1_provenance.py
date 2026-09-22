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


def check(name, cond, note=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + str(note)[:200]) if note and not cond else ""))


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
c = P.classify(r"C:\Users\Someone\Downloads\invoice.exe", REG, root)
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
j = judged("Trojan:Win32/Wacatac.B!ml", r"C:\Users\Someone\Downloads\invoice.exe")
check("PV1.9 a machine-learning verdict on a FOREIGN file is never settled", j["settled"] is False and "NEEDS YOU" in j["says"], j["says"])
j = judged("", member)
check("PV1.10 a verdict with no name is not assumed heuristic", j["settled"] is False)

# ---- the real registry and the real detections, read-only
real = P.registry()
check("PV1.11 the real registry names at least one archive, each with a source and a 64-hex digest",
      real and all(len(str(e.get("sha256", ""))) == 64 and e.get("source") for e in real), real)
good = {e.get("archive") for e, _m in P.verified_archives()}
check("PV1.12 and every archive it names still hashes to what its publisher published",
      good and len(good) == len(real), (sorted(good), len(real)))
j = P.judge_detection({"threat": "Trojan:Win32/Wacatac.B!ml",
                       "resources": r"file:_C:\Users\Lawre\covenant\tools\llama\llama-gguf-split.exe"})
check("PV1.13 the real detection from 2026-09-21 settles as a false positive, by hash",
      j["settled"] is True and "still hashes to what" in j["says"], j["says"][:150])

# ---- and the detector the watchdog runs
import covenant_highway as HW                                         # noqa: E402
d = HW.detect_defender_threat()
check("PV1.14 with every detection settled the condition is ABSENT and says nothing was waved through blind",
      d["state"] == HW.ABSENT and d["measured"].get("all_settled") is True
      and "waved through blind" in d["measured"].get("note", ""), d["measured"])

print("\nnot measured here: that upstream itself was honest. A hash proves we hold exactly what a project "
      "published; if the project were compromised the hash matches the compromised file. That is the bar, and "
      "this suite claims nothing above it.")
print("\nPV1: %d/%d passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
