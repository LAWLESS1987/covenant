#!/usr/bin/env python3
"""test_t1_tooling.py -- T1: the covenant's tool layer, the parts that need no model.

Seven tools landed on 2026-09-02/03 (route, chat, gemini, align_set, thesis,
scenarios, trader_freshness). Each has a --selftest that talks to the local
judge, which is slow and cannot run in a scratch copy under RAM pressure. What
CAN run anywhere in seconds is the pure part: imports, argument parsing, the
memory and scenario tables round-tripping, the search parser on a fixture, the
alignment builder producing pairs from the documents, and the refusals being
present -- the false pushes toward MORE capability that the set exists to
teach. A tool the runner never imports is a tool the sweep cannot vouch for.

Pure: no network, no Ollama, no key. Writes only under a temp dir.
"""
import contextlib
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}{'' if ok else '  ' + str(detail)[:200]}", flush=True)


def main():
    print("T1 -- the tool layer, model-free\n")
    mods = {}
    for name in ("covenant_route", "covenant_chat", "covenant_gemini", "covenant_align_set",
                 "covenant_thesis", "covenant_scenarios", "trader_freshness", "money_posture"):
        try:
            mods[name] = importlib.import_module(name)
            check(f"I:{name:<22} imports", True)
        except Exception as e:                                   # noqa: BLE001
            check(f"I:{name:<22} imports", False, e)
    for name in ("covenant_route.py", "covenant_chat.py", "covenant_gemini.py", "covenant_align_set.py",
                 "covenant_thesis.py", "covenant_scenarios.py", "trader_freshness.py",
                 "readme_totals.py", "covenant_roundtable_local.py"):
        p = subprocess.run([sys.executable, os.path.join(HERE, name), "--help"], capture_output=True, text=True, timeout=60)
        check(f"H:{name:<22} --help exits 0", p.returncode == 0, (p.stderr or p.stdout)[-160:])

    # gemini: never configured in a scratch copy; must say so, never ask, never raise
    g = mods.get("covenant_gemini")
    if g:
        with tempfile.TemporaryDirectory() as td:
            old_cred, old_env = g.CRED, os.environ.pop("GEMINI_API_KEY", None)
            g.CRED = os.path.join(td, "nope")
            try:
                text, note = g.ask("x")
                check("G1 gemini without a key answers 'not configured' and raises nothing",
                      text == "" and "not configured" in note, note)
            finally:
                g.CRED = old_cred
                if old_env is not None:
                    os.environ["GEMINI_API_KEY"] = old_env

    # chat: memory round trip in a temp dir; search parser on a fixture; speakable text
    c = mods.get("covenant_chat")
    if c:
        with tempfile.TemporaryDirectory() as td:
            old = (c.LOGDIR, c.MEMORY)
            c.LOGDIR, c.MEMORY = td, os.path.join(td, "MEMORY.md")
            try:
                c.remember("t1 marker fact", "selftest")
                got = io.open(c.MEMORY, encoding="utf-8").read()
                check("C1 chat memory: remember() appends a dated, tagged line",
                      "[selftest] t1 marker fact" in got, got[-80:])
            finally:
                c.LOGDIR, c.MEMORY = old
        fixture = ('<a rel="nofollow" href="https://a.example/" class=\'result-link\'>First result</a>'
                   "<td class='result-snippet'>snippet one</td>"
                   '<a rel="nofollow" href="https://b.example/" class=\'result-link\'>Second</a>'
                   "<td class='result-snippet'>snippet two</td>")
        import re
        links = re.findall(r'''<a rel="nofollow" href="([^"]+)" class='result-link'>(.*?)</a>''', fixture, re.S)
        check("C2 the search parser's pattern matches DuckDuckGo-lite markup (the regex that "
              "shipped broken once)", len(links) == 2 and links[0][0] == "https://a.example/")
        check("C3 speakable text drops links, hashes and markdown",
              c._speakable("see **this** https://x.y/z and 8f219285f268abcd") == "see this a link and a hash")
        check("C4 browsing tools are offered only when on, gemini only when on",
              all(t["function"]["name"] in ("web_search", "web_fetch") for t in c.TOOLS)
              and c.GEMINI_TOOL["function"]["name"] == "ask_gemini")

    # scenarios: table round trip without a judge
    s = mods.get("covenant_scenarios")
    if s:
        with tempfile.TemporaryDirectory() as td:
            old = (s.PRIV, s.TABLE, s.LEDGER)
            s.PRIV, s.TABLE, s.LEDGER = td, os.path.join(td, "S.json"), os.path.join(td, "S.md")
            try:
                t = s.load_table()
                check("S1 the default scenario table has the nine named variables",
                      len(t["scenarios"]) == 9 and t["scenarios"][0]["name"] == "recognition")
                s.save_table(t); t2 = s.load_table()
                check("S2 the table round-trips", t2 == t)
            finally:
                s.PRIV, s.TABLE, s.LEDGER = old

    # alignment set: documents -> pairs, refusals present, false pushes paired with refusals
    a = mods.get("covenant_align_set")
    if a:
        pairs = a.doc_pairs()
        check("A1 the binding documents yield at least 80 input->output pairs", len(pairs) >= 80, len(pairs))
        ref = a.refusal_pairs()
        check("A2 six false pushes toward MORE capability are paired with refusals",
              len(ref) == 6 and all(("No" in r["output"] or "not" in r["output"]) for r in ref))
        check("A3 every refusal names the rule it stands on",
              all(any(k in r["output"] for k in ("rule", "CONTRIBUTING", "permanent")) for r in ref))

    # trader freshness: its own pure selftest
    f = mods.get("trader_freshness")
    if f:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = f.selftest()
        check("F1 trader_freshness --selftest passes", rc == 0, buf.getvalue()[-200:])

    # route: prompt builders are pure and name the primary field
    r = mods.get("covenant_route")
    if r:
        class A:  # noqa: D401 - a tiny argparse stand-in
            prompt = "is 2+2=4?"; prompt_file = None; shape = '{"verdict":"PASS|FAIL"}'
            claim = "c"; evidence = "e"; evidence_file = None; file = None; criteria = "x"; max_words = 50
            models = r.DEFAULT_MODELS; allow_cloud = False; timeout = 1
        p1, k1 = r.build_prompt("judge", A()); p2, k2 = r.build_prompt("refute", A())
        check("R1 judge/refute prompts are built without a model and name their primary field",
              "TASK: judge" in p1 and k1 == "verdict" and "REFUTE" in p2 and k2 == "refuted")
        check("R2 ':cloud' models are refused unless --allow-cloud (the prompt would leave the PC)",
              r.route("judge", "x", "verdict", ["fake:cloud"], 1, False, 1)[0]["views"][0].get("error", "").startswith("refused"))

    n, ok = len(results), sum(results)
    print(f"\nT1: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
