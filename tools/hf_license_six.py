#!/usr/bin/env python3
"""Add an Apache-2.0 LICENSE to the six public repos that had none (his ask 2026-10-26: "Apache-2.0 the six
to match"). Adds the real LICENSE file on GitHub (canonical) AND the HF mirror, using the exact Apache-2.0
text already in covenant's LICENSE (standard license text, identical across projects). After this, re-run
tools/hf_cards.py so the model cards pick up license: apache-2.0. Needs COVENANT_GH_READ=1 (push via the
git credential) + cached HF token. Not committed (one-off)."""
import base64
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request as U

sys.path.insert(0, r"C:\Users\Lawre\covenant\tools")
import hf_mirror as M

GH = "LAWLESS1987"
SIX = ["spiking-experiments", "threefold-memory", "contradiction-probe",
       "flinch-observability", "flinch-record", "Sentinel-Witness"]


def main():
    hft = M._hf_token()
    if not hft:
        print("No HF token (hf auth login)."); return 2
    from huggingface_hub import HfApi, upload_file
    user = HfApi(token=hft).whoami().get("name")

    # The canonical Apache-2.0 text, straight from covenant's LICENSE (verified Apache-2.0).
    with U.urlopen("https://raw.githubusercontent.com/%s/covenant/main/LICENSE" % GH, timeout=20) as r:
        apache = r.read().decode("utf-8", "replace")
    if "Apache License" not in apache:
        print("could not fetch Apache text from covenant LICENSE"); return 1

    done = 0
    for repo in SIX:
        print("=== %s ===" % repo)
        d = tempfile.mkdtemp(prefix="hflic-")
        work = os.path.join(d, repo)
        # Public clone -- no auth needed. Push uses the system git credential (GCM), same path that pushes
        # covenant here successfully.
        c = subprocess.run(["git", "clone", "--depth", "1", "--single-branch", "--branch", "main",
                            "https://github.com/%s/%s.git" % (GH, repo), work], capture_output=True, text=True)
        if c.returncode != 0:
            print("  clone FAILED:", (c.stderr or "")[-160:]); shutil.rmtree(d, ignore_errors=True); continue
        if os.path.exists(os.path.join(work, "LICENSE")):
            print("  already has a LICENSE on GitHub -- ensuring HF only")
        else:
            with open(os.path.join(work, "LICENSE"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(apache)
            subprocess.run(["git", "-C", work, "add", "LICENSE"], capture_output=True, text=True)
            subprocess.run(["git", "-C", work, "commit", "-m", "Add Apache-2.0 LICENSE"], capture_output=True, text=True)
            env = dict(os.environ); env["GIT_TERMINAL_PROMPT"] = "0"
            p = subprocess.run(["git", "-C", work, "push", "origin", "main"], capture_output=True, text=True, env=env)
            print("  GitHub push:", "OK" if p.returncode == 0 else "FAILED " + (p.stderr or "")[-160:])
        # HF: upload the LICENSE file to the mirror.
        try:
            upload_file(path_or_fileobj=apache.encode("utf-8"), path_in_repo="LICENSE",
                        repo_id="%s/%s" % (user, repo), repo_type="model", token=hft,
                        commit_message="Add Apache-2.0 LICENSE")
            print("  HF LICENSE uploaded"); done += 1
        except Exception as e:                                  # noqa: BLE001
            print("  HF upload FAILED:", str(e)[-160:])
        shutil.rmtree(d, ignore_errors=True)
    print("licensed %d/%d" % (done, len(SIX)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
