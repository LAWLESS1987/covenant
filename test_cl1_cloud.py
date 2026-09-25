#!/usr/bin/env python3
"""CL1 -- his own cloud storage (covenant_cloud.py, A222; his words 2026-09-25: "can we create our
own free secure cloud storage?" -> "do so"). Runs with no Syncthing running and no network:

  CL1a  setup hardens a generated config: listens only on the tailnet address; relays, NAT,
        global and local discovery, usage and crash reporting off; the GUI on loopback; the
        API key rotated; one folder with 30-day staggered versioning; idempotent
  CL1b  verify counts added / changed / missing, and flags SILENT damage -- bytes changed with
        size and time unchanged -- both ways; it writes counts to the check and names only to
        the manifest
  CL1c  accept takes only devices dialling from the tailnet (100.x) and shares the folder with
        them; a device from anywhere else is listed and not accepted
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_cloud as C  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("  -- %s" % (str(detail)[:300],)) if detail and not ok else ""))


CONFIG = """<configuration version="51">
    <device id="AAAAAAA-BBBBBBB-CCCCCCC-DDDDDDD-EEEEEEE-FFFFFFF-GGGGGGG-HHHHHHH" name="Sales" compression="metadata"><address>dynamic</address></device>
    <gui enabled="true" tls="false"><address>127.0.0.1:8384</address><apikey>OLDKEY</apikey></gui>
    <options><listenAddress>default</listenAddress><globalAnnounceEnabled>true</globalAnnounceEnabled>
    <localAnnounceEnabled>true</localAnnounceEnabled><relaysEnabled>true</relaysEnabled><natEnabled>true</natEnabled>
    <urAccepted>0</urAccepted><crashReportingEnabled>true</crashReportingEnabled></options>
</configuration>"""


def main():
    td = tempfile.mkdtemp(prefix="cl1_")
    try:
        cfg = os.path.join(td, "config.xml")
        with open(cfg, "w", encoding="utf-8") as fh:
            fh.write(CONFIG)
        real_ip = C.tailnet_ip
        C.tailnet_ip = lambda: "100.1.2.3"
        folder = os.path.join(td, "cloud")
        try:
            C.setup(config=cfg, folder_path=folder, say=lambda *a: None)
            C.setup(config=cfg, folder_path=folder, say=lambda *a: None)          # idempotent
        finally:
            C.tailnet_ip = real_ip
        import xml.etree.ElementTree as ET
        root = ET.parse(cfg).getroot()
        o = root.find("options")
        val = lambda t: o.find(t).text                              # noqa: E731
        check("CL1a listens only on the tailnet address, and nothing else",
              [e.text for e in o.findall("listenAddress")] == ["tcp://100.1.2.3:22000"])
        check("CL1a relays, NAT, global and local discovery, usage and crash reporting are off",
              (val("relaysEnabled"), val("natEnabled"), val("globalAnnounceEnabled"), val("localAnnounceEnabled"),
               val("urAccepted"), val("crashReportingEnabled")) == ("false", "false", "false", "false", "-1", "false"))
        g = root.find("gui")
        check("CL1a the GUI stays on loopback and its API key is rotated",
              g.find("address").text == "127.0.0.1:8384" and g.find("apikey").text not in ("OLDKEY", "", None))
        fs = [f for f in root.findall("folder") if f.get("id") == C.FOLDER_ID]
        vp = fs[0].find("versioning") if fs else None
        check("CL1a exactly one folder after two runs, with staggered versioning kept 30 days, and it exists on disk",
              len(fs) == 1 and vp is not None and vp.get("type") == "staggered"
              and vp.find("param").get("val") == str(30 * 86400) and os.path.isdir(folder), len(fs))

        man, chk = os.path.join(td, "man.json"), os.path.join(td, "chk.json")
        st = lambda: {"running": False}                             # noqa: E731
        with open(os.path.join(folder, "a.txt"), "wb") as fh:
            fh.write(b"hello world")
        with open(os.path.join(folder, "b.txt"), "wb") as fh:
            fh.write(b"second file")
        os.makedirs(os.path.join(folder, ".stversions"))
        with open(os.path.join(folder, ".stversions", "old.txt"), "wb") as fh:
            fh.write(b"not counted")
        r1 = C.verify(folder=folder, manifest=man, check=chk, status_fn=st)
        check("CL1b first run: two files added, versions folder not counted", r1["counts"]["files"] == 2 and r1["counts"]["added"] == 2, r1["counts"])
        p = os.path.join(folder, "a.txt")
        stat = os.stat(p)
        with open(p, "wb") as fh:
            fh.write(b"HELLO WORLD")                                # same size
        os.utime(p, (stat.st_atime, stat.st_mtime))                 # same time: silent damage
        r2 = C.verify(folder=folder, manifest=man, check=chk, status_fn=st)
        check("CL1b bytes changed with size and time unchanged is SILENT damage", r2["counts"]["silent"] == 1 and r2["counts"]["changed"] == 0, r2["counts"])
        with open(os.path.join(folder, "b.txt"), "wb") as fh:
            fh.write(b"second file, edited")                        # size changes: an ordinary edit
        os.remove(p)
        r3 = C.verify(folder=folder, manifest=man, check=chk, status_fn=st)
        check("CL1b an ordinary edit is changed, not silent; a removed file is missing",
              r3["counts"]["changed"] == 1 and r3["counts"]["silent"] == 0 and r3["counts"]["missing"] == 1, r3["counts"])
        written = open(chk, encoding="utf-8").read()
        check("CL1b the check file carries counts, never file names (names stay in the manifest)",
              "a.txt" not in written and "b.txt" not in written and "b.txt" in open(man, encoding="utf-8").read())

        calls = []
        pending = {"PHONEID": {"address": "100.86.158.1:22000", "name": "phone"},
                   "STRANGER": {"address": "203.0.113.9:22000", "name": "x"}}
        folder_cfg = {"id": C.FOLDER_ID, "devices": [{"deviceID": "ME"}]}

        def fake_api(path, method="GET", body=None, config=None, raw=False):
            calls.append((method, path))
            if path == "/rest/cluster/pending/devices":
                return pending
            if path.startswith("/rest/config/folders/"):
                if method == "PUT":
                    folder_cfg.update(body)
                return folder_cfg
            return None
        real_api = C._api
        C._api = fake_api
        try:
            out = C.accept(say=lambda *a: None)
        finally:
            C._api = real_api
        check("CL1c a device dialling from the tailnet is accepted and shares the folder; one from elsewhere is not",
              [d for d, _ in out["accepted"]] == ["PHONEID"] and [d for d, _ in out["left"]] == ["STRANGER"]
              and any(d["deviceID"] == "PHONEID" for d in folder_cfg["devices"])
              and ("PUT", "/rest/config/devices/STRANGER") not in calls, (out, calls))
    finally:
        shutil.rmtree(td, ignore_errors=True)

    n, ok = len(results), sum(results)
    print("\nCL1: %d/%d passed" % (ok, n))
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
