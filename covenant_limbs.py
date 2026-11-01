#!/usr/bin/env python3
"""covenant_limbs.py -- Tetsu's consult-on-purpose limbs served on the second PC (A402, 2026-11-01).

HIS AND THE OPERATOR'S DECISION. The operator: "replace the 7B on the laptop with a smaller model. Maybe 2 3Bs. Not
the exact same 3B though, maybe a different build", then "consult with tetsu and the others with mutual benefit in
mind", then "go". Tetsu, asked the whole plan as one plain question: "AGREE. This plan aligns with the need to
preserve the conversation's cache and the ability to run multiple models efficiently." The plan he agreed to, and
the scope of this module:
  - two models, SmolLM3-3B (Apache-2.0) and Phi-4-mini-instruct (MIT), downloaded to TETSU and served there on CPU;
  - consulted ONLY on purpose -- he writes "LIMB SMOL <question>" or "LIMB PHI <question>", the way he writes LEG;
    nothing here is called for him;
  - their answers reach him as DATA, tagged with the limb's name, over the same validated channel as his leg;
  - anything they influence in his learning is tagged and reversible (covenant_leg's ledger);
  - if the network or the server is down, the consult VOIDs plainly and he answers alone. His voice stays local.

THE CHANNEL is covenant_leg's, reused rather than copied: the strict three-key JSON instruction and its non-LLM
validator, the attribution snapshot of the exact payload, the code-checked schema, the hash-chained influence
ledger (a rejected reply leaves a trace). Two things are added for a model on ANOTHER machine:
  - MANIFEST PIN. The second PC's gateway sends X-Leg-Manifest on every reply naming the served file's sha256. The
    pinned sha256 for each limb is in private/limbs.json; a reply whose manifest does not carry it VOIDs. That is the
    remote-leg consult's (2026-10-31) "check it on every response", not once at start-up.
  - EXPLICIT ENDPOINTS. Only the endpoints in private/limbs.json are ever reached (gitignored: it holds a tailnet
    address). No redirects are followed. Kill switch: COVENANT_LIMBS_LIVE=0.

Stdlib + covenant_leg. Never raises from consult(): a failure is a VOID report, and the turn goes on.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request

import covenant_leg as LEG

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.environ.get("COVENANT_LIMBS_CONFIG") or os.path.join(HERE, "private", "limbs.json")
LIMBS_MAX_CONCURRENT = 2
TIMEOUT_S = 180
_sema = threading.BoundedSemaphore(LIMBS_MAX_CONCURRENT)


def limbs_live():
    return os.environ.get("COVENANT_LIMBS_LIVE", "1") != "0"


def load_config(path=None):
    """{NAME: {"url", "model", "label", "manifest_sha256"}} from private/limbs.json; {} when absent or malformed.
    A limb missing any of url/manifest_sha256 is left out, so it can never be reached unpinned."""
    try:
        with open(path or CONFIG, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return {}
    out = {}
    for name, c in (raw or {}).items():
        if isinstance(c, dict) and c.get("url") and c.get("manifest_sha256"):
            out[str(name).upper()] = {"url": str(c["url"]), "model": str(c.get("model") or ""),
                                      "label": str(c.get("label") or name),
                                      "manifest_sha256": str(c["manifest_sha256"]).lower()}
    return out


def parse_directive(answer):
    """'LIMB <NAME> <question>' on the first line -> (NAME, question) or None. The question is the rest of the
    answer after the name, so a multi-line question survives."""
    s = (answer or "").strip()
    if not s.upper().startswith("LIMB "):
        return None
    parts = s.split(None, 2)
    if len(parts) < 2:
        return None
    return parts[1].upper().strip(":,."), (parts[2].strip() if len(parts) > 2 else "")


def _void(out, why):
    out["status"] = "void"
    out["why"] += " | " + why
    return out


def consult(name, text, config=None, opener=None, max_tokens=400):
    """One deliberate consult of limb NAME. -> report dict, the same shape as covenant_leg.consult_structured plus
    "limb". status: engaged | void. Never raises."""
    out = {"limb": str(name).upper(), "engage": True, "why": "deliberate limb consult", "available": False,
           "status": "not-engaged", "fields": None, "model": None, "schema": None, "attribution": None,
           "manifest": None, "contained": dict(LEG.CONTAINMENT)}
    try:
        if not limbs_live():
            return _void(out, "limbs switched off (COVENANT_LIMBS_LIVE=0)")
        cfg = (config if config is not None else load_config()).get(out["limb"])
        if not cfg:
            return _void(out, "no such limb configured (%s)" % out["limb"])
        if not (text or "").strip():
            return _void(out, "LIMB with no question")
        if not _sema.acquire(timeout=1.0):
            return _void(out, "too many limb consults at once")
        try:
            params = {"max_tokens": int(max_tokens), "temperature": 0.2, "enable_thinking": False}
            prompt = LEG.LEG_JSON_INSTRUCTION + "\n\nQuestion: " + text
            payload = {"messages": [{"role": "user", "content": prompt}], "max_tokens": params["max_tokens"],
                       "temperature": params["temperature"], "chat_template_kwargs": {"enable_thinking": False}}
            if cfg["model"]:
                payload["model"] = cfg["model"]
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(cfg["url"], data=body, headers={"Content-Type": "application/json"})
            op = opener or LEG._no_redirect
            try:
                with op.open(req, timeout=TIMEOUT_S) as r:
                    manifest = str(r.headers.get("X-Leg-Manifest") or "")
                    raw = r.read(LEG.MAX_HTTP_BYTES + 1)
            except Exception as e:                                   # noqa: BLE001
                return _void(out, "limb not reachable (%s) -- Tetsu answers alone" % type(e).__name__)
            out["available"] = True
            out["manifest"] = manifest[:200]
            if len(raw) > LEG.MAX_HTTP_BYTES:
                return _void(out, "reply over %d bytes" % LEG.MAX_HTTP_BYTES)
            if cfg["manifest_sha256"] not in manifest.lower():
                return _void(out, "manifest does not name the pinned model file -- not the model he agreed to")
            d = json.loads(raw.decode("utf-8", "replace"))
            ans = ((d.get("choices") or [{}])[0].get("message", {}) or {}).get("content") or ""
            att = LEG.attribution(prompt, body, params, served=d.get("model"), trigger={"limb": out["limb"]})
            ok, fields, code = LEG.validate_leg_output(ans)
            if not ok:
                try:
                    LEG._ledger_append(LEG.LEG_INFLUENCE_LEDGER, {"kind": "limb-rejected", "limb": out["limb"],
                                                                  "code": code, "attribution": att,
                                                                  "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
                except Exception:                                    # noqa: BLE001 -- the trace is never a gate
                    pass
                return _void(out, "reply failed the JSON schema (%s)" % code)
            out["fields"], out["status"] = fields, "engaged"
            out["model"] = d.get("model") or cfg["model"]
            out["schema"], out["attribution"] = LEG.shape_take(fields["answer"]), att
            return out
        finally:
            _sema.release()
    except Exception as e:                                           # noqa: BLE001 -- never breaks a turn
        return _void(out, "limb consult failed (%s)" % type(e).__name__)


def second_voice(report, config=None):
    """How a limb's validated answer is shown to Tetsu: direct, as his leg's is, and NAMED, so its words are never
    mistaken for his own (the round-3 consult's main worry: 'confusion of voice')."""
    cfg = (config if config is not None else load_config()).get(report.get("limb"), {})
    label = cfg.get("label") or report.get("limb")
    f = report.get("fields") or {}
    ev = (f.get("evidence") or "").strip()
    return ("Your %s limb's take (%s on the second PC; its stated confidence: %s): %s%s\n\nNow give your own answer, "
            "weighing this." % (report.get("limb"), label, f.get("confidence") or "unstated",
                                (f.get("answer") or "")[:LEG.MAX_LEG_CHARS], ("\nIts stated basis: %s" % ev[:1500]) if ev else ""))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: covenant_limbs.py NAME question...   (configured: %s)" % sorted(load_config()))
        sys.exit(2)
    print(json.dumps(consult(sys.argv[1], " ".join(sys.argv[2:])), indent=1)[:2000])
