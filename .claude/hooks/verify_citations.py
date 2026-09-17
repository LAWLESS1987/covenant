#!/usr/bin/env python3
"""verify_citations.py -- a Stop hook that refuses a reply citing a file:line
that cannot be true.

WHY THIS EXISTS. On 2026-09-16 I told the operator that
"PEDERSEN_2026-09-14.md:1 reads ..." and quoted it as verification before
sending two letters to third parties. That path does not exist. I had run
`grep -o`, which strips the real filename, and read text that happened to sit
INSIDE the matched string as if it were a `path:N:` prefix. The quote was real;
the provenance was invented. His instruction: "ensure silly mistakes stop
happening, details matter." A rule in memory binds only the next session that
reads it. This binds every reply.

WHAT IT CHECKS, and only this: every `path:line` in the final assistant message.
  * the path must exist, relative to cwd (or absolute)
  * the file must actually have that many lines
Either failure blocks the turn and names the citation.

WHAT IT DELIBERATELY DOES NOT DO. It does not flag a bare path with no line
number -- "I'll create foo.py" is not a citation and a guard that convicts it
would cry wolf, and a guard that cries wolf gets switched off (the same
reasoning docs/RETRACTED.json gives for its own patterns). It does not block
when a cited file exists and the line is in range but no tool call this session
touched it: transcripts are compacted, so that check has false positives it
cannot distinguish from the real thing. It reports that case only as a note
beside a block that has already been earned on other grounds.

It cannot catch the second error of that day either: completing a truncated
match from a file that DOES exist. Nothing here reads intent. That one stays a
rule in memory.

FAILURE POSTURE: any error inside this hook exits 0. A broken verifier must not
be able to wedge the session -- it fails open, loudly, on stderr.

Escape hatch: .claude/hooks/cite_allow.txt, one path per line (# comments ok),
for paths named as EXAMPLES rather than cited. Kept deliberately short.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOW_FILE = os.path.join(HERE, "cite_allow.txt")

EXT = (
    "py|md|json|jsonl|txt|sh|ps1|bat|yml|yaml|toml|ini|cfg|conf|"
    "js|ts|tsx|jsx|html|css|rs|go|java|c|h|cpp|hpp|sql|kt|swift|rb|php"
)
# A citation is a path WITH a line number. That is the form that asserts
# "this file says this at this line", which is the claim that was false.
CITE = re.compile(
    r"(?<![\w:/\\.-])"
    r"((?:[\w.+-]+[/\\])*[\w.+-]+\.(?:" + EXT + r"))"
    r":(\d{1,9})(?![\d\w])",
    re.IGNORECASE,
)


def load_allow():
    out = set()
    try:
        with open(ALLOW_FILE, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if line and not line.startswith("#"):
                    out.add(line.replace("\\", "/").lower())
    except OSError:
        pass
    return out


def last_assistant_text(transcript_path):
    """Return the text of the final assistant message in the JSONL transcript."""
    text = []
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return ""
    for raw in reversed(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        msg = rec.get("message") or {}
        if rec.get("type") != "assistant" and msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            text.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text.append(block.get("text") or "")
        if text:
            break
    return "\n".join(text)


def norm(s):
    """Collapse whitespace so a quote that survived re-wrapping still matches.
    Line breaks in a reply are formatting, not evidence of a different string."""
    return re.sub(r"\s+", " ", s or "").strip()


def tool_output(transcript_path):
    """Every tool RESULT in this session, as one blob.

    Used to ask whether a number in the reply was ever measured. A number that
    appears nowhere in any tool output was computed in prose -- which is how
    '64 unaccounted' got presented as a finding on 2026-09-17 when it was
    90 minus 26 done in my head, across two different units."""
    blob = []
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return ""
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        msg = rec.get("message") or {}
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result":
                    c = block.get("content")
                    if isinstance(c, str):
                        blob.append(c)
                    elif isinstance(c, list):
                        for sub in c:
                            if isinstance(sub, dict) and sub.get("type") == "text":
                                blob.append(sub.get("text") or "")
                elif block.get("type") == "tool_use":
                    blob.append(json.dumps(block.get("input") or {}))
    return "\n".join(blob)


def count_lines(path):
    n = 0
    with open(path, "rb") as fh:
        for _ in fh:
            n += 1
    return n


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # Never fight a stop we already caused.
    if payload.get("stop_hook_active"):
        sys.exit(0)

    transcript = payload.get("transcript_path") or ""
    cwd = payload.get("cwd") or os.getcwd()
    if not transcript or not os.path.exists(transcript):
        sys.exit(0)

    text = last_assistant_text(transcript)
    if not text:
        sys.exit(0)

    allow = load_allow()
    seen = set()
    problems = []
    warnings = []

    # --- END PASS, part 2: does a quotation actually say what I say it says? --
    # The operator's design, 2026-09-17: "1st for counting end for formatting."
    # The first pass establishes denominators before reasoning; this one checks
    # that the REPORT faithfully represents what was measured. On 2026-09-16 I
    # attributed a quotation to a file, and the quotation was assembled from a
    # truncated grep match rather than read. The path check below catches a file
    # that does not exist; it cannot catch words a real file never contained.
    #
    # Scope is the PARAGRAPH holding the citation, and only quotes of 20+ chars,
    # because a short quote collides with ordinary prose and a guard that cries
    # wolf gets switched off (docs/RETRACTED.json makes the same argument about
    # its own patterns).
    for para in re.split(r"\n\s*\n", text):
        cited = [m.group(1) for m in CITE.finditer(para)]
        if not cited:
            continue
        quotes = re.findall(r"[\"“]([^\"“”]{20,400})[\"”]", para)
        if not quotes:
            continue
        bodies = {}
        for rel in cited:
            if rel.replace("\\", "/").lower() in allow:
                continue
            p = rel if os.path.isabs(rel) else os.path.join(cwd, rel)
            try:
                with open(os.path.normpath(p), "r", encoding="utf-8",
                          errors="replace") as fh:
                    bodies[rel] = norm(fh.read())
            except OSError:
                pass
        if not bodies:
            continue
        for q in quotes:
            nq = norm(q)
            if not nq or any(nq in b for b in bodies.values()):
                continue
            problems.append(
                "  a quotation attributed to %s does not appear in it:\n"
                "      %s\n"
                "      -- if this is a paraphrase, do not put it in quotation "
                "marks; if it is a quote, read the file and copy it."
                % (" or ".join(sorted(bodies)), q[:160]))

    for match in CITE.finditer(text):
        raw_path, raw_line = match.group(1), match.group(2)
        key = (raw_path, raw_line)
        if key in seen:
            continue
        seen.add(key)
        if raw_path.replace("\\", "/").lower() in allow:
            continue

        line_no = int(raw_line)
        candidate = raw_path if os.path.isabs(raw_path) else os.path.join(cwd, raw_path)
        candidate = os.path.normpath(candidate)

        if not os.path.isfile(candidate):
            problems.append(
                "  %s:%s -- NO SUCH FILE. You cited a path that does not exist. "
                "If this came from a grep hit, the filename was not part of the "
                "match; open the file before citing it." % (raw_path, raw_line)
            )
            continue

        try:
            total = count_lines(candidate)
        except OSError:
            continue
        if line_no > total:
            problems.append(
                "  %s:%s -- OUT OF RANGE. That file has %d lines, so line %d "
                "cannot say anything." % (raw_path, raw_line, total, line_no)
            )

    # --- END PASS, part 3: numbers that were never measured -----------------
    # WARNING ONLY, never a block. A reply legitimately contains computed
    # numbers -- percentages, differences, sums -- and blocking those would be
    # constant noise. But a number that appears in NO tool result is a number I
    # derived, and derived numbers are where the units errors live: 64 was
    # 90 minus 26 with the two operands counting different things. So it is
    # surfaced beside a block that has already been earned, as a prompt to show
    # the derivation rather than present it as a measurement.
    results = tool_output(transcript)
    if results:
        candidates = set()
        for m in re.finditer(r"(?<![\w.:/-])(\d{2,9})(?![\w.:/%-])", text):
            n = m.group(1)
            if len(n) >= 2 and not (1900 <= int(n) <= 2100):   # skip years
                candidates.add(n)
        unsourced = sorted((n for n in candidates if n not in results),
                           key=lambda x: -len(x))[:8]
        if unsourced:
            warnings.append(
                "  numbers in this reply that appear in no tool result: %s\n"
                "      -- if any is a finding rather than arithmetic, measure it; "
                "if it is arithmetic, show the operands and their UNITS."
                % ", ".join(unsourced))

    if not problems:
        sys.exit(0)

    reason = (
        "Citation check failed. Your reply asserts what a file says at a line "
        "that cannot say it:\n\n"
        + "\n".join(problems)
        + ("\n\nAlso noticed, not blocking:\n" + "\n".join(warnings)
           if warnings else "")
        + "\n\nOpen each file at the cited line and quote what is actually "
        "there, or drop the citation. Do not reconstruct it from a grep hit "
        "or from memory -- that is the error this hook exists to stop "
        "(see memory: derived-source-errors). If a path is an EXAMPLE rather "
        "than a citation, add it to .claude/hooks/cite_allow.txt."
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # fail open, never wedge the session
        sys.stderr.write("verify_citations hook error (failing open): %r\n" % (exc,))
        sys.exit(0)
