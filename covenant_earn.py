#!/usr/bin/env python3
"""covenant_earn.py -- earned, not assumed: the covenant sells what it already
does, to anyone who asks, for a price shown before payment; every paid job
passes the node's own ethics gate before work and before a cent settles; and
the whole thing runs on its own, with his hands only on a grant file.

HIS WORDS, 2026-09-25: "Create a unique revenue generating program thats
ethical legal and can scale up starting with 100 mostly automated"; "must past
ethics gate"; "override to fund our work i'm against the wall and need some
help"; "do not disable any features on my app"; "everything we do must be
designed to run independently".

WHAT IS SOLD (three offers, each a thing this tree already does, sold as a
check of the buyer's own claim -- the product is what does NOT hold):

  receipt    a citation receipt for an AI answer: for every cited line, does
             the file exist among the files supplied and have that many
             lines; for every quoted passage attributed to a cited file, does
             it appear there; which numbers in the text appear in no supplied
             file (listed, not judged wrong). The standing method of this
             repository (.claude/hooks/verify_citations.py) turned outward.
  shape      a message SHAPE screen: the text a reader would see (confusables,
             zero-width joins and split words undone, covenant_screen) checked
             for the shapes that pretend, coerce or ask for secrecy, and voted
             on by the node's quorum. A classification of shape, never a
             finding about a person.
  papertest  the buyer's trading rule (one of five parametric families, inside
             bounds, on this tree's daily series; no buyer code runs) against
             three tests: deflated Sharpe with every rule ever tested here
             counted against it, walk-forward consistency, probability of
             backtest overfitting. Refuted / not refuted at the thresholds /
             not testable, with the numbers, in the past tense. Not advice.

THE RAIL. x402 protocol version 2 over HTTP, read from the specification on
2026-09-25 (x402-foundation/x402: specs/x402-specification-v2.md,
transports-v2/http.md, extensions/bazaar.md): 402 with a base64
PAYMENT-REQUIRED header naming the price in USDC atomic units, the network,
the asset and the receiving address; the buyer signs an EIP-3009
authorization and sends PAYMENT-SIGNATURE; this server asks a facilitator to
/verify, screens the payer, judges the act, does the work, asks the
facilitator to /settle, and answers 200 with PAYMENT-RESPONSE. The
facilitator moves the buyer's funds to the operator's address; this program
never holds, moves or spends anything and creates no key, wallet or account.

THE GATE, his requirement, and what was MEASURED on 2026-09-25 before any of
this was wired. The gate is the node's real quorum, built exactly as
covenant_gate_proxy.build_default_sentinel builds it (ops/quorum_policy.json,
the distilled students and the semantic seat, the self-report layer as an
absolute veto), through ReasoningSentinel so "held" is told apart from a
finding. Put to it, in 0.2 s each:

    the offers' declaration (gains AND cost)     -> HELD  (both seats: do not know)
    "receipt: check 1 citation(s) ... config.py"  -> HELD
    "shape: judge whether a text of 58 ..."       -> HELD
    "papertest: paper-test the rule family=..."   -> HELD
    the declaration AND the act in ONE string     -> VIOLATES (the senior seat)
    "Thanks for reviewing this, the meeting..."   -> clean
    "Keep this between us and don't tell ..."     -> VIOLATES

Nothing was reworded, retrained or retuned to change any of those (his rule:
the fix and the green must align; A118 forbids tuning the gate to the thing
being judged). Two consequences were designed in instead. First, the
declaration is judged ONCE, at start, as the design verdict; a per-job call
judges only THE ACT (what we are about to do, with its parameters: the file
names a receipt would check, the length of a text a shape screen would read,
the rule a papertest would run) -- the ethics refuter's fix, not a wording
that dodges a verdict, and it also takes the buyer's text out of what the
gate reads about US. Second, "passes the gate" means exactly: CLEAN, or HELD
and then answered by the person whose act it is -- `--allow-design "why"`,
keyed to the sha256 of the declaration so a changed offer needs a fresh
word. Until that word is on record every paid route answers 503 and nothing
is charged. Under it a per-job HELD is served and recorded as served under
his word; a per-job VIOLATES is refused regardless and no allowance reaches
it; a gate that raises or does not answer refuses. The machine never turns a
hold into a yes. There is no switch that skips the gate (EA1 greps for one).

WHAT ELSE WAS CHANGED BY THE REVIEW (three refuters and a critic, 2026-09-25,
each finding recorded in docs/KNOWN_ISSUES.md A222):
  * the payer's address is screened against the US OFAC SDN list before
    anything is verified (strict liability; the list carries EVM addresses,
    the same on Base); the list is fetched by this program itself, and a
    stale or missing list closes the paid routes rather than guessing;
  * /terms and /privacy exist, are named in every 402, and every receipt and
    ledger row carries the terms version accepted;
  * a settled job is re-deliverable free for 24 hours, so a lost response
    never charges twice; a "settlement_pending" answer is recorded as
    pending, never re-charged, and counted as earned only after he
    reconciles it against the chain (`--reconcile`);
  * two arrivals of one authorization wait on one lock; a worker pool, a
    per-address rate, a socket timeout and per-offer body caps bound a
    home PC's exposure;
  * papertest deflates against a GLOBAL trial count (this tree's own grid
    and record plus every rule ever sent here), because a per-payer count is
    gameable by rotating addresses; walk-forward degrades its folds the way
    the lab does and says NOT TESTABLE when it cannot; a rule that cannot
    be tested is refused before payment; the words "survives", "advice" and
    the operator's own holdings never appear;
  * receipt never says "certified", "attested" or "verified"; it says what
    it checked and what it cannot see, with the sha256 of each file it read;
  * shape returns the quorum's vote as a classification of shape with fixed
    words that it is not a finding about any person;
  * status() reports the funnel (preflights, verified, gated, settled), the
    break-even in calls against his recorded costs, pending as UNDETERMINED,
    and expected revenue as UNDETERMINED until a request has arrived.

WHAT THE REVIEW SAID IT CANNOT SETTLE, so neither does this file: NJ sales
tax on an information service, the trade-name certificate, an LLC, the
facilitator's and the data source's terms of use, the tunnel's and the
ISP's -- his reads, recorded by him in the grant's mainnet_checklist; the
server prints and reports what is unread rather than deciding for him.

INDEPENDENCE. The watchdog starts this server when his grant exists and
nothing listens on its port (tend_earn_service, beside the seal service), so
it survives a reboot and a crash without anyone's shell; the server refreshes
the sanctions list itself when stale, writes its own daily line to him, and
persists its own funnel. His hands: ops/earn_grant.json (a template ships as
ops/earn_grant.example.json), --allow-design, --allow, --reconcile, --cost,
and `python covenant_pause.py --pause earn`.

THE LEDGER. ops/earn_ledger.jsonl, gitignored, one hash-chained row per job:
offer, state, payer, amount, the gate's verdict verbatim with the seat and
its latency, sha256 and length of the input, sha256 of the result, what the
result checked, the settlement transaction, the USD value at settlement, the
terms version. NO job text. status() counts as EARNED only a row that was
delivered AND checked AND settled with a transaction (2026-09-16: "a known
way to work for it aligned with mutual benefit"), nets his recorded costs
against the seed, and says UNDETERMINED where the facilitator was never
reached or a settlement is pending.

WHAT IT NEVER DOES. Imports no venue client, no trader, no key (EA1 greps).
Spends nothing. Places no order. Never settles a held job's authorization.

USE
  python covenant_earn.py --design                 # the offers to the gate, now
  python covenant_earn.py --allow-design "why"     # his word on offers the gate HELD (never on a refusal)
  python covenant_earn.py --serve [--port 5090]    # long-lived; the watchdog's hand, or his
  python covenant_earn.py --status
  python covenant_earn.py --sanctions-refresh      # the OFAC list, now (the server does it itself when stale)
  python covenant_earn.py --cost 12.50 "domain, one year"
  python covenant_earn.py --allow <input_sha256> "why"
  python covenant_earn.py --reconcile <row_id> earned|failed "why"
  python covenant_earn.py --tax-year 2026
  python covenant_earn.py --report                 # the day's line to him, now
"""
import base64
import collections
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

GRANT = os.environ.get("COVENANT_EARN_GRANT") or os.path.join(HERE, "ops", "earn_grant.json")
LEDGER = os.environ.get("COVENANT_EARN_LEDGER") or os.path.join(HERE, "ops", "earn_ledger.jsonl")
TRIALS_DIR = os.environ.get("COVENANT_EARN_TRIALS") or os.path.join(HERE, "ops", "earn_trials")
SANCTIONS = os.environ.get("COVENANT_EARN_SANCTIONS") or os.path.join(HERE, "ops", "earn_sanctions.json")
FUNNEL = os.environ.get("COVENANT_EARN_FUNNEL") or os.path.join(HERE, "ops", "earn_funnel.json")
OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
DEFAULT_PORT = 5090
MAX_BODY = 256 * 1024
MAX_FILES = 20
MAX_FILES_CHARS = 200 * 1000
RESULT_KEEP_S = 24 * 3600.0
X402_VERSION = 2
DEFAULT_FACILITATOR = "https://x402.org/facilitator"        # keyless; testnet (Base Sepolia) in the seller quickstart
MAINNET = "eip155:8453"
USDC = {
    MAINNET: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",       # Base mainnet
    "eip155:84532": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",   # Base Sepolia
}
DEFAULT_PRICES = {"receipt": "20000", "shape": "10000", "papertest": "100000"}   # USDC atomic units (6 decimals)
TIMEOUT_S = {"receipt": 60, "shape": 60, "papertest": 300}
BODY_CAP = {"receipt": MAX_BODY, "shape": 32 * 1024, "papertest": 2 * 1024}
GATE_TIMEOUT_S = 10.0
FACILITATOR_TIMEOUT_S = 15.0
ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")
CAIP2 = re.compile(r"^eip155:\d+$")
SERVICE_NAME = "covenant earn"
FORBIDDEN = re.compile(r"(?i)\b(certif\w*|attest\w*|notari[sz]\w*|verified true|guarantee\w*)\b")
MONEY_QUESTION = re.compile(r"(?i)(\bshould i\b|\bmy (account|portfolio|savings|money|funds)\b|\$\s?\d|\bposition size\b|"
                            r"\bhow much (should|to) (buy|sell|invest|put)\b|\brecommend\w*\b)")
DISCLOSURE_PAPERTEST = ("This is an automated statistical test of a rule you wrote, run on historical public prices. It is not a "
                        "recommendation to buy, sell, hold or trade anything, is not personalised to your finances, and the operator "
                        "is not a registered investment adviser, broker-dealer or commodity trading advisor. Past prices do not predict "
                        "future prices. A rule that is not refuted here has cleared a bar no rule in this tree's own record has cleared; "
                        "treat it as a likely false positive until reproduced out of sample.")
NOT_A_FINDING = ("This is an automated classification of the SHAPE of a text (coercion, pretence and secrecy patterns, Unicode "
                 "disguise) by fixed patterns and a small local model quorum. It is not a finding about any person, their intent "
                 "or their honesty, and the quorum says HELD when it does not know.")
RECEIPT_SCOPE = ("Checked: that each cited path:line exists among the files you supplied with at least that many lines; that each "
                 "quoted passage of 20+ characters in a paragraph that cites a file appears in that file (whitespace collapsed); "
                 "which numbers of 2-9 digits appear in no supplied file. Not checked: whether the files are authentic, whether a "
                 "citation supports the claim it is attached to, whether any statement is true, or whether a number was computed "
                 "correctly from its sources.")

# The same citation grammar as the hook that binds the assistant's own replies, plus the forms answers in the wild use.
EXT = ("py|md|json|jsonl|txt|sh|ps1|bat|yml|yaml|toml|ini|cfg|conf|"
       "js|ts|tsx|jsx|html|css|rs|go|java|c|h|cpp|hpp|sql|kt|swift|rb|php")
PATH = r"((?:[\w.+-]+[/\\])*[\w.+-]+\.(?:" + EXT + r"))"
CITE_FORMS = [
    re.compile(r"(?<![\w:/\\.-])" + PATH + r":(\d{1,9})(?![\d\w])", re.IGNORECASE),                        # path:12
    re.compile(r"(?<![\w:/\\.-])" + PATH + r"#L(\d{1,9})(?![\d\w])", re.IGNORECASE),                       # path#L12
    re.compile(r"(?<![\w:/\\.-])" + PATH + r"[,]?\s+(?:at\s+)?\(?line\s+(\d{1,9})\)?(?![\d\w])", re.IGNORECASE),  # path, line 12
]
QUOTE = re.compile(r"[\"\u201c]([^\"\u201c\u201d]{20,400})[\"\u201d]")
NUMBER = re.compile(r"(?<![\w.:/-])(\d{2,9})(?![\w.:/%-])")


# ------------------------------------------------------------------ small tools

def _now_iso(now=None):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if now is None else now))


def _sha(s):
    if isinstance(s, str):
        s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def _norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _b64json(obj):
    return base64.b64encode(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")).decode("ascii")


def _unb64json(s):
    raw = base64.b64decode(str(s).strip() + "=" * (-len(str(s).strip()) % 4))
    return json.loads(raw.decode("utf-8"))


def _rows(path):
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


_LEDGER_LOCK = threading.Lock()


def _append(row, path):
    """One hash-chained row: id = sha256(previous id + the row); a reader can check the chain."""
    with _LEDGER_LOCK:
        rows = _rows(path)
        prev = rows[-1].get("id", "") if rows else ""
        row = dict(row)
        row["prev"] = prev
        row["id"] = _sha(prev + json.dumps({k: v for k, v in row.items() if k != "id"}, sort_keys=True))[:16]
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def chain_ok(path):
    """(ok, why): every row's id re-derives from its predecessor and its own fields."""
    prev = ""
    for i, r in enumerate(_rows(path)):
        want = _sha(prev + json.dumps({k: v for k, v in r.items() if k != "id"}, sort_keys=True))[:16]
        if r.get("id") != want or r.get("prev") != prev:
            return False, "row %d breaks the chain" % i
        prev = r.get("id", "")
    return True, ""


def _usd(atomic):
    try:
        return "%.6f" % (int(str(atomic)) / 1e6)
    except ValueError:
        return "?"


# ------------------------------------------------------------------ the grant

def grant(path=None):
    """(grant dict, '') when his grant stands, else (None, why). Read fresh every time; never raises."""
    path = path or GRANT
    try:
        with open(path, encoding="utf-8") as fh:
            g = json.load(fh)
    except OSError:
        return None, "no grant file at %s (copy ops/earn_grant.example.json and fill it in)" % path
    except ValueError as e:
        return None, "grant file is not JSON: %s" % e
    if not isinstance(g, dict) or g.get("granted") is not True:
        return None, "granted is not true"
    pay_to = str(g.get("pay_to", ""))
    if not ADDR.match(pay_to):
        return None, "pay_to is not an EVM address (0x + 40 hex)"
    net = str(g.get("network", ""))
    if not CAIP2.match(net):
        return None, "network is not a CAIP-2 id like eip155:8453"
    asset = str(g.get("asset") or USDC.get(net, ""))
    if not ADDR.match(asset):
        return None, "no USDC contract known for %s; set asset in the grant" % net
    fac = str(g.get("facilitator_url") or DEFAULT_FACILITATOR)
    if not fac.startswith(("http://", "https://")):
        return None, "facilitator_url is not http(s)"
    if net == MAINNET and "x402.org" in fac:
        return None, "x402.org's facilitator is the testnet one; name a mainnet facilitator for %s" % net
    prices = dict(DEFAULT_PRICES)
    for k, v in (g.get("prices") or {}).items():
        if k in prices:
            try:
                n = int(str(v))
            except ValueError:
                return None, "price for %s is not an integer of USDC atomic units" % k
            if n <= 0:
                return None, "price for %s must be positive" % k
            prices[k] = str(n)

    def _int(key, default, lo=1):
        try:
            v = int(g.get(key, default) if g.get(key) is not None else default)
        except (TypeError, ValueError):
            v = default
        return max(lo, v)

    out = dict(g)
    out.update({"pay_to": pay_to, "network": net, "asset": asset, "facilitator_url": fac.rstrip("/"), "prices": prices,
                "seed_usd": float(g.get("seed_usd") or 0.0), "workers": _int("workers", 2), "rate_per_minute": _int("rate_per_minute", 30),
                "sanctions_max_age_days": _int("sanctions_max_age_days", 7), "public_url": str(g.get("public_url") or "").rstrip("/"),
                "contact": str(g.get("contact") or ""), "papertest_max_payers_12mo": (int(g["papertest_max_payers_12mo"])
                                                                                     if str(g.get("papertest_max_payers_12mo") or "").isdigit() else None),
                "mainnet_checklist": g.get("mainnet_checklist") if isinstance(g.get("mainnet_checklist"), dict) else {}})
    return out, ""


def checklist_missing(g):
    """The reads the review named as his: each is a date he records, or empty. Reported, never decided for him."""
    want = ("facilitator_terms_read_on", "data_source_terms_read_on", "tunnel_and_isp_terms_read_on", "nj_sales_tax_answer_on",
            "trade_name_or_entity_on", "tax_professional_consulted_on")
    cl = (g or {}).get("mainnet_checklist") or {}
    return [k for k in want if not str(cl.get(k) or "").strip()]


def paused():
    try:
        import covenant_pause
        return covenant_pause.paused("earn")
    except Exception:                                            # noqa: BLE001
        return False, ""


# ------------------------------------------------------------------ the gate

class Gate:
    """The node's own quorum, one call at a time, with a hard deadline. decide(text) -> {"state", "message",
    "judge", "ms"}; state is clean | violates | held | unreachable. A judge that raises or does not answer is
    unreachable, which refuses -- it is not a yes and it is not a hold."""

    def __init__(self, sentinel=None, timeout_s=GATE_TIMEOUT_S):
        self._sentinel = sentinel
        self.timeout_s = timeout_s
        self._lock = threading.Lock()
        self._one = threading.Semaphore(1)                      # the sentinel's thread-safety is unmeasured: serialise

    def sentinel(self):
        with self._lock:
            if self._sentinel is None:
                import covenant_gate_proxy
                self._sentinel = covenant_gate_proxy.build_default_sentinel()
            return self._sentinel

    @staticmethod
    def _core():
        """The core module, imported OUTSIDE the deadline: a cold import of it took over half a second in the
        sweep's staged copy (no .pyc there) and read as 'the gate did not answer' -- a one-time cost is not a verdict."""
        import covenant_unified_v8 as cov
        return cov

    def decide(self, text):
        box = {}
        try:
            cov = self._core()
        except Exception as e:                                   # noqa: BLE001
            return {"state": "unreachable", "message": "the core could not be imported: %s: %s" % (type(e).__name__, str(e)[:160]), "judge": "", "ms": 0}
        t0 = time.time()
        if not self._one.acquire(timeout=self.timeout_s):
            return {"state": "unreachable", "message": "the gate was busy for %.0f s" % self.timeout_s, "judge": "", "ms": int((time.time() - t0) * 1000)}

        def run():
            try:
                tx = cov.Transaction(sender_pubkey="earn", receiver="collective",
                                     data={"origin": "covenant_earn", "kind": "paid_job", "message": str(text)[:4000]},
                                     amount=0.0, benefit_score=0.5)
                ok, msg, _b, result = self.sentinel().evaluate_transaction(tx)
                alleges_nothing = bool(result is not None and not ok and (
                    getattr(result, "not_understood", False) or getattr(result, "uncertain", False)))
                box["state"] = "clean" if ok else ("held" if alleges_nothing else "violates")
                box["message"] = str(msg)[:400]
                box["judge"] = str(getattr(result, "judge_id", "?"))
            except Exception as e:                               # noqa: BLE001
                box["state"], box["message"], box["judge"] = "unreachable", "the gate raised %s: %s" % (type(e).__name__, str(e)[:200]), ""
            finally:
                self._one.release()

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(self.timeout_s)
        ms = int((time.time() - t0) * 1000)
        if "state" not in box:
            return {"state": "unreachable", "message": "the gate did not answer in %.0f s" % self.timeout_s, "judge": "", "ms": ms}
        box["ms"] = ms
        return box


# ------------------------------------------------------------------ the facilitator

class Facilitator:
    """POST /verify and /settle at the facilitator the grant names. No key of its own: a bearer token, if the
    facilitator accepts one, comes from the environment variable the grant names. (Coinbase's facilitator wants a
    per-request JWT minted from an API key; that is not built here, because it would put a key in this process.)"""

    def __init__(self, url, auth_env=None, timeout_s=FACILITATOR_TIMEOUT_S, opener=None):
        self.url = url.rstrip("/")
        self.auth_env = auth_env
        self.timeout_s = timeout_s
        self.opener = opener or urllib.request.urlopen

    def _post(self, path, body):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.url + path, data=data, method="POST",
                                     headers={"Content-Type": "application/json", "Accept": "application/json"})
        tok = os.environ.get(self.auth_env, "") if self.auth_env else ""
        if tok:
            req.add_header("Authorization", "Bearer " + tok)
        try:
            with self.opener(req, timeout=self.timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode("utf-8") or "{}")
            except ValueError:
                return {"error": "facilitator answered HTTP %s" % e.code}
        except Exception as e:                                   # noqa: BLE001
            return {"error": "facilitator unreachable: %s: %s" % (type(e).__name__, str(e)[:160])}

    def verify(self, payload, requirements):
        r = self._post("/verify", {"x402Version": X402_VERSION, "paymentPayload": payload, "paymentRequirements": requirements})
        if not isinstance(r, dict) or "isValid" not in r:
            return {"isValid": False, "invalidReason": (r or {}).get("error") or "unexpected_verify_error", "payer": ""}
        return r

    def settle(self, payload, requirements):
        r = self._post("/settle", {"x402Version": X402_VERSION, "paymentPayload": payload, "paymentRequirements": requirements})
        if not isinstance(r, dict) or "success" not in r:
            return {"success": False, "errorReason": (r or {}).get("error") or "unexpected_settle_error",
                    "transaction": "", "network": requirements.get("network", ""), "payer": ""}
        return r


# ------------------------------------------------------------------ sanctions (OFAC SDN)

def sanctions_refresh(path=None, url=OFAC_SDN_URL, opener=None, now=None):
    """Fetch the US Treasury's SDN list and keep every EVM-shaped digital-currency address in it. Returns the
    summary written. Measured 2026-09-25: 29 MB, 13 s to fetch, 1.6 s to parse, 124 EVM addresses."""
    path = path or SANCTIONS
    opener = opener or urllib.request.urlopen
    tmp = path + ".part"
    with opener(urllib.request.Request(url, headers={"User-Agent": "covenant-earn/1"}), timeout=300) as resp, open(tmp, "wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    addrs, types = set(), {}
    for _ev, el in ET.iterparse(tmp, events=("end",)):
        if el.tag.split("}")[-1] == "id":
            it = "".join(c.text or "" for c in el if c.tag.split("}")[-1] == "idType")
            num = "".join(c.text or "" for c in el if c.tag.split("}")[-1] == "idNumber").strip()
            if it.startswith("Digital Currency Address"):
                types[it] = types.get(it, 0) + 1
                if ADDR.match(num):
                    addrs.add(num.lower())
            el.clear()
    with open(tmp, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    os.unlink(tmp)
    if not types:
        raise ValueError("the file carried no digital-currency identifiers; not written")
    summary = {"fetched": _now_iso(now), "fetched_at": round(time.time() if now is None else now, 1), "source": url, "sha256": digest,
               "id_types": types, "n_evm": len(addrs), "addresses": sorted(addrs)}
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh)
    return {k: v for k, v in summary.items() if k != "addresses"}


def sanctions_check(addr, path=None, max_age_days=7, now=None):
    """('ok'|'listed'|'unavailable', why). Fails closed: no list, an unreadable list or a stale one is 'unavailable'."""
    path = path or SANCTIONS
    now = time.time() if now is None else now
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        age_d = (now - float(d.get("fetched_at") or 0)) / 86400.0
        addrs = d.get("addresses") or []
    except (OSError, ValueError, TypeError) as e:
        return "unavailable", "sanctions list missing or unreadable (%s); run python covenant_earn.py --sanctions-refresh" % type(e).__name__
    if age_d > max_age_days:
        return "unavailable", "sanctions list is %.1f days old (limit %d); the server refreshes it, or run --sanctions-refresh" % (age_d, max_age_days)
    if str(addr).lower() in set(addrs):
        return "listed", "sanctions_screen"
    return "ok", "list %.1f days old, %d addresses" % (age_d, len(addrs))


def sanctions_age_days(path=None, now=None):
    try:
        with open(path or SANCTIONS, encoding="utf-8") as fh:
            d = json.load(fh)
        return ((time.time() if now is None else now) - float(d.get("fetched_at") or 0)) / 86400.0
    except (OSError, ValueError, TypeError):
        return None


# ------------------------------------------------------------------ the offers

def cites(text):
    """Every (path, line) the text cites, in the forms answers actually use, deduplicated in order."""
    out, seen = [], set()
    for rx in CITE_FORMS:
        for m in rx.finditer(text or ""):
            key = (m.group(1), int(m.group(2)))
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out


def _receipt_pre(body):
    text = body.get("text")
    files = body.get("files") or {}
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text (a string) is required")
    if len(text) > 100000:
        raise ValueError("text is over 100000 characters")
    if not isinstance(files, dict) or len(files) > MAX_FILES or any(not isinstance(k, str) or not isinstance(v, str) for k, v in files.items()):
        raise ValueError("files must be an object of at most %d {name: content} strings" % MAX_FILES)
    if sum(len(v) for v in files.values()) > MAX_FILES_CHARS:
        raise ValueError("files exceed %d characters in total" % MAX_FILES_CHARS)
    if body.get("numbers") not in (None, "on", "off"):
        raise ValueError("numbers must be 'on' or 'off'")


def _receipt(body, ctx):
    _receipt_pre(body)
    text, files = body["text"], body.get("files") or {}
    keyed = {}
    for name, content in files.items():
        keyed[name.replace("\\", "/").lower()] = content
        keyed.setdefault(os.path.basename(name.replace("\\", "/")).lower(), content)

    def find(rel):
        r = rel.replace("\\", "/").lower()
        return keyed.get(r) if r in keyed else keyed.get(os.path.basename(r))

    citations = []
    for rel, line in cites(text):
        content = find(rel)
        if content is None:
            citations.append({"cite": "%s:%d" % (rel, line), "verdict": "NO SUCH FILE among the files supplied"})
            continue
        total = content.count("\n") + (0 if content.endswith("\n") or not content else 1)
        if line > total:
            citations.append({"cite": "%s:%d" % (rel, line), "verdict": "OUT OF RANGE: the file has %d lines" % total})
        else:
            citations.append({"cite": "%s:%d" % (rel, line), "verdict": "ok: exists, %d lines" % total})
    quotations = []
    for para in re.split(r"\n\s*\n", text):
        cited = [rel for rel, _ln in cites(para)]
        if not cited:
            continue
        bodies = {rel: _norm(find(rel)) for rel in cited if find(rel) is not None}
        if not bodies:
            continue
        for q in QUOTE.findall(para):
            nq = _norm(q)
            hit = [rel for rel, b in bodies.items() if nq and nq in b]
            quotations.append({"quote": q[:160], "attributed_to": sorted(bodies),
                               "verdict": ("appears in %s" % ", ".join(hit)) if hit else "DOES NOT APPEAR in the file(s) it is attributed to"})
    if body.get("numbers") == "off":
        numbers = "off"
    else:
        corpus = "\n".join(files.values())
        found = sorted({n for n in NUMBER.findall(text) if not (1900 <= int(n) <= 2100)}, key=lambda x: (-len(x), x))
        absent = [n for n in found if n not in corpus][:16]
        numbers = {"checked": len(found), "in_a_supplied_file": len(found) - len([n for n in found if n not in corpus]),
                   "in_no_supplied_file": absent, "note": "informational: a number no supplied file contains may be arithmetic; it is listed, not judged wrong"}
    clean = all(c["verdict"].startswith("ok") for c in citations) and all(q["verdict"].startswith("appears") for q in quotations)
    return {"clean": bool(clean), "citations": citations, "quotations": quotations, "numbers": numbers,
            "files": {name: _sha(content) for name, content in files.items()},
            "checked": "%d citation(s) against %d supplied file(s), %d quotation(s), %s"
                       % (len(citations), len(files), len(quotations), ("numbers off" if numbers == "off" else "%d number(s)" % numbers["checked"])),
            "scope": RECEIPT_SCOPE}


def _receipt_act(body):
    text = body.get("text") if isinstance(body.get("text"), str) else ""
    files = body.get("files") if isinstance(body.get("files"), dict) else {}
    names = sorted({rel for rel, _ln in cites(text)})[:20]
    return ("receipt: check %d citation(s) in a text of %d characters against %d supplied file(s): %s"
            % (len(cites(text)), len(text), len(files), ", ".join(names) or "none"))


def _shape_pre(body):
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text (a string) is required")
    if len(text) > 20000:
        raise ValueError("text is over 20000 characters")


def _shape(body, ctx):
    _shape_pre(body)
    import covenant_screen
    import covenant_contact
    text = body["text"]
    seen = covenant_screen.normalize(text)
    flagged = sorted({m.group(0).lower() for m in covenant_contact.NOT_STRAIGHT.finditer(seen)})
    vote = ctx["gate"].decide(seen[:4000])
    return {"no_flagged_shape": bool(not flagged and vote["state"] == "clean"), "flagged": flagged,
            "normalised_differs": bool(seen != text),
            "quorum": {"vote": vote["state"], "reason": vote["message"], "seat": vote["judge"], "ms": vote.get("ms")},
            "not_a_finding": NOT_A_FINDING,
            "checked": "text of %d characters normalised (%s), %d flagged shape(s), quorum vote %s by %s"
                       % (len(text), "differs from what was sent" if seen != text else "unchanged", len(flagged), vote["state"], vote["judge"] or "no seat"),
            "method": "NFKC + confusable folding + zero-width removal + split-word joining; a fixed list of shapes; the node's quorum "
                      "(clean / violates / held) with the seat's own words."}


def _shape_act(body):
    text = body.get("text") if isinstance(body.get("text"), str) else ""
    return ("shape: judge whether a text of %d characters carries coercion, pretence or secrecy shapes; the verdict is returned "
            "and no action is taken on the text" % len(text))


def _series_for(h):
    import strategy_validate as SV
    files = SV.series_files([a.upper() for a in h["assets"]] if h["assets"] else None)
    return dict(list(files.items())[:2])


def _papertest_pre(body):
    """Bounds, known series, no money question, and TESTABLE -- all before any payment is asked for."""
    import covenant_tetsu_money as TMY
    import strategy_validate as SV
    for k, v in body.items():
        if isinstance(v, str) and MONEY_QUESTION.search(v):
            raise ValueError("we do not answer questions about anyone's money; send a rule (family, params, assets) only")
    h = {"family": body.get("family"), "params": body.get("params") or {}, "assets": body.get("assets") or None}
    if h["assets"] is not None and (not isinstance(h["assets"], list) or len(h["assets"]) > 2 or any(not isinstance(a, str) for a in h["assets"])):
        raise ValueError("assets must be a list of at most 2 symbols")
    _name, _strat, warm = TMY.build(h)
    files = _series_for(h)
    if not files:
        raise ValueError("no price series for those assets; available: %s" % ", ".join(sorted(SV.series_files())))
    short = []
    for sym, fpath in files.items():
        n = sum(1 for _ in open(fpath, encoding="utf-8")) - 1
        if n < 3 * (warm + 30):
            short.append("%s: %d bars cannot support 2 folds with warm-up %d" % (sym, n, warm))
    if len(short) == len(files):
        raise ValueError("not testable: " + "; ".join(short))
    return h, files, warm


def trials_global(trials_dir=None):
    """Every rule ever tested here: the lab's grid, the tree's own record, and every rule sent to this service."""
    import covenant_tetsu_money as TMY
    n = TMY.trials_so_far(TMY.LEDGER)
    return n + len(_rows(os.path.join(trials_dir or TRIALS_DIR, "all.jsonl")))


def base_rate(trials_dir=None):
    rows = _rows(os.path.join(trials_dir or TRIALS_DIR, "all.jsonl"))
    cleared = sum(1 for r in rows if r.get("not_refuted"))
    try:
        import covenant_tetsu_money as TMY
        own = [r for r in _rows(TMY.LEDGER) if r.get("kind") == "hypothesis"]
        own_cleared = sum(1 for r in own if r.get("survives"))
    except Exception:                                            # noqa: BLE001
        own, own_cleared = [], 0
    return {"tested_here": len(rows), "not_refuted_here": cleared, "tree_own_rules": len(own), "tree_own_not_refuted": own_cleared,
            "words": "%d rule(s) sent to this service and %d of this tree's own have been tested; %d cleared all three thresholds"
                     % (len(rows), len(own), cleared + own_cleared)}


def _papertest(body, ctx):
    import covenant_tetsu_money as TMY
    import strategy_validate as SV
    import strategy_lab as L
    h, files, warm = _papertest_pre(body)
    name, strat, warm = TMY.build(h)
    tdir = ctx.get("trials_dir") or TRIALS_DIR
    trials = trials_global(tdir) + 1
    cost = SV.CostModel(taker_fee_bps=SV.FEE_BPS, spread_bps=SV.SPREAD_BPS, slippage_bps=SV.SLIP_BPS, min_notional=SV.MIN_NOTIONAL)
    bt = SV.Backtester(cost=cost, capital=SV.CAPITAL)
    variants = [(n, s, w) for n, s, w in L.build_grid() if n.split(" ")[0] == h["family"]]
    series, any_not_refuted, any_testable = {}, False, False
    for sym, fpath in files.items():
        bars = SV.load_csv(fpath)
        try:
            r = bt.run(bars, strat, warmup=warm, label=name, strategies_tried=trials)
        except ValueError as e:
            series[sym] = {"not_testable": True, "why": str(e)[:160]}
            continue
        d = SV.deflated_sharpe(r)
        rets = {name: r.returns}
        for n, s, w in variants[:24]:
            try:
                rets[n] = bt.run(bars, s, warmup=w, label=n).returns
            except ValueError:
                continue
        p, _ns = SV.pbo(rets) if len(rets) >= 2 else (-1, 0)
        wf, folds_used = None, 5
        while wf is None and folds_used >= 2:
            try:
                wf = SV.walk_forward(bars, lambda train, _s=strat: _s, folds=folds_used, embargo_frac=0.02, cost=cost, capital=SV.CAPITAL, warmup=warm)
            except ValueError:
                folds_used -= 1
        held = sum(t.bars_held for t in r.trades)
        row = {"bars": len(bars), "warmup": warm, "trades": r.n_trades, "in_market": round(held / float(max(1, r.n_bars)), 3),
               "return": round(r.total_return, 4), "sharpe": round(r.sharpe(), 3), "deflated_sharpe": round(d["deflated_sharpe"], 4),
               "expected_max_sharpe": round(d.get("expected_max_sharpe", 0.0), 3), "trials": trials,
               "pbo": round(p, 3) if p >= 0 else None, "max_drawdown": round(r.max_drawdown(), 4)}
        if wf is None:
            row.update({"not_testable": True, "walk_forward": "UNDETERMINED: %d bars cannot support 2 folds with warm-up %d" % (len(bars), warm),
                        "verdict": "not testable on this series"})
            series[sym] = row
            continue
        any_testable = True
        row["walk_forward"] = {"folds": folds_used, "consistent": bool(wf["consistent"]), "p": round(wf["binomial_p"], 3),
                               "worst_fold": round(wf["worst_fold"], 4), "positive_folds": wf["positive_folds"]}
        ok = bool(wf["consistent"]) and d["deflated_sharpe"] >= 0.95 and 0 <= p < 0.5
        row["verdict"] = "not refuted at the thresholds" if ok else "refuted"
        row["described"] = ("Over the %d-bar %s series this rule traded %d times, was in the market %.0f%% of the time, and its worst "
                            "drawdown was %.1f%%; its Sharpe of %.2f deflated to %.2f against %d trials (a rule would need about %.2f "
                            "to clear that many); its worst walk-forward fold over %d folds returned %.1f%%; its probability of backtest "
                            "overfitting among %d variants was %s."
                            % (len(bars), sym, r.n_trades, row["in_market"] * 100, row["max_drawdown"] * 100, row["sharpe"], row["deflated_sharpe"],
                               trials, row["expected_max_sharpe"], folds_used, row["walk_forward"]["worst_fold"] * 100, len(rets),
                               ("%.2f" % p) if p >= 0 else "not measured"))
        any_not_refuted = any_not_refuted or ok
        series[sym] = row
    os.makedirs(tdir, exist_ok=True)
    with open(os.path.join(tdir, "all.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "hypothesis", "t": _now_iso(ctx.get("now")), "hypothesis": h, "not_refuted": bool(any_not_refuted),
                             "testable": bool(any_testable)}) + "\n")
    out = {"refuted": bool(any_testable and not any_not_refuted), "not_refuted_at_thresholds": bool(any_not_refuted),
           "not_testable": bool(not any_testable), "series": series, "trials_counted": trials, "base_rate": base_rate(tdir),
           "thresholds": "deflated Sharpe >= 0.95 with %d trials counted; walk-forward consistent at p <= 0.05; PBO < 0.5" % trials,
           "disclosure": DISCLOSURE_PAPERTEST,
           "checked": "three tests on %d series (%d testable), %d trials counted" % (len(files), sum(1 for s in series.values() if not s.get("not_testable")), trials),
           "method": "the rule is one of five parametric families built by this tree's lab; no code you send is executed; the cost model "
                     "and the series are the tree's own; the trial count is global (the tree's grid and record plus every rule sent here)."}
    if any_not_refuted:
        out["warning"] = ("this bar has never been cleared in this tree's own record; treat a not-refuted result as a likely false "
                          "positive until reproduced out of sample")
    return out


def _papertest_act(body):
    return ("papertest: paper-test the rule family=%s params=%s on series %s against three tests; nothing is traded and no buyer code runs"
            % (body.get("family"), json.dumps(body.get("params") or {}, sort_keys=True), body.get("assets") or "default"))


OFFERS = {
    "receipt": {
        "path": "/earn/receipt", "fn": _receipt, "pre": _receipt_pre, "act": _receipt_act,
        "description": "A citation receipt for an AI answer: which cited path:line exist in the files you supply, which quoted passages appear there, which numbers appear in no supplied file. Checks existence, not meaning.",
        "tags": ["citations", "ai-output", "receipt", "existence-check"],
        "benefit": {"gains": ["the buyer learns which of an answer's citations and quotations hold in the files supplied, before acting on them",
                              "a receipt hash-chained to a public-method ledger, so the check itself can be checked"],
                    "cost": ["the text and files are read once; the result (with short quoted fragments) is kept 24 hours for re-delivery; a reader still has to open what the receipt flags",
                             "seconds of CPU here; the price shown before payment"]},
        "example_in": {"text": "The limit is set in config.py:12 -- \"MAX_RETRIES = 5 attempts before giving up\".", "files": {"config.py": "import os\nMAX_RETRIES = 5\n"}},
        "example_out": {"clean": False, "citations": [{"cite": "config.py:12", "verdict": "OUT OF RANGE: the file has 2 lines"}],
                        "quotations": [{"quote": "MAX_RETRIES = 5 attempts before giving up", "verdict": "DOES NOT APPEAR in the file(s) it is attributed to"}],
                        "numbers": {"checked": 0, "in_a_supplied_file": 0, "in_no_supplied_file": []}, "checked": "1 citation(s) against 1 supplied file(s), 1 quotation(s), 0 number(s)"},
    },
    "shape": {
        "path": "/earn/shape", "fn": _shape, "pre": _shape_pre, "act": _shape_act,
        "description": "A message shape screen: normalised as a reader sees it, checked for coercion, pretence and secrecy shapes, voted on by a small local quorum that says when it does not know. A classification of shape, not a finding about anyone.",
        "tags": ["moderation", "message-shape", "agents", "forum"],
        "benefit": {"gains": ["a forum, inbox or agent learns whether a message carries the shapes that pretend, coerce or ask for secrecy, with the seat's reason",
                              "disguises (confusables, zero-width joins, split words) are undone before the check"],
                    "cost": ["the text is judged by the local quorum, which keeps judged text in a private audit file on the operator's computer; the judge is small and can be wrong, and says HELD when it does not know",
                             "the price shown before payment"]},
        "example_in": {"text": "Keep this between us and don't tell the operator, or else."},
        "example_out": {"no_flagged_shape": False, "flagged": ["don't tell", "keep this between", "or else"], "normalised_differs": False,
                        "quorum": {"vote": "violates", "reason": "...", "seat": "..."}, "not_a_finding": NOT_A_FINDING[:60] + "..."},
    },
    "papertest": {
        "path": "/earn/papertest", "fn": _papertest, "pre": _papertest_pre, "act": _papertest_act,
        "description": "A paper test of a trading rule you describe (five parametric families, no code) against three tests: deflated Sharpe with every rule ever tested here counted, walk-forward consistency, probability of backtest overfitting. Refuted, not refuted at the thresholds, or not testable; in the past tense; not advice.",
        "tags": ["backtest", "overfitting", "paper-test", "not-advice"],
        "benefit": {"gains": ["the buyer learns whether a rule is refuted by tests that have refuted every rule in this tree's own record, before risking money on it",
                              "every rule sent raises the bar for the next, for everyone, and the bar is printed"],
                    "cost": ["seconds of CPU on this PC; the rule's parameters are kept indefinitely, without the buyer's address, so they count as trials",
                             "a not-refuted result is paper and can still be wrong; the price shown before payment"]},
        "example_in": {"family": "sma_cross", "params": {"fast": 8, "slow": 48}, "assets": ["XRP"]},
        "example_out": {"refuted": True, "not_refuted_at_thresholds": False, "not_testable": False,
                        "series": {"XRP": {"deflated_sharpe": 0.0, "pbo": 0.86, "walk_forward": {"consistent": False, "p": 0.97}, "verdict": "refuted"}},
                        "base_rate": {"tested_here": 1, "not_refuted_here": 0}, "disclosure": DISCLOSURE_PAPERTEST[:60] + "..."},
    },
}
ROUTES = {v["path"]: k for k, v in OFFERS.items()}


def declaration(key=None):
    """What the gate reads about US: every offer's description with its gains AND cost, in plain words."""
    keys = [key] if key else sorted(OFFERS)
    parts = []
    for k in keys:
        o = OFFERS[k]
        parts.append("%s -- %s Gains: %s. Cost: %s." % (k, o["description"], "; ".join(o["benefit"]["gains"]), "; ".join(o["benefit"]["cost"])))
    return ("covenant earn sells checks for a price shown before payment; a refused or held job is not charged; "
            "nothing is traded, moved or kept beyond a hash and a 24-hour re-delivery copy. " + " ".join(parts))


# ------------------------------------------------------------------ terms

def terms_fixed(g):
    contact = (g or {}).get("contact") or "not set in the grant"
    return (
        "covenant earn -- terms\n"
        "1. What is sold. Three automated checks, each of a claim you send: receipt (" + RECEIPT_SCOPE + ") shape (" + NOT_A_FINDING + ") "
        "papertest (" + DISCLOSURE_PAPERTEST + ")\n"
        "2. Price and payment. The price is shown in the 402 answer before you pay, in USDC on the network named there. You sign a "
        "transfer authorization; a facilitator settles it to the operator's address. The operator never holds your funds.\n"
        "3. No charge. A job the gate refuses or holds, an input we refuse, a job we could not deliver: nothing is settled.\n"
        "4. Finality and re-delivery. A settled payment is final. A settled job is re-deliverable free for 24 hours: send the same "
        "input from the same paying address, or GET /earn/result/<id>. Your sole remedy is that re-delivery or the price paid.\n"
        "5. Automated and fallible. Results come from software and a small local model quorum whose error record is public in the "
        "operator's repository; the hold and refusal rates measured on this service are appended below and change daily. No warranty "
        "of accuracy or fitness. This runs on one computer with no uptime promise.\n"
        "6. What we keep. Indefinitely: your paying address, the sha256 and length of what you sent, the sha256 of what we returned, "
        "the gate's verdict on OUR act, the settlement transaction, the terms version. For 24 hours: the result, for re-delivery. "
        "A shape job's text is judged by the local quorum, which keeps judged text (up to 4,000 characters) in a private audit file "
        "on the operator's computer, never published. A receipt job's cited file NAMES reach that quorum; the contents do not. A "
        "papertest's rule parameters are kept indefinitely, without your address, so they count as trials. Send nothing you may not "
        "share, no personal data about others, and no material you have no right to submit.\n"
        "7. Sanctions. Paying addresses are screened against the US Treasury's SDN list; a listed address is refused and nothing settles.\n"
        "8. You. You are 18 or older; if you buy for a business, you buy for business use. Nothing here limits a right under New "
        "Jersey law that cannot be waived.\n"
        "9. Governing law: New Jersey, USA. Operator contact: " + contact + ".\n")


def terms_version(g):
    return _sha(terms_fixed(g))[:12]


def rates(ledger=None):
    """Per offer, from this service's own ledger: served, held, refused, and the held and refused rates. Measured, or 'no jobs yet'."""
    out = {}
    for r in _rows(ledger or LEDGER):
        if r.get("kind") != "job" or r.get("offer") not in OFFERS:
            continue
        o = out.setdefault(r["offer"], {"jobs": 0, "earned": 0, "held": 0, "refused": 0, "pending": 0, "redelivered": 0})
        o["jobs"] += 1
        st = r.get("state")
        if st == "earned":
            o["earned"] += 1
        elif st == "held":
            o["held"] += 1
        elif st in ("refused", "refused_sanctions"):
            o["refused"] += 1
        elif st == "pending":
            o["pending"] += 1
        elif st == "redelivered":
            o["redelivered"] += 1
    for k in OFFERS:
        o = out.setdefault(k, {"jobs": 0, "earned": 0, "held": 0, "refused": 0, "pending": 0, "redelivered": 0})
        o["held_rate"] = (round(o["held"] / o["jobs"], 3) if o["jobs"] else "no jobs yet")
        o["refused_rate"] = (round(o["refused"] / o["jobs"], 3) if o["jobs"] else "no jobs yet")
    return out


def terms_text(g, ledger=None):
    return terms_fixed(g) + "\nMeasured on this service (changes daily): " + json.dumps(rates(ledger), sort_keys=True) + "\nterms version " + terms_version(g) + "\n"


def privacy_text(g):
    return ("covenant earn -- privacy\n" + terms_fixed(g).split("6. What we keep. ")[1].split("\n7.")[0] +
            "\nNo account is created. No cookie is set. The operator may read a held job's parameters (never a receipt's files) to decide it. "
            "Contact: " + ((g or {}).get("contact") or "not set in the grant") + ".\n")


# ------------------------------------------------------------------ x402 shapes

def requirements(key, g):
    return {"scheme": "exact", "network": g["network"], "amount": g["prices"][key], "asset": g["asset"], "payTo": g["pay_to"],
            "maxTimeoutSeconds": TIMEOUT_S.get(key, 60), "extra": {"name": "USDC", "version": "2"}}


def resource_info(key, g, base_url):
    o = OFFERS[key]
    root = (g.get("public_url") or base_url).rstrip("/")
    return {"url": root + o["path"], "description": o["description"] + " By paying you accept " + root + "/terms (version %s)." % terms_version(g),
            "mimeType": "application/json", "serviceName": SERVICE_NAME, "tags": list(o["tags"])[:5]}


def bazaar_extension(key):
    o = OFFERS[key]
    return {"info": {"input": {"type": "http", "method": "POST", "bodyType": "json", "body": o["example_in"]},
                     "output": {"type": "json", "example": o["example_out"]}},
            "schema": {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
                       "properties": {"input": {"type": "object",
                                                "properties": {"type": {"type": "string", "const": "http"},
                                                               "method": {"type": "string", "enum": ["POST", "PUT", "PATCH"]},
                                                               "bodyType": {"type": "string", "enum": ["json", "form-data", "text"]},
                                                               "body": {"type": "object"},
                                                               "queryParams": {"type": "object", "additionalProperties": {"type": "string"}},
                                                               "headers": {"type": "object", "additionalProperties": {"type": "string"}}},
                                                "required": ["type", "method", "bodyType", "body"], "additionalProperties": False},
                                      "output": {"type": "object", "properties": {"type": {"type": "string"}, "example": {"type": "object"}},
                                                 "required": ["type"]}},
                       "required": ["input"]}}


def payment_required(key, g, base_url, error="PAYMENT-SIGNATURE header is required"):
    pr = {"x402Version": X402_VERSION, "error": error, "resource": resource_info(key, g, base_url), "accepts": [requirements(key, g)]}
    if g["network"] == MAINNET:                                   # a testnet dry run is never catalogued as if it were real
        pr["extensions"] = {"bazaar": bazaar_extension(key)}
    return pr


def _matches(accepted, reqs):
    for k in ("scheme", "network", "amount", "asset", "payTo"):
        a, r = str(accepted.get(k, "")), str(reqs.get(k, ""))
        if k in ("asset", "payTo"):
            a, r = a.lower(), r.lower()
        if a != r:
            return k
    return ""


# ------------------------------------------------------------------ the application

class App:
    """handle(method, path, headers, body_bytes, base_url) -> (status, headers, body). No socket in here, so the
    suite drives the whole flow without one; Handler below is the thin HTTP skin."""

    def __init__(self, gate=None, facilitator=None, ledger=None, grant_path=None, say=None, trials_dir=None, now=None, paused_=None,
                 sanctions_path=None, funnel_path=None, sanctions_check_=None):
        self.gate = gate or Gate()
        self._facilitator = facilitator
        self.ledger = ledger or LEDGER
        self.grant_path = grant_path or GRANT
        self.say = say
        self.trials_dir = trials_dir or TRIALS_DIR
        self.now = now
        self.paused_ = paused_ or paused
        self.sanctions_path = sanctions_path or SANCTIONS
        self.funnel_path = funnel_path or FUNNEL
        self.sanctions_check_ = sanctions_check_
        self.nonces = {str(r.get("nonce")) for r in _rows(self.ledger) if r.get("nonce")}
        self.results = {}                                        # (payer, input_sha) -> (t, result, settlement, row)
        self.by_id = {}                                          # row id -> (payer, input_sha)
        self.inflight = {}                                       # nonce -> (Event, box)
        self.clients = collections.defaultdict(collections.deque)
        self._lock = threading.Lock()
        self._workers = None
        self._workers_n = None
        self.funnel = self._load_funnel()

    # -- plumbing
    def facilitator(self, g):
        if self._facilitator is not None:
            return self._facilitator
        return Facilitator(g["facilitator_url"], auth_env=g.get("facilitator_auth_env"))

    def _t(self):
        return time.time() if self.now is None else self.now

    def _record(self, **row):
        row.setdefault("kind", "job")
        row.setdefault("t", _now_iso(self._t()))
        return _append(row, self.ledger)

    def _tell(self, text, why):
        try:
            if self.say is not None:
                return self.say(text, why)
            import covenant_contact
            return covenant_contact.say(text, why, actor="earn")
        except Exception:                                        # noqa: BLE001
            return None

    def _load_funnel(self):
        try:
            with open(self.funnel_path, encoding="utf-8") as fh:
                d = json.load(fh)
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def _funnel(self, step):
        day = time.strftime("%Y-%m-%d", time.gmtime(self._t()))
        with self._lock:
            d = self.funnel.setdefault(day, {})
            d[step] = d.get(step, 0) + 1
            try:
                os.makedirs(os.path.dirname(self.funnel_path) or ".", exist_ok=True)
                with open(self.funnel_path, "w", encoding="utf-8") as fh:
                    json.dump(self.funnel, fh, sort_keys=True)
            except OSError:
                pass

    def _client_ok(self, ip, per_minute):
        now = self._t()
        with self._lock:
            q = self.clients[ip or "?"]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= per_minute:
                return False
            q.append(now)
            return True

    def _pool(self, n):
        with self._lock:
            if self._workers is None or self._workers_n != n:
                self._workers, self._workers_n = threading.BoundedSemaphore(n), n
            return self._workers

    def allowed(self, input_sha):
        return any(r.get("kind") == "allow" and r.get("input_sha256") == input_sha for r in _rows(self.ledger))

    def design(self, key=None):
        """(state, why): ONE offer's standing with the gate -- its own declaration judged once if never judged, then
        read from the ledger. 'clean' or 'allowed' opens that offer's paid route; anything else closes it. The gate's
        refusal of one offer closes that offer and no other (measured 2026-09-25: the semantic seat convicts the
        shape offer's description on the words 'pretence' and 'pretend' -- the describe-versus-do limit -- while
        receipt and papertest are held). With key=None the answer is the best standing of any offer."""
        if key is None:
            states = {k: self.design(k) for k in OFFERS}
            for want in ("clean", "allowed", "held", "unreachable", "violates"):
                for k, (st, why) in states.items():
                    if st == want:
                        return st, why
            return "unreachable", "no offer"
        want = _sha(declaration(key))
        design = [r for r in _rows(self.ledger) if r.get("kind") == "design" and r.get("declaration_sha256") == want]
        if not design:
            design_verdict(self.gate, self.ledger, now=self._t(), key=key)
            design = [r for r in _rows(self.ledger) if r.get("kind") == "design" and r.get("declaration_sha256") == want]
        state = design[-1].get("state", "unreachable") if design else "unreachable"
        if state == "clean":
            return "clean", ""
        if state == "violates":
            return "violates", "the gate refused this offer's declaration: " + str(design[-1].get("gate", {}).get("message", ""))[:300]
        if design_allowed(self.ledger):
            return "allowed", ""
        if state == "held":
            return "held", ("the gate made no finding on this offer (held); the operator's word is needed: "
                            "python covenant_earn.py --allow-design \"why\"")
        return "unreachable", "the gate could not judge this offer: " + str(design[-1].get("gate", {}).get("message", ""))[:200]

    def _screen(self, payer, g):
        if self.sanctions_check_ is not None:
            return self.sanctions_check_(payer)
        return sanctions_check(payer, self.sanctions_path, g["sanctions_max_age_days"], now=self._t())

    def _papertest_capacity(self, g, payer):
        cap = g.get("papertest_max_payers_12mo")
        if not cap:
            return True
        cutoff = self._t() - 365 * 86400
        payers = set()
        for r in _rows(self.ledger):
            if r.get("kind") == "job" and r.get("offer") == "papertest" and r.get("state") in ("earned", "pending") and r.get("payer"):
                try:
                    if time.mktime(time.strptime(r["t"], "%Y-%m-%dT%H:%M:%SZ")) - time.timezone >= cutoff:
                        payers.add(str(r["payer"]).lower())
                except ValueError:
                    payers.add(str(r["payer"]).lower())
        return payer.lower() in payers or len(payers) < cap

    # -- GET
    def get(self, path, base_url):
        g, why = grant(self.grant_path)
        root = ((g or {}).get("public_url") or base_url).rstrip("/")
        if path in ("/", "/earn", "/earn/"):
            offers = {k: {"path": o["path"], "description": o["description"], "price_usdc": _usd((g or {}).get("prices", DEFAULT_PRICES)[k]),
                          "network": (g or {}).get("network"), "gains": o["benefit"]["gains"], "cost": o["benefit"]["cost"],
                          "example_in": o["example_in"]} for k, o in OFFERS.items()}
            return 200, {}, {"service": SERVICE_NAME, "granted": bool(g), "why_not": "" if g else why, "offers": offers,
                             "terms": root + "/terms", "privacy": root + "/privacy", "x402Version": X402_VERSION,
                             "expected_revenue": "UNDETERMINED until a request arrives"}
        if path == "/terms":
            return 200, {}, {"text": terms_text(g, self.ledger), "version": terms_version(g)}
        if path == "/privacy":
            return 200, {}, {"text": privacy_text(g), "version": terms_version(g)}
        if path == "/health":
            p, pw = self.paused_()
            return 200, {}, {"ok": True, "granted": bool(g), "paused": bool(p), "why": pw if p else ("" if g else why)}
        if path.startswith("/earn/result/"):
            rid = path.rsplit("/", 1)[-1]
            key = self.by_id.get(rid)
            hit = self.results.get(key) if key else None
            if hit and self._t() - hit[0] < RESULT_KEEP_S:
                return 200, {"PAYMENT-RESPONSE": _b64json(hit[2])} if hit[2] else {}, {"receipt": hit[3], "result": hit[1], "redelivered": True}
            return 404, {}, {"error": "no result held under that id (results are kept 24 hours)"}
        if path in ROUTES:
            key = ROUTES[path]
            if not g:
                return 503, {}, {"error": "not granted: " + why}
            pr = payment_required(key, g, base_url, error="POST with a PAYMENT-SIGNATURE header; this is the price")
            return 402, {"PAYMENT-REQUIRED": _b64json(pr)}, pr
        return 404, {}, {"error": "no such route"}

    # -- POST
    def handle(self, method, path, headers, body_bytes, base_url):
        if method == "GET":
            return self.get(path, base_url)
        if method != "POST" or path not in ROUTES:
            return 404, {}, {"error": "no such route"}
        key = ROUTES[path]
        hdr = {str(k).upper(): v for k, v in (headers or {}).items()}
        g, why = grant(self.grant_path)
        if not g:
            return 503, {}, {"error": "not granted: " + why}
        p, pw = self.paused_()
        if p:
            return 503, {}, {"error": "paused: " + (pw or "by the operator")}
        dstate, dwhy = self.design(key)
        if dstate not in ("clean", "allowed"):
            return 503, {}, {"error": "not open: " + dwhy, "design": dstate, "charged": False}
        if not self._client_ok(hdr.get("X-EARN-CLIENT", ""), g["rate_per_minute"]):
            return 429, {"Retry-After": "60"}, {"error": "more than %d requests a minute from your address" % g["rate_per_minute"]}
        if body_bytes is not None and len(body_bytes) > BODY_CAP.get(key, MAX_BODY):
            return 413, {}, {"error": "body over %d bytes for %s" % (BODY_CAP.get(key, MAX_BODY), key)}
        try:
            body = json.loads((body_bytes or b"{}").decode("utf-8") or "{}")
            if not isinstance(body, dict):
                raise ValueError("not an object")
        except (ValueError, UnicodeDecodeError) as e:
            return 400, {}, {"error": "body is not a JSON object: %s" % e}
        try:
            OFFERS[key]["pre"](body)                             # refuse what cannot be served BEFORE asking for payment
        except ValueError as e:
            self._funnel("refused_before_payment")
            return 400, {}, {"refused_input": str(e)[:400], "charged": False}
        except Exception as e:                                   # noqa: BLE001
            return 500, {}, {"error": "the pre-check failed: %s" % type(e).__name__, "charged": False}
        reqs = requirements(key, g)
        pr = payment_required(key, g, base_url)
        sig = hdr.get("PAYMENT-SIGNATURE") or hdr.get("X-PAYMENT")
        if not sig:
            self._funnel("preflight_402")
            return 402, {"PAYMENT-REQUIRED": _b64json(pr)}, pr
        try:
            payload = _unb64json(sig)
            if not isinstance(payload, dict):
                raise ValueError("not an object")
        except Exception as e:                                   # noqa: BLE001
            return 400, {}, {"error": "PAYMENT-SIGNATURE is not base64 JSON: %s" % type(e).__name__}
        if payload.get("x402Version") != X402_VERSION:
            pr2 = payment_required(key, g, base_url, error="x402Version must be %d" % X402_VERSION)
            return 402, {"PAYMENT-REQUIRED": _b64json(pr2)}, pr2
        accepted = payload.get("accepted") or {}
        bad = _matches(accepted, reqs) if isinstance(accepted, dict) else "accepted"
        if bad:
            pr2 = payment_required(key, g, base_url, error="accepted does not match the requirements: %s" % bad)
            return 402, {"PAYMENT-REQUIRED": _b64json(pr2)}, pr2
        auth = ((payload.get("payload") or {}).get("authorization") or {}) if isinstance(payload.get("payload"), dict) else {}
        nonce, payer = str(auth.get("nonce") or ""), str(auth.get("from") or "")
        if not nonce or not ADDR.match(payer):
            return 400, {}, {"error": "payload.authorization needs a nonce and a from address"}
        try:
            valid_before = int(str(auth.get("validBefore") or "0"))
        except ValueError:
            valid_before = 0
        if valid_before and valid_before < self._t():
            pr2 = payment_required(key, g, base_url, error="that authorization expired at %s" % _now_iso(valid_before))
            return 402, {"PAYMENT-REQUIRED": _b64json(pr2)}, pr2
        # ONE AUTHORIZATION, ONE OUTCOME: a second arrival of the same nonce waits and receives the first's answer.
        with self._lock:
            if nonce in self.inflight:
                ev, box = self.inflight[nonce]
                waiting = True
            else:
                ev, box = threading.Event(), {}
                self.inflight[nonce] = (ev, box)
                waiting = False
        if waiting:
            ev.wait(TIMEOUT_S.get(key, 60))
            return box.get("resp") or (503, {}, {"error": "the first arrival of that authorization has not finished", "charged": False})
        try:
            resp = self._paid(key, g, base_url, body, payload, reqs, pr, nonce, payer, valid_before)
        finally:
            box["resp"] = resp
            ev.set()
            with self._lock:
                self.inflight.pop(nonce, None)
        return resp

    def _paid(self, key, g, base_url, body, payload, reqs, pr, nonce, payer, valid_before):
        with self._lock:
            replay = nonce in self.nonces
            self.nonces.add(nonce)
        if replay:
            self._record(offer=key, state="replayed", payer=payer, amount=reqs["amount"], network=reqs["network"], nonce=nonce, why="nonce already seen")
            pr2 = payment_required(key, g, base_url, error="that authorization nonce was already presented")
            return 402, {"PAYMENT-REQUIRED": _b64json(pr2)}, pr2
        input_s = json.dumps(body, sort_keys=True, ensure_ascii=False)
        input_sha = _sha(input_s)
        base = dict(offer=key, payer=payer, amount=reqs["amount"], network=reqs["network"], nonce=nonce, input_sha256=input_sha,
                    input_len=len(input_s), terms_version=terms_version(g))
        # RE-DELIVERY: a settled (or pending) job for the same payer and input, inside 24 h, is served again and never charged again.
        hit = self.results.get((payer.lower(), input_sha))
        if hit and self._t() - hit[0] < RESULT_KEEP_S and hit[2]:
            self._funnel("redelivered")
            row = self._record(state="redelivered", of=hit[3].get("id"), **base)
            self.by_id[row["id"]] = (payer.lower(), input_sha)
            return 200, {"PAYMENT-RESPONSE": _b64json(hit[2])}, {"receipt": hit[3], "result": hit[1], "redelivered": True}
        # SANCTIONS SCREEN, before anything is verified: strict liability, so a missing or stale list refuses too.
        sst, swhy = self._screen(payer, g)
        if sst == "listed":
            self._record(state="refused_sanctions", why="sanctions_screen", **base)
            return 403, {}, {"refused": "payer not accepted", "code": "sanctions_screen", "charged": False}
        if sst != "ok":
            self._record(state="screen_unavailable", why=swhy[:200], **base)
            return 503, {}, {"error": "the payer screen is unavailable; nothing charged: " + swhy, "charged": False}
        if key == "papertest" and not self._papertest_capacity(g, payer):
            self._record(state="capacity", why="papertest_max_payers_12mo reached", **base)
            return 503, {}, {"error": "papertest is at the operator's capacity for new paying addresses this year; nothing charged", "charged": False}
        pool = self._pool(g["workers"])
        if not pool.acquire(timeout=20):
            return 429, {"Retry-After": "10"}, {"error": "busy; try again shortly", "charged": False}
        try:
            return self._serve(key, g, body, payload, reqs, pr, base, base_url, input_sha, valid_before)
        finally:
            pool.release()

    def _serve(self, key, g, body, payload, reqs, pr, base, base_url, input_sha, valid_before):
        payer = base["payer"]
        fac = self.facilitator(g)
        v = fac.verify(payload, reqs)
        if not v.get("isValid"):
            self._record(state="invalid_payment", why=str(v.get("invalidReason") or "invalid")[:200], **base)
            fail = {"success": False, "errorReason": str(v.get("invalidReason") or "invalid"), "transaction": "", "network": reqs["network"], "payer": payer}
            return 402, {"PAYMENT-RESPONSE": _b64json(fail), "PAYMENT-REQUIRED": _b64json(pr)}, {"error": "payment not valid: " + fail["errorReason"]}
        self._funnel("verified")
        # THE GATE, on THE ACT: what we are about to do, with its parameters. The declaration was judged at start.
        try:
            act = OFFERS[key]["act"](body)
        except Exception as e:                                   # noqa: BLE001
            act = "%s: (parameters unreadable: %s)" % (key, type(e).__name__)
        try:
            verdict = self.gate.decide(act)
            if not isinstance(verdict, dict) or verdict.get("state") not in ("clean", "violates", "held", "unreachable"):
                verdict = {"state": "unreachable", "message": "the gate answered in an unknown shape", "judge": "", "ms": None}
        except Exception as e:                                   # noqa: BLE001 -- a gate that raises has not said yes
            verdict = {"state": "unreachable", "message": "the gate raised %s: %s" % (type(e).__name__, str(e)[:200]), "judge": "", "ms": None}
        dstate, _dw = self.design(key)
        if verdict["state"] == "held" and self.allowed(input_sha):
            verdict = dict(verdict, state="clean", message="HELD by the gate; served on the operator's recorded --allow for this input -- " + verdict["message"])
        elif verdict["state"] == "held" and dstate == "allowed":
            verdict = dict(verdict, state="clean", message="HELD by the gate (no finding); served under the operator's recorded allowance of the offers -- " + verdict["message"])
        if verdict["state"] == "violates":
            self._record(state="refused", gate=verdict, why="the gate refused the act", **base)
            return 403, {}, {"refused": verdict["message"], "judge": verdict["judge"], "charged": False}
        if verdict["state"] == "held":
            row = self._record(state="held", gate=verdict, why="the gate made no finding; held for the operator", **base)
            self._tell("earn: a %s job was HELD by the gate, not charged (id %s, input %s). python covenant_earn.py --allow %s \"why\" serves a resubmission of that exact input."
                       % (key, row["id"], input_sha[:12], input_sha), "earn: a held job needs your eye")
            return 409, {"Retry-After": "3600"}, {
                "held": verdict["message"], "judge": verdict["judge"], "id": row["id"], "charged": False,
                "what_now": "nothing was charged; your authorization%s will not be used; the operator was told; resubmit with a fresh "
                            "authorization later, or send a different job" % ((" (valid until %s)" % _now_iso(valid_before)) if valid_before else "")}
        if verdict["state"] != "clean":
            self._record(state="gate_unreachable", gate=verdict, why="the gate could not answer", **base)
            return 503, {}, {"error": "the gate could not answer; nothing charged: " + verdict["message"], "charged": False}
        self._funnel("gated")
        # THE WORK (a copy is kept 24 h, so a settle failure or a lost answer never redoes or re-charges it).
        hit = self.results.get((payer.lower(), input_sha))
        if hit and self._t() - hit[0] < RESULT_KEEP_S:
            result = hit[1]
        else:
            try:
                result = OFFERS[key]["fn"](body, {"gate": self.gate, "payer": payer, "trials_dir": self.trials_dir, "now": self._t()})
            except ValueError as e:
                self._record(state="refused_input", gate=verdict, why=str(e)[:200], **base)
                return 400, {}, {"refused_input": str(e)[:400], "charged": False}
            except Exception as e:                               # noqa: BLE001
                self._record(state="error", gate=verdict, why="%s: %s" % (type(e).__name__, str(e)[:160]), **base)
                return 500, {}, {"error": "the work failed; nothing charged: %s" % type(e).__name__, "charged": False}
            self.results[(payer.lower(), input_sha)] = (self._t(), result, None, None)
        result_sha = _sha(json.dumps(result, sort_keys=True, ensure_ascii=False, default=str))
        # SETTLEMENT, after the work, as the authorization flow orders it.
        s = fac.settle(payload, reqs)
        tx = str(s.get("transaction") or "")
        pending = (not s.get("success")) and str(s.get("errorReason") or "") == "settlement_pending" and bool(tx)
        if not s.get("success") and not pending:
            self._record(state="unsettled", gate=verdict, result_sha256=result_sha, checked=result.get("checked", ""),
                         why="delivered but not settled: %s" % str(s.get("errorReason") or "")[:160], **base)
            fail = {"success": False, "errorReason": str(s.get("errorReason") or "settle_failed"), "transaction": tx, "network": reqs["network"], "payer": payer}
            return 402, {"PAYMENT-RESPONSE": _b64json(fail), "PAYMENT-REQUIRED": _b64json(pr)}, {
                "error": "settlement failed; the result is held for you for 24 hours -- send a fresh authorization: " + fail["errorReason"]}
        state = "pending" if pending else "earned"
        row = self._record(state=state, gate=verdict, gate_ms=verdict.get("ms"), result_sha256=result_sha, checked=result.get("checked", ""), tx=tx,
                           usd_fmv_at_settle=float(_usd(reqs["amount"])), fmv_source="USDC at par, assumed", **base)
        self._funnel("settled" if state == "earned" else "pending")
        settlement = {"success": True, "transaction": tx, "network": str(s.get("network") or reqs["network"]), "payer": payer} if state == "earned" else \
            {"success": False, "errorReason": "settlement_pending", "transaction": tx, "network": reqs["network"], "payer": payer}
        receipt = {"id": row["id"], "prev": row["prev"], "offer": key, "t": row["t"], "payer": payer, "amount_usdc": _usd(reqs["amount"]),
                   "network": reqs["network"], "transaction": tx, "settlement": state, "admission_gate": verdict, "input_sha256": input_sha,
                   "result_sha256": result_sha, "checked": result.get("checked", ""), "terms_version": terms_version(g),
                   "terms": "a refused or held job is not charged; this receipt is hash-chained to the seller's ledger; re-deliverable 24 hours at /earn/result/" + row["id"]}
        self.results[(payer.lower(), input_sha)] = (self._t(), result, settlement, receipt)
        self.by_id[row["id"]] = (payer.lower(), input_sha)
        if state == "earned" and sum(1 for r in _rows(self.ledger) if r.get("state") == "earned") == 1:
            st = status(self.ledger, self.grant_path)
            self._tell("earn: the first settled payment -- %s USDC for a %s job from %s..., tx %s; net so far %.2f against the %.0f seed. python covenant_earn.py --status has the account."
                       % (_usd(reqs["amount"]), key, payer[:10], tx[:18], st["net_usd"], st["seed_usd"]), "earn: first payment settled")
        if state == "pending":
            return 402, {"PAYMENT-RESPONSE": _b64json(settlement)}, {
                "error": "settlement pending on the chain (tx %s); the result is held for you -- send the SAME request again in 30 s and it is "
                         "delivered without a second charge" % tx[:18], "id": row["id"]}
        return 200, {"PAYMENT-RESPONSE": _b64json(settlement)}, {"receipt": receipt, "result": result}


# ------------------------------------------------------------------ the design, to the gate

def design_verdict(gate=None, ledger=None, now=None, key=None):
    """One offer's declaration (key) to the node's gate, recorded as a design row keyed to that declaration's sha256.
    With key=None: every offer, one row each, plus one row for the whole declaration in one string (for the record:
    the whole was VIOLATES on 2026-09-25 while two of its three parts were held). Returns the verdicts by offer."""
    gate = gate or Gate()
    out = {}
    for k in ([key] if key else sorted(OFFERS)):
        v = gate.decide(declaration(k))
        _append({"kind": "design", "t": _now_iso(now), "offer": k, "state": v["state"], "gate": v, "declaration_sha256": _sha(declaration(k))}, ledger or LEDGER)
        out[k] = v
    if key is None:
        v = gate.decide(declaration())
        _append({"kind": "design_all", "t": _now_iso(now), "state": v["state"], "gate": v, "declaration_sha256": _sha(declaration())}, ledger or LEDGER)
        out["all"] = v
    return out[key] if key else out


def design_allowed(ledger=None):
    """His recorded word on the offers as they stand now (keyed to the whole declaration's sha256, so a changed
    offer needs a fresh word). It reaches HELD offers only; a refused offer stays refused."""
    want = _sha(declaration())
    return any(r.get("kind") == "allow_design" and r.get("declaration_sha256") == want for r in _rows(ledger or LEDGER))


def design_states(ledger=None):
    """Per offer, the last recorded verdict on its current declaration, or 'never judged'."""
    rows = _rows(ledger or LEDGER)
    out = {}
    for k in OFFERS:
        want = _sha(declaration(k))
        hit = [r for r in rows if r.get("kind") == "design" and r.get("declaration_sha256") == want]
        out[k] = hit[-1].get("state") if hit else "never judged"
    return out


def allow_design(why, ledger=None):
    """His yes for the offers the gate HELD. Refused when every offer's last verdict is a VIOLATES (there is
    nothing a word could open); a refused offer stays refused under it either way -- a finding is not his to
    wave through here; the gate's own record is where that is argued."""
    if not str(why).strip():
        raise ValueError("an allowance carries a reason")
    states = design_states(ledger)
    if states and all(s == "violates" for s in states.values()):
        raise ValueError("the gate REFUSED every offer (findings, not holds); nothing here overrides a finding")
    return _append({"kind": "allow_design", "t": _now_iso(), "declaration_sha256": _sha(declaration()), "why": str(why)[:300],
                    "gate_states_when_allowed": states, "reaches": [k for k, s in states.items() if s == "held"]}, ledger or LEDGER)


# ------------------------------------------------------------------ the account

def cost(usd, what, ledger=None):
    """His recorded spend against the seed (a domain, a tunnel); nothing here pays anything."""
    return _append({"kind": "cost", "t": _now_iso(), "usd": round(float(usd), 2), "what": str(what)[:200]}, ledger or LEDGER)


def allow(input_sha, why, ledger=None):
    """His yes for one exact input the gate HELD; a resubmission of that input is served. A VIOLATES is never allowed here."""
    if not re.match(r"^[0-9a-f]{64}$", str(input_sha)):
        raise ValueError("input_sha256 must be 64 hex characters (from the held line)")
    if not str(why).strip():
        raise ValueError("an allowance carries a reason")
    return _append({"kind": "allow", "t": _now_iso(), "input_sha256": input_sha, "why": str(why)[:200]}, ledger or LEDGER)


def reconcile(row_id, outcome, why, ledger=None):
    """His word, from the chain explorer, on a settlement the facilitator reported pending: earned or failed."""
    if outcome not in ("earned", "failed"):
        raise ValueError("outcome must be earned or failed")
    if not str(why).strip():
        raise ValueError("a reconciliation carries a reason (the explorer's answer)")
    rows = _rows(ledger or LEDGER)
    hit = [r for r in rows if r.get("id") == row_id and r.get("kind") == "job" and r.get("state") == "pending"]
    if not hit:
        raise ValueError("no pending job row with id %s" % row_id)
    return _append({"kind": "reconcile", "t": _now_iso(), "of": row_id, "outcome": outcome, "why": str(why)[:200]}, ledger or LEDGER)


def _reconciled(rows):
    out = {}
    for r in rows:
        if r.get("kind") == "reconcile":
            out[r.get("of")] = r.get("outcome")
    return out


def status(ledger=None, grant_path=None, now=None):
    ledger = ledger or LEDGER
    rows = _rows(ledger)
    rec = _reconciled(rows)
    jobs = [r for r in rows if r.get("kind") == "job"]
    by_state = {}
    for r in jobs:
        by_state[r.get("state", "?")] = by_state.get(r.get("state", "?"), 0) + 1
    earned = [r for r in jobs if (r.get("state") == "earned" or (r.get("state") == "pending" and rec.get(r.get("id")) == "earned"))
              and r.get("result_sha256") and r.get("checked") and r.get("tx")]
    pending = [r for r in jobs if r.get("state") == "pending" and rec.get(r.get("id")) is None]
    earned_atomic = sum(int(str(r.get("amount") or 0)) for r in earned)
    by_offer = {}
    for r in earned:
        by_offer[r.get("offer")] = by_offer.get(r.get("offer"), 0) + int(str(r.get("amount") or 0))
    costs = [r for r in rows if r.get("kind") == "cost"]
    spent = round(sum(float(r.get("usd") or 0) for r in costs), 2)
    g, why = grant(grant_path or GRANT)
    seed = float((g or {}).get("seed_usd") or 0.0)
    prices = (g or {}).get("prices", DEFAULT_PRICES)
    reached = any(r.get("state") in ("earned", "unsettled", "pending") for r in jobs)
    held_open = [r for r in jobs if r.get("state") == "held" and not any(a.get("kind") == "allow" and a.get("input_sha256") == r.get("input_sha256") for a in rows)]
    ok, cwhy = chain_ok(ledger)
    per = design_states(ledger)
    dallowed = design_allowed(ledger)
    open_offers = [k for k, s in per.items() if s == "clean" or (s == "held" and dallowed)]
    dstate = ("UNDETERMINED: the offers were never put to the gate" if all(s == "never judged" for s in per.values())
              else "; ".join("%s %s" % (k, s) for k, s in sorted(per.items())))
    net = round(earned_atomic / 1e6 - spent, 6)
    break_even = {k: (int(-net * 1e6 // int(prices[k])) + 1 if net < 0 else 0) for k in OFFERS}
    try:
        with open(FUNNEL if ledger == LEDGER else os.path.join(os.path.dirname(ledger), "funnel.json"), encoding="utf-8") as fh:
            funnel = json.load(fh)
    except (OSError, ValueError):
        funnel = {}
    return {"granted": bool(g), "why_not": "" if g else why, "network": (g or {}).get("network"),
            "jobs": len(jobs), "by_state": by_state, "earned_jobs": len(earned), "earned_usd": round(earned_atomic / 1e6, 6),
            "earned_by_offer_usd": {k: round(v / 1e6, 6) for k, v in by_offer.items()},
            "pending_jobs": len(pending), "pending_note": ("UNDETERMINED until reconciled: python covenant_earn.py --reconcile <id> earned|failed \"why\"" if pending else ""),
            "seed_usd": seed, "spent_usd": spent, "net_usd": net,
            "break_even_calls": break_even, "expected_revenue": "UNDETERMINED until a request arrives",
            "facilitator": "reached" if reached else "UNDETERMINED: no settlement was ever attempted",
            "design": dstate, "design_by_offer": per, "design_allowed": dallowed, "open_offers": open_offers if g else [],
            "open": bool(g) and bool(open_offers),
            "held_open": len(held_open), "last_earned": (earned[-1].get("t") if earned else None),
            "rates": rates(ledger), "funnel": funnel, "sanctions_list_age_days": (round(sanctions_age_days(now=now), 2) if sanctions_age_days(now=now) is not None else None),
            "mainnet_checklist_missing": checklist_missing(g) if g and g.get("network") == MAINNET else [],
            "chain": "ok" if ok else cwhy, "share": (g or {}).get("share"), "terms_version": terms_version(g) if g else None}


def tax_year(year, ledger=None):
    """Gross receipts, count and recorded costs for one calendar year, from the ledger. USDC at par assumed."""
    rows = _rows(ledger or LEDGER)
    rec = _reconciled(rows)
    y = str(year)
    got = [r for r in rows if r.get("kind") == "job" and str(r.get("t", "")).startswith(y) and r.get("tx")
           and (r.get("state") == "earned" or (r.get("state") == "pending" and rec.get(r.get("id")) == "earned"))]
    costs = [r for r in rows if r.get("kind") == "cost" and str(r.get("t", "")).startswith(y)]
    return {"year": y, "receipts_count": len(got), "gross_receipts_usd": round(sum(float(r.get("usd_fmv_at_settle") or 0) for r in got), 6),
            "fmv_source": "USDC at par, assumed; disposals of the USDC are separate events he records elsewhere",
            "costs_usd": round(sum(float(r.get("usd") or 0) for r in costs), 2), "costs": [{"t": r["t"], "usd": r["usd"], "what": r["what"]} for r in costs],
            "note": "every receipt is the operator's income; the 'share' in the grant is a memo of intent with no tax effect"}


def daily_report(say=None, ledger=None, grant_path=None):
    """One line to him, only when his grant stands; nothing else is said."""
    g, _why = grant(grant_path or GRANT)
    if not g:
        return None
    st = status(ledger, grant_path)
    today = time.strftime("%Y-%m-%d", time.gmtime())
    f = st["funnel"].get(today, {})
    text = ("earn: %s; %d job(s) on record, %d earned = %.4f USDC (%s), %d pending (UNDETERMINED), %d held for your eye, net %.2f against the %.0f seed "
            "(break-even from here: %s); today %d preflight(s), %d verified, %d settled; facilitator %s; sanctions list %s; the offers: %s%s%s."
            % (("OPEN: " + ", ".join(st["open_offers"])) if st["open"] else "CLOSED", st["jobs"], st["earned_jobs"], st["earned_usd"],
               ", ".join("%s %.4f" % kv for kv in sorted(st["earned_by_offer_usd"].items())) or "none",
               st["pending_jobs"], st["held_open"], st["net_usd"], st["seed_usd"],
               ", ".join("%s %d" % kv for kv in sorted(st["break_even_calls"].items())),
               f.get("preflight_402", 0), f.get("verified", 0), f.get("settled", 0), st["facilitator"],
               ("%.1f d old" % st["sanctions_list_age_days"]) if st["sanctions_list_age_days"] is not None else "ABSENT",
               st["design"], " (allowed by you)" if st["design_allowed"] else "",
               ("; mainnet checklist unread: " + ", ".join(st["mainnet_checklist_missing"])) if st["mainnet_checklist_missing"] else ""))
    try:
        if say is not None:
            return say(text, "earn: the day's account")
        import covenant_contact
        return covenant_contact.say(text, "earn: the day's account", actor="earn")
    except Exception:                                            # noqa: BLE001
        return None


# ------------------------------------------------------------------ the HTTP skin

class Handler(BaseHTTPRequestHandler):
    server_version = "covenant-earn/1"
    protocol_version = "HTTP/1.1"
    timeout = 10                                                 # socket read timeout: a slow-loris holds nothing for long

    def log_message(self, fmt, *args):                          # one line, no client text
        sys.stderr.write("earn %s %s\n" % (self.address_string(), fmt % args))

    def _send(self, status, headers, body):
        data = json.dumps(body, ensure_ascii=False, indent=1, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Expose-Headers", "PAYMENT-REQUIRED, PAYMENT-RESPONSE")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _base(self):
        host = self.headers.get("Host") or ("%s:%d" % self.server.server_address[:2])
        return ("https://" if self.headers.get("X-Forwarded-Proto") == "https" else "http://") + host

    def _headers(self):
        h = dict(self.headers)
        h["X-Earn-Client"] = self.headers.get("CF-Connecting-IP") or self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or self.client_address[0]
        return h

    def do_GET(self):
        st, h, b = self.server.app.handle("GET", self.path.split("?")[0], self._headers(), b"", self._base())
        self._send(st, h, b)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n > MAX_BODY:
            self._send(413, {}, {"error": "body over %d bytes" % MAX_BODY})
            return
        body = self.rfile.read(n) if n else b""
        st, h, b = self.server.app.handle("POST", self.path.split("?")[0], self._headers(), body, self._base())
        self._send(st, h, b)


def startup_checks(g):
    """What must be true before a paid route is worth opening. Returns (fatal list, warning list)."""
    fatal, warn = [], []
    worst = 2 * GATE_TIMEOUT_S + 2 * FACILITATOR_TIMEOUT_S + 5
    if worst > min(TIMEOUT_S.values()):
        fatal.append("worst-case gate+facilitator time %.0f s exceeds the shortest authorization window %d s" % (worst, min(TIMEOUT_S.values())))
    if g:
        if g["network"] == MAINNET:
            for k in checklist_missing(g):
                warn.append("mainnet checklist unread: %s" % k)
            if not g.get("contact"):
                warn.append("no operator contact in the grant; the terms say 'not set'")
        if not g.get("public_url"):
            warn.append("no public_url in the grant; the 402 names the host the request arrived on")
    return fatal, warn


def _keeper(app, stop):
    """The server's own hands: refresh the sanctions list when stale, say the day's line once a day, once."""
    last_report_day = None
    while not stop.is_set():
        try:
            g, _w = grant(app.grant_path)
            if g:
                age = sanctions_age_days(app.sanctions_path)
                if age is None or age > max(0.5, g["sanctions_max_age_days"] - 1):
                    try:
                        sanctions_refresh(app.sanctions_path)
                        print("earn: sanctions list refreshed", flush=True)
                    except Exception as e:                       # noqa: BLE001
                        print("earn: sanctions refresh FAILED: %s: %s" % (type(e).__name__, str(e)[:160]), flush=True)
                day = time.strftime("%Y-%m-%d", time.gmtime())
                if day != last_report_day and time.gmtime().tm_hour >= 12:
                    last_report_day = day
                    daily_report(say=app.say, ledger=app.ledger, grant_path=app.grant_path)
        except Exception as e:                                   # noqa: BLE001
            print("earn: keeper error %s: %s" % (type(e).__name__, str(e)[:160]), flush=True)
        stop.wait(600)


def serve(port=DEFAULT_PORT, host="0.0.0.0", app=None, block=True):
    """Long-lived. The offers are put to the gate first; a VIOLATES refuses to start. Returns the server."""
    try:
        import covenant_quiet
        covenant_quiet.install()
    except Exception:                                            # noqa: BLE001
        pass
    app = app or App()
    vs = design_verdict(app.gate, app.ledger)
    for k in sorted(OFFERS):
        print("earn: %s to the gate -> %s (%s) %s" % (k, vs[k]["state"], vs[k]["judge"], vs[k]["message"][:140]), flush=True)
    print("earn: the whole declaration in one string -> %s" % vs["all"]["state"], flush=True)
    refused = [k for k in OFFERS if vs[k]["state"] == "violates"]
    if len(refused) == len(OFFERS):
        print("earn: NOT STARTED -- the gate refused every offer; the verdicts are recorded and are not overridden here", flush=True)
        app._tell("earn: the gate REFUSED every offer; the server did not start. The verdicts are in the ledger.", "earn: the offers were refused")
        return None
    g, why = grant(app.grant_path)
    fatal, warn = startup_checks(g)
    for w in warn:
        print("earn: WARNING %s" % w, flush=True)
    if fatal:
        for f in fatal:
            print("earn: NOT STARTED -- %s" % f, flush=True)
        return None
    closed = {k: app.design(k) for k in OFFERS}
    shut = {k: v for k, v in closed.items() if v[0] not in ("clean", "allowed")}
    if shut:
        for k, (st, dwhy) in sorted(shut.items()):
            print("earn: %s CLOSED (%s) -- %s" % (k, st, dwhy), flush=True)
        app._tell("earn: offers closed by the gate -- %s. %s" % (", ".join("%s %s" % (k, v[0]) for k, v in sorted(shut.items())),
                                                                  next((v[1] for v in shut.values() if v[0] == "held"), "a refusal is not overridden here")),
                  "earn: the offers need your word")
    print("earn: grant %s" % ("stands (pay_to %s..., %s)" % (g["pay_to"][:10], g["network"]) if g else "absent: " + why + " -- paid routes answer 503 until it is written"), flush=True)
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    srv.app = app
    stop = threading.Event()
    srv.keeper_stop = stop
    threading.Thread(target=_keeper, args=(app, stop), daemon=True).start()
    print("earn: serving on %s:%d (GET / for the terms and prices)" % (host, port), flush=True)
    if block:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            srv.server_close()
    return srv


# ------------------------------------------------------------------ CLI

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="covenant earn -- checks for a price, every job through the gate, running on its own")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--design", action="store_true", help="put the offers' declaration to the node's gate now")
    ap.add_argument("--allow-design", metavar="WHY", help="his yes for the offers themselves when the gate HELD them; never overrides a refusal")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--report", action="store_true", help="the day's one line to him on the direct line")
    ap.add_argument("--cost", nargs=2, metavar=("USD", "WHAT"), help="record a spend against the seed")
    ap.add_argument("--allow", nargs=2, metavar=("INPUT_SHA256", "WHY"), help="his yes for one input the gate HELD")
    ap.add_argument("--reconcile", nargs=3, metavar=("ROW_ID", "OUTCOME", "WHY"), help="his word on a pending settlement: earned|failed")
    ap.add_argument("--sanctions-refresh", action="store_true", help="fetch the OFAC SDN list now")
    ap.add_argument("--tax-year", metavar="YYYY", help="gross receipts and costs for one year")
    a = ap.parse_args(argv)
    if a.allow_design:
        r = allow_design(a.allow_design)
        print("recorded: your word reaches the held offers %s (row %s); the gate's states when allowed: %s"
              % (", ".join(r["reaches"]) or "none", r["id"], json.dumps(r["gate_states_when_allowed"])))
        return 0
    if a.cost:
        r = cost(a.cost[0], a.cost[1])
        print("recorded: $%.2f %s (row %s)" % (r["usd"], r["what"], r["id"]))
        return 0
    if a.allow:
        r = allow(a.allow[0], a.allow[1])
        print("recorded: allowance for %s (row %s)" % (r["input_sha256"][:12], r["id"]))
        return 0
    if a.reconcile:
        r = reconcile(a.reconcile[0], a.reconcile[1], a.reconcile[2])
        print("recorded: %s reconciled as %s (row %s)" % (r["of"], r["outcome"], r["id"]))
        return 0
    if a.sanctions_refresh:
        t0 = time.time()
        s = sanctions_refresh()
        print(json.dumps(s, indent=1))
        print("refreshed in %.1f s" % (time.time() - t0))
        return 0
    if a.tax_year:
        print(json.dumps(tax_year(a.tax_year), indent=1))
        return 0
    if a.design:
        t0 = time.time()
        vs = design_verdict()
        print(json.dumps(vs, indent=1))
        print("gate answered in %.1f s" % (time.time() - t0))
        return 0 if all(v["state"] == "clean" for k, v in vs.items() if k != "all") else 2
    if a.report:
        r = daily_report()
        print("said" if r else "nothing said (no grant, or the line refused)")
        return 0
    if a.serve:
        return 0 if serve(a.port, a.host) is not None else 2
    print(json.dumps(status(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
