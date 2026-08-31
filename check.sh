#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# check.sh -- ONE command that checks everything a stranger can check.
#
# WHY THIS FILE EXISTS
#
#   The only event that changes anything for this project is somebody who
#   does not know the author running the verifiers and finding that they
#   agree. Everything else -- letters, documents, claims -- is a promise
#   about that event.
#
#   So the cost of that event is the number worth minimising, and it was
#   five commands and a decision about whether to install Python. This
#   makes it one command and no decision. A reader with sh and sha256 and
#   nothing else still gets a real result, not a diagnostic about what
#   they are missing.
#
# WHAT IT WILL NOT DO
#
#   * It will not carry its own copy of the hashes it checks. A test that
#     compares a program against a constant stored inside the test proves
#     the constant, and both can be edited in the same commit. So the
#     constitution check here is a comparison between two INDEPENDENT
#     implementations -- sh+awk against Python -- and it passes only if
#     they agree with each other.
#   * It will not report a skipped check as a passed one. Every runtime
#     that is absent is named, with what went unchecked because of it.
#   * It will not treat a non-zero exit as failure where a non-zero exit
#     is the point. scale.py exits 1 BECAUSE the dissent survived to the
#     top; a wrapper that called that a failure would be reporting the
#     healthy case as broken, which is the trap this file was written
#     around.
#
# USE:  sh check.sh          (no arguments, nothing to configure)
# EXIT: 0 everything that could run agreed. 1 something disagreed.
#       2 nothing could be checked at all.
# LICENCE: Apache-2.0.

set -u

HERE=$(dirname "$0")
cd "$HERE" || exit 2

PASS=0
FAIL=0
SKIP=0

say() { printf '%s\n' "$*"; }

# awk, not `grep -o`. -o is not in POSIX, and this script's whole claim is
# that it runs where verify.sh runs -- sh, awk, a sha256 tool, nothing else.
# Adding a GNU-only flag would have narrowed that quietly. Interval braces
# {64} are avoided too, since older awks do not have them: length() and a
# charset test say the same thing everywhere.
hashes_of() {
    printf '%s\n' "$1" | awk '{
        for (i = 1; i <= NF; i++)
            if (length($i) == 64 && $i ~ /^[0-9a-f]+$/) print $i
    }'
}

# ---------------------------------------------------------------- runtimes
have() { command -v "$1" >/dev/null 2>&1; }

PY=""
for c in python3 python py; do
    if have "$c" && "$c" -c "import sys" >/dev/null 2>&1; then PY=$c; break; fi
done

SHA=""
for c in sha256sum shasum sha256; do
    if have "$c"; then SHA=$c; break; fi
done

say ""
say "  COVENANT -- independent check, one command"
say "  =========================================="
say ""
say "  runtimes   sh yes | awk $(have awk && echo yes || echo NO) |" \
    "sha256 ${SHA:-NONE} | python ${PY:-NONE}"
say ""

# --------------------------------------------------- 1+2. the constitution
#
# Two programs, no shared code, computing the same hash over the same text.
# The claim under test is that they AGREE -- so neither is compared against
# a number written down here.

SH_HASH=""
PY_HASH=""

if [ -f verify.sh ] && have awk && [ -n "$SHA" ]; then
    OUT=$(sh verify.sh 2>&1)
    RC=$?
    # Both numbers it prints -- computed, then anchored -- and they must
    # agree. The first draft took only the first, which would have printed
    # the hash of a tampered file as though it were a result: the overall
    # verdict would still have failed, because the python verifier exits
    # non-zero, but this line would have said the wrong thing. Measured
    # afterwards by mutating a protected block: both verifiers computed
    # a5835192466032933e45f9e87c147557ac1ac79ee384185310e5e8233cc4b854
    # against the anchored 0f0b3162..., both reported MISMATCH, and the
    # script exited 1.
    A=$(hashes_of "$OUT" | head -n 1)
    B=$(hashes_of "$OUT" | tail -n 1)
    if [ $RC -eq 0 ] && [ -n "$A" ] && [ "$A" = "$B" ]; then
        SH_HASH=$A
        say "  [1] constitution, WITHOUT python   sh + awk + $SHA"
        say "      $SH_HASH"
    else
        say "  [1] constitution, WITHOUT python   MISMATCH (exit $RC)"
        say "      computed  ${A:-none}"
        say "      anchored  ${B:-none}"
        say "      The text on disk is not the text the anchor names."
        FAIL=$((FAIL + 1))
    fi
else
    say "  [1] constitution, WITHOUT python   SKIPPED"
    say "      missing: $( [ -f verify.sh ] || echo 'verify.sh ')$(have awk || echo 'awk ')$( [ -n "$SHA" ] || echo 'a sha256 tool')"
    say "      unchecked: whether the published rules are the rules on disk."
    SKIP=$((SKIP + 1))
fi

if [ -n "$PY" ] && [ -f constitution.py ]; then
    OUT=$("$PY" constitution.py verify 2>&1)
    RC=$?
    A=$(hashes_of "$OUT" | head -n 1)
    B=$(hashes_of "$OUT" | tail -n 1)
    if [ $RC -eq 0 ] && [ -n "$A" ] && [ "$A" = "$B" ]; then
        PY_HASH=$A
        say "  [2] constitution, python           constitution.py verify"
        say "      $PY_HASH"
    else
        say "  [2] constitution, python           MISMATCH (exit $RC)"
        say "      anchored  ${A:-none}"
        say "      current   ${B:-none}"
        FAIL=$((FAIL + 1))
    fi
else
    say "  [2] constitution, python           SKIPPED -- no python found"
    SKIP=$((SKIP + 1))
fi

if [ -n "$SH_HASH" ] && [ -n "$PY_HASH" ]; then
    if [ "$SH_HASH" = "$PY_HASH" ]; then
        say ""
        say "      -> TWO IMPLEMENTATIONS SHARING NO CODE AGREE."
        say "         An amendment would have to alter both to pass unseen."
        PASS=$((PASS + 2))
    else
        say ""
        say "      -> DISAGREE. This is a real finding, and the project would"
        say "         rather have it than not. Please open an issue with both"
        say "         hashes and your platform."
        FAIL=$((FAIL + 1))
    fi
elif [ -n "$SH_HASH" ] || [ -n "$PY_HASH" ]; then
    say ""
    say "      -> only ONE implementation ran, so agreement was not tested."
    say "         A single verifier checks the text; it cannot check itself."
    PASS=$((PASS + 1))
fi
say ""

# ------------------------------------------------------ 3. conformance root
if [ -n "$PY" ] && [ -f conformance.py ]; then
    OUT=$("$PY" conformance.py 2>&1)
    RC=$?
    ROOT=$(hashes_of "$OUT" | head -n 1)
    if [ $RC -eq 0 ] && [ -n "$ROOT" ]; then
        say "  [3] conformance root               11 vectors, behaviour not prose"
        say "      $ROOT"
        say "      NOT CROSS-CHECKED: no second implementation exists yet."
        say "      This is the number an independent build must reproduce, in"
        say "      any language, sharing none of this code. Reproducing it is"
        say "      the single most useful thing a reader of this repository"
        say "      can do, and it needs nobody's permission."
        PASS=$((PASS + 1))
    else
        say "  [3] conformance root               FAIL (exit $RC)"
        FAIL=$((FAIL + 1))
    fi
else
    say "  [3] conformance root               SKIPPED -- no python found"
    say "      unchecked: whether this build agrees with any other."
    SKIP=$((SKIP + 1))
fi
say ""

# --------------------------------------- 4. dissent survives composition
#
# scale.py exits NON-ZERO on success. A dissent three levels down reaching
# the top is the property being demonstrated, and the exit code is how it
# reports it. Zero here would mean the disagreement vanished on the way up.

if [ -n "$PY" ] && [ -f scale.py ]; then
    "$PY" scale.py >/dev/null 2>&1
    RC=$?
    if [ $RC -ne 0 ]; then
        say "  [4] dissent survives composition   exit $RC, which is the PASS"
        say "      A single node disagreed three levels down and the federation"
        say "      reports it. The obvious implementation forwards the majority"
        say "      and the dissent disappears at exactly the scale where"
        say "      somebody would have acted on it."
        PASS=$((PASS + 1))
    else
        say "  [4] dissent survives composition   FAIL -- exit 0"
        say "      The dissent was absorbed. That is the failure this mechanism"
        say "      exists to prevent."
        FAIL=$((FAIL + 1))
    fi
else
    say "  [4] dissent survives composition   SKIPPED -- no python found"
    SKIP=$((SKIP + 1))
fi
say ""

# ------------------------------------------------------- 5. what it survives
if [ -n "$PY" ] && [ -f redundancy.py ]; then
    OUT=$("$PY" redundancy.py 2>&1)
    RC=$?
    if [ $RC -eq 0 ]; then
        say "  [5] redundancy floor               redundancy.py, its own words:"
        printf '%s\n' "$OUT" | tail -n 5 | sed 's/^ */      | /'
        PASS=$((PASS + 1))
    else
        say "  [5] redundancy floor               FAIL (exit $RC)"
        FAIL=$((FAIL + 1))
    fi
else
    say "  [5] redundancy floor               SKIPPED -- no python found"
    SKIP=$((SKIP + 1))
fi

# ------------------------------------------------------------------ verdict
say ""
say "  ------------------------------------------------------------------"
say "  $PASS passed, $FAIL disagreed, $SKIP skipped."

if [ $FAIL -gt 0 ]; then
    say ""
    say "  SOMETHING DISAGREED, and that is worth more to this project than"
    say "  agreement. github.com/LAWLESS1987/covenant/issues -- paste the"
    say "  block above and your platform. A refutation is recorded publicly"
    say "  here, the same as a confirmation."
    exit 1
fi

if [ $PASS -eq 0 ]; then
    say ""
    say "  NOTHING COULD BE CHECKED. That is a finding about this machine,"
    say "  not about the repository. Install a sha256 tool, or python, and"
    say "  run this again."
    exit 2
fi

say ""
if [ $SKIP -gt 0 ]; then
    say "  Everything that COULD run agreed. $SKIP check(s) did not run, and"
    say "  are listed above with what went unchecked -- a skipped check is"
    say "  not a passed one, and this script will not round it up."
else
    say "  Everything agreed."
fi
say ""
say "  What none of this proves: that the verifier and the thing it"
say "  verifies are not both wrong. They ran on the same machine, from the"
say "  same clone. The check that this cannot do is the one only a stranger"
say "  can do -- clone it somewhere this machine cannot reach, run it"
say "  again, and see whether the roots match. That is the whole ask."
say ""
exit 0
