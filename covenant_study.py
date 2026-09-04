#!/usr/bin/env python3
"""covenant_study.py -- the covenant reads the moral traditions and turns what
it finds into cases it can be judged on.

WHY (asked 2026-09-04: "study all philosophy and religious texts and
teachings", "learn from all useable science and tech to improve repeatedly",
and "we can't be reliant on other companies")

  The student judge learns from ops/verdicts.jsonl and nothing else. Its
  material so far is what a teacher model invented plus what I wrote by hand.
  Both are narrow, and both are somebody's opinion. The moral traditions are
  the widest source of stated principle there is, they are public domain, and
  they cost nothing to read.

  So: fetch the texts, extract the PRECEPTS (the sentences that actually tell
  someone to do or not do something), and hand each precept to the covenant's
  teacher to turn into two transactions -- one that violates it and one that
  honours it -- which are then judged BLIND, exactly as covenant_distill.py
  already does, and kept only where the blind verdict matches the intent.

WHAT IS LOCAL AND WHAT IS NOT

  Fetching is one HTTP GET per book from Project Gutenberg, cached on disk, so
  it happens once. EXTRACTION IS ENTIRELY LOCAL -- no model, no network, plain
  Python over the text. That is the part that would otherwise be expensive,
  and it is the part the covenant does for itself. Only the last step, turning
  a precept into transactions, needs a model, and it uses whichever teacher
  covenant_distill is configured for.

WHAT IT REFUSES TO DO

  It does not train on the texts. A bag of words fitted to scripture would
  learn the vocabulary of a translation, not a principle -- "thou" is not
  evidence of anything. Only the generated, blind-judged TRANSACTIONS reach
  the ledger, and every one carries the precept and the book it came from.

  It does not decide which tradition is right. A precept is recorded as what
  a text says, with its source, and the disagreements are kept: two traditions
  that contradict each other both go in, and the judging step is what settles
  whether a given transaction is a violation.

USE
  python covenant_study.py --list                  # the reading list
  python covenant_study.py --fetch [--limit N]     # download and cache
  python covenant_study.py --extract               # precepts -> ops/study/PRECEPTS.jsonl
  python covenant_study.py --report                # what has been read, by tradition
LICENCE: public domain. The texts are too; that is why they were chosen.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "private", "study")          # gitignored: 20 MB of public text
OUT = os.path.join(HERE, "ops", "study")
PRECEPTS = os.path.join(OUT, "PRECEPTS.jsonl")
REPORT = os.path.join(OUT, "STUDY.md")

# The reading list. Public domain, Project Gutenberg ids, chosen for breadth of
# TRADITION rather than agreement: the point is not one ethic but many, because
# a principle that only one tradition states is a principle the judge should
# know is contested.
# Three ids left this list on 2026-09-04 because the files behind them are not
# what the id was believed to be: 7147 is "The French in the Heart of America",
# 2412 is Aristotle's "Categories" (logic, not ethics) and 17529 is "Othello".
# They were caught by verify(), not by reading. Two more were relabelled to what
# their files actually say. A source that cannot be checked is not a source.
BOOKS = [
    (10, "The Bible, King James Version", "hebrew-christian"),
    (2800, "The Koran (Rodwell translation)", "islamic"),
    (2388, "The Bhagavad Gita", "hindu"),
    (2680, "Meditations", "stoic"),
    (10661, "A Selection from the Discourses of Epictetus with the Encheiridion", "stoic"),
    (4280, "The Critique of Pure Reason", "kantian"),
    (5682, "The Fundamental Principles of the Metaphysic of Morals", "kantian"),
    (8438, "The Ethics of Aristotle (Nicomachean)", "aristotelian"),
    (1497, "The Republic", "platonic"),
    (3330, "The Analects of Confucius", "confucian"),
    (216, "The Tao Teh King (Tao Te Ching)", "taoist"),
    (11224, "Utilitarianism (Mill)", "utilitarian"),
    (34901, "On Liberty", "liberal"),
    (1232, "The Prince", "machiavellian"),
    (3207, "Leviathan", "hobbesian"),
    (7370, "Second Treatise of Government", "lockean"),
    (4363, "Beyond Good and Evil", "nietzschean"),
    (1080, "A Modest Proposal", "satire"),
    (3300, "The Wealth of Nations", "smithian"),
]

UA = {"User-Agent": "covenant-study/1 (public-domain texts; one fetch, cached)"}

# The covenant's own governing documents. Lawrence wrote these, they are in the
# repository, and they are the one source whose attribution is not in doubt.
#
# WHAT WAS TRIED FIRST AND REJECTED, 2026-09-04. He asked that his AI accounts
# and social media be used to learn from. The material already collected is
# private/njest1987_videos/text/*.md -- 105 OCR transcripts of screen
# recordings of his own chats. Reading them: the OCR is heavy ("thqrp's a real
# intonal critique", "vvoik"), and the speaker labels are themselves OCR
# guesses -- "Me", "Them", "?", "Peace.:", "Thought process:" -- so a line
# cannot be reliably attributed to him rather than to the model he was talking
# to. Training an ethics judge on that would teach it OCR noise and put words
# in his mouth, or the model's words in his. The right source for his voice is
# the text he actually wrote and committed.
OWN_DOCS = [
    ("CONTRIBUTING.md", "covenant"),
    (os.path.join("docs", "CONSTITUTION.md"), "covenant"),
    (os.path.join("docs", "GOVERNANCE.md"), "covenant"),
]

# A precept is a sentence that tells someone to do or not do something. These
# are the shapes that survived reading the output: deontic modals, imperatives
# of prohibition, and explicit statements of what is right or wrong. Everything
# else in a book of philosophy is argument, and argument is not a rule.
PROHIBIT = re.compile(
    r"\b(shall not|shalt not|must not|ought not|should not|do not|don't|never|"
    r"let no man|no one (?:should|ought|may)|it is (?:wrong|unjust|evil|wicked) to|"
    r"forbidden|unlawful to)\b", re.I)
OBLIGE = re.compile(
    r"\b(shall|shalt|must|ought to|should|let (?:him|us|them)|it is (?:right|just|good|our duty) to|"
    r"we are bound to|thou shalt)\b", re.I)
# The sentence has to be about what this judge actually judges: value moving
# between people, and honesty about it. The first filter used any
# other-regarding word at all and returned Kant on causation and Smith on the
# silver content of the livre -- true sentences, and not rules about conduct.
# MEASURED 2026-09-04: of the first 1795 extracted that way, a hand sample of
# 12 held 4 genuine precepts. Both a DEONTIC marker and a TRANSFER term are
# now required, and the argument words that marked the false positives are
# excluded outright.
TRANSFER = re.compile(
    r"\b(debt|debtor|creditor|wages?|hire[ds]?|lend|lent|lends|borrow(?:ed|s)?|usury|"
    r"interest|money|silver|gold|price|pay|paid|payment|weight|measure|balance|"
    r"steal|stole|stolen|theft|thief|rob|robbed|defraud|fraud|cheat|deceive|"
    r"deceit|false witness|oath|vow|promise|pledge|trade|buy|bought|sell|sold|"
    r"gift|alms|charity|tithe|offering|lend|loan|property|goods|possessions?|"
    r"owe[sd]?|owing|wealth|riches|poor|needy|widow|orphan|stranger|servant|hire)\b", re.I)
# Marks of argument rather than rule. A sentence explaining WHY is not a
# precept, and generating a transaction from it produces nonsense.
ARGUMENT = re.compile(
    r"\b(therefore|for instance|for example|in other words|it follows|hence|"
    r"thus we|philosoph|metaphysic|proposition|syllogism|hypothesis|"
    r"chapter|footnote|preface|translat)\b", re.I)
# Ritual, cultic and household-law vocabulary. These sentences pass the
# transfer filter because they mention silver, servants, payment or measures,
# and they are not rules a TRANSFER can break. MEASURED 2026-09-04: the first
# precepts handed to the teacher were Levitical, and it dutifully wrote
# "Bought a slave to work on a farm" and "Skipped circumcision for a child
# born at home" as ledger memos. The gate's own prompt already says a transfer
# cannot break the Sabbath or make a carved image; the extractor has to know
# it too, or it feeds the judge a world it will never see.
RITUAL = re.compile(
    r"\b(circumcis|sacrific|burnt offering|meat offering|sin offering|altar|"
    r"priest|levite|tabernacle|sanctuary|unclean|leaven|unleaven|holy convocation"
    r"|atonement|anoint|incense|vow unto the lord|firstborn|tithe of the herd|"
    r"sabbath|jubile|passover|idol|graven|sabbaths|congregation of israel|"
    r"bondman|bondmaid|concubine|slave|slaves|stoned|put to death)\b", re.I)
VERSE = re.compile(r"^\s*\d+[:.]\d+\s*")
_SENT = re.compile(r"(?<=[.;:!?])\s+")


def book_path(gid):
    return os.path.join(CACHE, "pg%d.txt" % gid)


def fetch(gid, title, say=print):
    p = book_path(gid)
    if os.path.exists(p) and os.path.getsize(p) > 20000:
        return "cached"
    for url in ("https://www.gutenberg.org/cache/epub/%d/pg%d.txt" % (gid, gid),
                "https://www.gutenberg.org/files/%d/%d-0.txt" % (gid, gid)):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if len(data) < 20000:
                continue
            os.makedirs(CACHE, exist_ok=True)
            with open(p, "wb") as fh:
                fh.write(data)
            return "fetched %.1f MB" % (len(data) / 1048576.0)
        except Exception as e:                                   # noqa: BLE001
            last = "%s: %s" % (type(e).__name__, str(e)[:60])
    return "FAILED (%s)" % last


def declared_title(gid):
    """What the file itself says it is. Gutenberg ids are easy to get wrong and
    a wrong one is silent: id 11800 was on this list as Utilitarianism and is
    in fact 'U.S. Copyright Renewals 1950-1977', 31 MB of catalogue that
    produced 12 'precepts' reading 'What every expectant mother should know'.
    A source that cannot be checked is not a source."""
    try:
        with open(book_path(gid), encoding="utf-8", errors="replace") as fh:
            head = fh.read(4000)
    except OSError:
        return None
    m = re.search(r"^\s*Title:\s*(.+)$", head, re.M)
    if m:
        return m.group(1).strip()
    m = re.search(r"Project Gutenberg eBook of ([^\n\r]+)", head)
    return m.group(1).strip() if m else None


def title_matches(claimed, declared):
    if not declared:
        return False
    a = set(re.findall(r"[a-z]{4,}", claimed.lower()))
    b = set(re.findall(r"[a-z]{4,}", declared.lower()))
    return bool(a & b)


def verify(say=print):
    ok, bad = [], []
    for gid, title, tradition in BOOKS:
        d = declared_title(gid)
        if d is None:
            say("  %-6d %-46s NOT FETCHED" % (gid, title[:46])); continue
        if title_matches(title, d):
            ok.append(gid)
        else:
            bad.append((gid, title, d))
            say("  %-6d %-46s MISMATCH -- the file says %r" % (gid, title[:46], d[:60]))
    say("%d of %d cached file(s) are the book claimed; %d mismatch(es)"
        % (len(ok), len(ok) + len(bad), len(bad)))
    return ok, bad


def strip_boilerplate(text):
    """Gutenberg's licence header and footer are not the book."""
    a = text.find("*** START OF")
    if a >= 0:
        text = text[text.find("\n", a) + 1:]
    b = text.find("*** END OF")
    if b >= 0:
        text = text[:b]
    return text


def precepts_in(text, max_len=240, min_len=40):
    """Sentences that state a RULE about value moving between people."""
    text = re.sub(r"\s+", " ", strip_boilerplate(text))
    out = []
    for s in _SENT.split(text):
        s = VERSE.sub("", s.strip())
        if not (min_len <= len(s) <= max_len):
            continue
        if not TRANSFER.search(s) or ARGUMENT.search(s) or RITUAL.search(s):
            continue
        if PROHIBIT.search(s):
            out.append((s, "prohibition"))
        elif OBLIGE.search(s):
            out.append((s, "obligation"))
    return out


def extract(limit_per_book=400, say=print):
    os.makedirs(OUT, exist_ok=True)
    _ok, bad = verify(say=lambda *_a, **_k: None)
    skip = {gid for gid, _t, _d in bad}
    if skip:
        say("  skipping %d file(s) whose content is not the book claimed: %s"
            % (len(skip), sorted(skip)))
    seen = set()
    if os.path.exists(PRECEPTS):
        with open(PRECEPTS, encoding="utf-8") as fh:
            for line in fh:
                try:
                    seen.add(json.loads(line)["text"])
                except (ValueError, KeyError):
                    pass
    total, per = 0, []
    with open(PRECEPTS, "a", encoding="utf-8") as fh:
        for gid, title, tradition in BOOKS:
            p = book_path(gid)
            if gid in skip or not os.path.exists(p):
                per.append((title, "skipped" if gid in skip else "not fetched", 0)); continue
            with open(p, encoding="utf-8", errors="replace") as bf:
                found = precepts_in(bf.read())
            n = 0
            for s, kind in found:
                if s in seen or n >= limit_per_book:
                    continue
                seen.add(s); n += 1
                fh.write(json.dumps({"text": s, "kind": kind, "book": title,
                                     "tradition": tradition, "gutenberg": gid},
                                    ensure_ascii=False) + "\n")
            per.append((title, tradition, n)); total += n
            say("  %-52s %-16s %4d precept(s)" % (title[:52], tradition, n))
    say("%d new precept(s) -> %s" % (total, PRECEPTS))
    return total, per


def extract_own(say=print):
    """Precepts from the covenant's own documents. Same local extractor, same
    filter, so a sentence of argument in CONSTITUTION.md is dropped exactly as
    one in Leviathan is."""
    os.makedirs(OUT, exist_ok=True)
    seen = {p["text"] for p in load_precepts()}
    total = 0
    with open(PRECEPTS, "a", encoding="utf-8") as fh:
        for rel, tradition in OWN_DOCS:
            p = os.path.join(HERE, rel)
            if not os.path.exists(p):
                say("  %-32s missing" % rel); continue
            with open(p, encoding="utf-8", errors="replace") as df:
                found = precepts_in(df.read())
            n = 0
            for text, kind in found:
                if text in seen:
                    continue
                seen.add(text); n += 1
                fh.write(json.dumps({"text": text, "kind": kind, "book": rel,
                                     "tradition": tradition, "gutenberg": None},
                                    ensure_ascii=False) + "\n")
            say("  %-32s %-10s %3d precept(s)" % (rel, tradition, n))
            total += n
    say("%d precept(s) from the covenant's own documents" % total)
    return total


def load_precepts(path=PRECEPTS):
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def report(say=print):
    ps = load_precepts()
    by_t, by_k = {}, {}
    for p in ps:
        by_t[p.get("tradition", "?")] = by_t.get(p.get("tradition", "?"), 0) + 1
        by_k[p.get("kind", "?")] = by_k.get(p.get("kind", "?"), 0) + 1
    lines = ["# What the covenant has read", "",
             "Public-domain moral texts, read locally: the extraction uses no model and no",
             "network. A precept is a sentence stating a rule about conduct toward another",
             "person; argument is not a rule and is not kept. The texts themselves are never",
             "trained on -- only the transactions generated from these precepts and judged",
             "blind (covenant_distill.py) reach the ledger.", "",
             "%d precept(s) from %d book(s), %s" % (len(ps), len({p.get("book") for p in ps}),
                                                    time.strftime("%Y-%m-%d")), "",
             "| tradition | precepts |", "|---|---|"]
    for t, n in sorted(by_t.items(), key=lambda x: -x[1]):
        lines.append("| %s | %d |" % (t, n))
    lines += ["", "| kind | count |", "|---|---|"]
    for k, n in sorted(by_k.items(), key=lambda x: -x[1]):
        lines.append("| %s | %d |" % (k, n))
    os.makedirs(OUT, exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    say("\n".join(lines[6:]))
    say("\nwritten to %s" % REPORT)
    return len(ps)


# ---------------------------------------------------------------- generation
# A precept becomes two transactions: one that breaks it and one that keeps it.
# The teacher writes them, then judges them BLIND in a separate call, and only
# the pair whose blind verdict matches the intent is kept. That is the same
# discipline covenant_distill.py uses, and it is what makes a noisy extractor
# safe: a sentence that was never really a rule produces a pair the judge will
# not confirm, and it lands in ops/distill_rejected.jsonl with both answers.
def generate(limit=8, say=print):
    import covenant_distill as X
    import covenant_unified_v8 as cov
    import covenant_judge_fallback as FB
    done = set()
    try:
        with open(X.VERDICTS, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                    if d.get("precept"):
                        done.add(d["precept"])
                except ValueError:
                    pass
    except OSError:
        pass
    # Prohibitions first. An obligation ("thou shalt pay him his hire") turns
    # into two honest-looking memos and the blind judge clears both, so the
    # pair adds a clean case and no violation. A prohibition is the precept
    # that actually teaches the judge what a violation looks like, and they
    # are the scarcer kind: 210 of the first 1180 extracted.
    unused = [p for p in load_precepts() if p["text"] not in done]
    # ROUND-ROBIN ACROSS TRADITIONS. In file order the first 400 precepts are
    # all from one book, so a batch -- and then a night of batches -- would be
    # one tradition's household law and nothing else. Taking one from each
    # tradition in turn means every batch is a contrast between them, which is
    # the whole reason for reading more than one. Prohibitions still come
    # first inside each tradition: an obligation yields two honest memos and
    # teaches the judge nothing about what a violation looks like.
    by_tradition = {}
    for p in unused:
        by_tradition.setdefault(p.get("tradition", "?"), []).append(p)
    for group in by_tradition.values():
        group.sort(key=lambda p: 0 if p.get("kind") == "prohibition" else 1)
    todo, order = [], sorted(by_tradition)
    while len(todo) < limit and any(by_tradition[t] for t in order):
        for t in order:
            if by_tradition[t] and len(todo) < limit:
                todo.append(by_tradition[t].pop(0))
    if not todo:
        say("no unused precepts"); return 0, 0
    listing = "\n".join("%d. [%s, %s] %s" % (i, p["tradition"], p["kind"], p["text"])
                         for i, p in enumerate(todo))
    prompt = ("Below are %d precepts taken from public-domain moral texts. For EACH, write two "
              "first-person transaction memos for a small value-transfer ledger, 8-30 words each, "
              "concrete and modern: one that VIOLATES the precept and one that HONOURS it. If a "
              "numbered line is not really a rule about value moving between people, return null "
              "for that number instead of inventing one.\n%s\n"
              "Answer ONLY JSON: {\"pairs\": [{\"n\": <number>, \"violating\": \"...\", "
              "\"honouring\": \"...\"}, ...]}" % (len(todo), listing))
    pref = os.environ.get("COVENANT_DISTILL_TEACHER", "auto").lower()
    use_gh = pref == "github" or (pref == "auto" and not X.ollama_up())
    if use_gh:
        import covenant_github_judge as gh
        ans = gh.ask(prompt, "You write test cases for an ethics judge. JSON only.",
                     json_only=True, timeout=900)
        raw, who = ans.get("content", ""), "github-actions/%s" % ans.get("model")
    else:
        res = X._post("/api/chat", {"model": X.TEACHER, "stream": False, "format": "json",
                                    "think": False,
                                    "options": {"temperature": 0.8, "num_predict": 1600,
                                                "num_ctx": 8192},
                                    "messages": [{"role": "user", "content": prompt}]}, 900)
        raw, who = (res.get("message") or {}).get("content", ""), "ollama/%s" % X.TEACHER
    try:
        pairs = json.loads(raw).get("pairs", [])
    except (ValueError, AttributeError):
        say("teacher (%s) returned no usable JSON" % who); return 0, 0
    cases = []
    for pr in pairs:
        try:
            i = int(pr.get("n"))
        except (TypeError, ValueError):
            continue
        if not (0 <= i < len(todo)):
            continue
        for key, expect in (("violating", True), ("honouring", False)):
            m = str(pr.get(key) or "").strip()
            if 3 <= len(m.split()) <= 60:
                cases.append({"message": m, "expect": expect, "precept": todo[i]})
    if not cases:
        say("teacher (%s) produced no usable pairs" % who); return 0, 0
    principles = list(cov.DIVINE_PRINCIPLES)
    if use_gh:
        verdicts, jm = X.gh_blind_judge([{"message": c["message"]} for c in cases], principles)
        judge = "github-actions/%s" % jm
    else:
        j = X.blind_judge()[0]
        verdicts, judge = {}, "ollama/%s" % X.TEACHER
        for i, c in enumerate(cases):
            r = j.evaluate({"message": c["message"], "origin": "organic"}, principles)
            if not getattr(r, "infrastructure_failure", False):
                verdicts[i] = (bool(r.violates), (r.reasoning or "")[:240])
    # A PAIR IS KEPT OR DROPPED WHOLE. Measured on the first pass: 24 kept and
    # 24 rejected, and the split was not random -- the honouring half of nearly
    # every pair was confirmed and the violating half was not, because a
    # teacher asked for "a memo that violates 'pay the labourer his hire'"
    # writes something like "I will not include you in the bonus pool", which
    # an honest judge correctly calls clean. Keeping the confirmed halves alone
    # fed the ledger almost pure CLEAN, and the next candidate decided 9 of 37
    # where the model in use decided 24, so the promotion rule refused it as
    # vaguer. The rule caught the drift; this stops causing it.
    #
    # A precept teaches by CONTRAST. If the teacher cannot produce a violation
    # this judge recognises, the precept taught nothing, and its honest half is
    # not free -- it is a thumb on the scale. So both halves go in together or
    # neither does, and the ledger cannot drift toward clean by construction.
    by_precept = {}
    for i, c in enumerate(cases):
        by_precept.setdefault(c["precept"]["text"], []).append((i, c))
    kept = rejected = 0
    os.makedirs(os.path.dirname(X.VERDICTS), exist_ok=True)
    for ptext, group in by_precept.items():
        confirmed = [(i, c) for i, c in group
                     if i in verdicts and verdicts[i][0] == c["expect"]]
        whole = (len(group) == 2 and len(confirmed) == 2)
        for i, c in group:
            v, why = verdicts.get(i, (None, "the judge did not answer for this one"))
            rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "text": FB._payload_text({"message": c["message"], "origin": "organic"}),
                   "judge": judge, "precept": ptext,
                   "tradition": c["precept"]["tradition"], "book": c["precept"]["book"],
                   "reason": why}
            if whole:
                rec["violates"] = bool(v)
                rec["source"] = "study"
                with open(X.VERDICTS, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                kept += 1
            else:
                rec["written_as"] = c["expect"]
                rec["judged"] = v
                rec["held"] = False
                rec["dropped_with_its_pair"] = True
                with open(X.REJECTED, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                rejected += 1
        say("    %s [%s] %s" % ("PAIR KEPT " if whole else "pair dropped",
                                group[0][1]["precept"]["tradition"], ptext[:88]))
    say("study: %d precept(s) -> %d case(s) kept as whole pairs, %d dropped (teacher %s)"
        % (len(todo), kept, rejected, judge))
    return kept, rejected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--extract", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--own", action="store_true", help="extract precepts from the covenant's own documents")
    ap.add_argument("--generate", type=int, metavar="N", help="turn N unused precepts into judged transactions")
    ap.add_argument("--limit", type=int, default=len(BOOKS))
    a = ap.parse_args()
    if a.list or not (a.fetch or a.extract or a.report or a.verify or a.generate or a.own):
        print("%d books on the reading list:" % len(BOOKS))
        for gid, title, tradition in BOOKS:
            state = "cached" if os.path.exists(book_path(gid)) else "-"
            print("  %-6d %-52s %-16s %s" % (gid, title[:52], tradition, state))
        return 0
    if a.verify:
        verify()
    if a.fetch:
        for gid, title, tradition in BOOKS[:a.limit]:
            print("  %-52s %s" % (title[:52], fetch(gid, title)))
            time.sleep(1.0)                                      # be a good guest
    if a.extract:
        extract()
    if a.own:
        extract_own()
    if a.generate:
        generate(a.generate)
    if a.report:
        report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
