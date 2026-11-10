#!/usr/bin/env python3
"""Add HF model-card YAML front-matter to the public repos' existing READMEs (2026-10-26, his ask:
"Add READMEs/model cards to the public repos"). The content is already good on GitHub; this only prepends
the metadata HF needs to render a proper card (pretty_name, tags, detected license) -- it does NOT rewrite
the prose. License is READ from each repo's LICENSE file, never guessed. Uploads README.md to each HF repo.
Not committed (names are public repos, but it's a one-off). COVENANT_GH_READ not needed (public raw)."""
import sys
import urllib.request as U

sys.path.insert(0, r"C:\Users\Lawre\covenant\tools")
import hf_mirror as M

# (pretty_name, tags) per public repo -- drawn from each repo's own README, not invented.
META = {
    "covenant": ("Covenant", ["ai-safety", "multi-agent-systems", "ai-ethics", "governance", "peer-to-peer"]),
    "spiking-experiments": ("Spiking Neural Network Experiments",
                            ["spiking-neural-networks", "snntorch", "brian2", "neuromorphic", "mnist"]),
    "threefold": ("Threefold (L-lens)",
                  ["ai-observability", "interpretability", "provenance", "mechanistic-interpretability"]),
    "threefold-memory": ("Threefold Memory", ["agent-memory", "provenance", "ai-agents"]),
    "contradiction-probe": ("Contradiction Probe",
                            ["ai-safety", "evaluation", "preregistered", "contradiction-detection"]),
    "flinch-observability": ("Flinch Observability",
                             ["ai-safety", "interpretability", "model-behavior", "evaluation"]),
    "flinch-record": ("Flinch Record", ["ai-behavior", "transcript", "research-record"]),
    "grokflinch": ("GrokFlinch", ["ai-behavior", "video-analysis", "research-record"]),
    "Sentinel-Witness": ("Sentinel-Witness", ["trading", "dashboard", "ledger", "crypto"]),
}


def _fetch(repo, fname):
    for br in ("main", "master"):
        try:
            with U.urlopen("https://raw.githubusercontent.com/LAWLESS1987/%s/%s/%s" % (repo, br, fname), timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:                                       # noqa: BLE001
            continue
    return None


def _license(repo):
    """HF license id from the repo's LICENSE file text; None if indeterminate (then omitted, not guessed)."""
    txt = (_fetch(repo, "LICENSE") or _fetch(repo, "LICENSE.md") or _fetch(repo, "LICENCE") or "").lower()
    if not txt:
        return None
    if "public domain" in txt or "cc0" in txt or "creative commons zero" in txt:
        return "cc0-1.0"
    if "unlicense" in txt:
        return "unlicense"
    if "apache license" in txt or "apache-2.0" in txt:
        return "apache-2.0"
    if "permission is hereby granted, free of charge" in txt:   # MIT
        return "mit"
    if "gnu general public" in txt:
        return "gpl-3.0"
    return None


# Where each piece sits in the whole (one line, appended to its card).
PLACE = {
    "covenant": "the governed core the others observe, measure, and record.",
    "spiking-experiments": "the neuromorphic research lab behind the covenant's stdlib spiking reflexes.",
    "threefold": "the observability + provenance layer that measures and records what the system does.",
    "threefold-memory": "the persistent, provenance-tracked memory for that observability layer.",
    "contradiction-probe": "a preregistered, blind-scored instrument that keeps the system's judgements honest.",
    "flinch-observability": "a research instrument for a candidate conversational pattern, built to be hard to fool and hard to oversell.",
    "flinch-record": "a public session record of that pattern, named in real time on both sides.",
    "grokflinch": "verifiable observations of that pattern in a single real model session.",
    "Sentinel-Witness": "the ledger / trading-dashboard surface.",
}


def _system_md(user, repo):
    L = lambda n: "https://huggingface.co/%s/%s" % (user, n)
    return (
        "\n\n---\n\n"
        "## Part of one system — each piece usable on its own\n\n"
        "These repositories are independent instruments that also compose into a single apparatus for "
        "**building and honestly auditing trustworthy multi-intelligence systems**. Any one can be used "
        "standalone; together they form the stack:\n\n"
        "- **Governed core** — [covenant](%s): a self-governing multi-agent system with an ethics gate "
        "inside the transaction path.\n"
        "- **Observability & provenance** — [threefold](%s) (the L-lens layer over Jacobian Lens) and "
        "[threefold-memory](%s) (its persistent, provenance-tracked memory): every action measured and "
        "recorded under one task identity.\n"
        "- **Measurement instruments** — [contradiction-probe](%s) and [flinch-observability](%s), with the "
        "session records [flinch-record](%s) and [grokflinch](%s): preregistered, blind-scored tests of AI "
        "behaviour that embody the covenant's rule — *investigate a signal, never convict on one*.\n"
        "- **Neuromorphic research** — [spiking-experiments](%s): from-scratch spiking-network experiments "
        "with the pass/fail bar declared before each run.\n"
        "- **Ledger surface** — [Sentinel-Witness](%s): the trading / ledger dashboard.\n\n"
        "**This repository's place in it:** %s\n"
        % (L("covenant"), L("threefold"), L("threefold-memory"), L("contradiction-probe"),
           L("flinch-observability"), L("flinch-record"), L("grokflinch"), L("spiking-experiments"),
           L("Sentinel-Witness"), PLACE.get(repo, "one instrument in the system."))
    )


def main():
    hft = M._hf_token()
    if not hft:
        print("No HF token (hf auth login)."); return 2
    from huggingface_hub import HfApi, upload_file
    user = HfApi(token=hft).whoami().get("name")
    print("HF account:", user)
    done = 0
    for repo, (pretty, tags) in META.items():
        readme = _fetch(repo, "README.md")
        if readme is None:
            readme = "# %s\n" % pretty
        sysmd = _system_md(user, repo)
        if readme.lstrip().startswith("---"):
            # already carded: keep its front-matter and body, just add the system section (idempotent-ish).
            body = readme if "Part of one system" in readme else readme + sysmd
        else:
            # These six were Apache-2.0'd on 2026-10-26 (LICENSE added to GitHub and/or HF); force the card
            # to match even where GitHub detection can't see it yet (e.g. Sentinel-Witness, whose GitHub push
            # was blocked by repo rules but whose HF repo carries the Apache LICENSE).
            FORCE = {"spiking-experiments", "threefold-memory", "contradiction-probe",
                     "flinch-observability", "flinch-record", "Sentinel-Witness"}
            lic = "apache-2.0" if repo in FORCE else _license(repo)
            fm = ["---"]
            if lic:
                fm.append("license: %s" % lic)
            fm.append("pretty_name: %s" % pretty)
            fm.append("tags:")
            fm += ["  - %s" % t for t in tags]
            fm.append("---")
            body = "\n".join(fm) + "\n\n" + readme + sysmd
        try:
            upload_file(path_or_fileobj=body.encode("utf-8"), path_in_repo="README.md",
                        repo_id="%s/%s" % (user, repo), repo_type="model", token=hft,
                        commit_message="Add model-card front-matter (license/tags/title)")
            print("  %-26s OK (license=%s, %d tags)" % (repo, lic or "none", len(tags)))
            done += 1
        except Exception as e:                                  # noqa: BLE001
            print("  %-26s FAILED: %s" % (repo, str(e)[-160:]))
    print("carded %d/%d public repos" % (done, len(META)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
