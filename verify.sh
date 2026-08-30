#!/bin/sh
# verify.sh -- check the constitution WITHOUT PYTHON.
#
# WHY THIS EXISTS
#
#   Everything that verifies this project is written in Python, and the record
#   is supposed to outlive the machine it was written on. Those two facts do
#   not sit together. A record whose only verifier needs a particular runtime
#   is a record that expires when the runtime does -- when Python 3 goes the
#   way of Python 2, when the interpreter on the box is the thing that was
#   tampered with, or when whoever inherits this has a shell and no more.
#
#   So: the same answer, computed by different means. This script reproduces
#   constitution.py's hash using nothing but sh, awk and a SHA-256 tool that
#   every Unix already has. If the two ever disagree, that disagreement is
#   itself the finding -- one of them is wrong, and neither gets to be the
#   authority on whether it is the wrong one.
#
#   That is the point. Two independent implementations of one check is worth
#   more than one implementation checked twice.
#
# THE SCHEME, stated so it can be redone by hand on paper if it must be:
#   1. Take each protected block: from its heading, up to the next heading of
#      the same or higher level.
#   2. Normalise: CRLF -> LF, strip trailing whitespace from every line, drop
#      leading and trailing blank lines. Join with LF, NO trailing newline.
#   3. SHA-256 each normalised block -> its digest, in lowercase hex.
#   4. Sort the digests as strings. Order-independent on purpose: moving a
#      section is not a change to what it says.
#   5. SHA-256 of the literal bytes "covenant-constitution-v1" followed by the
#      sorted digests concatenated, with nothing between them. That is the
#      constitution hash.
#
# USE
#   sh verify.sh            compare against docs/CONSTITUTION_ANCHOR.json
#   sh verify.sh --show     print each block digest
#
# Exit 0 the anchor matches, 1 it does not, 2 the check could not be run --
# and 2 is never quietly treated as 0.
#
# LICENCE: public domain.

set -u
HERE=$(dirname "$0")
ANCHOR="$HERE/docs/CONSTITUTION_ANCHOR.json"
SHOW=0
[ "${1:-}" = "--show" ] && SHOW=1

# --- a SHA-256 that exists on this machine, whatever it is called -----------
sha256_stdin() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum | cut -d' ' -f1
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | cut -d' ' -f1
  elif command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 | sed 's/.*= *//'
  elif command -v digest >/dev/null 2>&1; then
    digest -a sha256
  else
    echo "NO_SHA256_TOOL"
  fi
}

if [ "$(printf '' | sha256_stdin)" = "NO_SHA256_TOOL" ]; then
  echo "  Could not find sha256sum, shasum, openssl or digest."
  echo "  This check could NOT run. That is not a pass."
  exit 2
fi

# --- block extraction + normalisation, in awk -------------------------------
# Prints the normalised block with NO trailing newline, so the bytes hashed
# here are the same bytes constitution.py hashes.
extract() {
  awk -v want="$2" '
    function depth(s,  n) { n = 0; while (substr(s, n+1, 1) == "#") n++; return n }
    BEGIN { d = 0; inb = 0; n = 0 }
    {
      line = $0
      sub(/\r$/, "", line)                      # CRLF -> LF
      sub(/[ \t]+$/, "", line)                  # rstrip
      # The heading may use -, an em dash or an en dash; all three mean the
      # same heading to a human, so all three must mean it here.
      probe = line
      gsub(/ — | – /, " - ", probe)
      target = want
      gsub(/ — | – /, " - ", target)
      # NOTE, found by this script disagreeing with constitution.py on exactly
      # one of three blocks: what gets hashed is the CANONICAL heading from
      # the protected list, not the heading as the file happens to spell it.
      # SUCCESSION.md writes "Layer 4 — Continuation" with an em dash while
      # the protected list says "Layer 4 - Continuation" with a hyphen, and
      # constitution.py hashes the hyphen. That is the better behaviour --
      # changing a dash is typography, not an amendment -- so this matches it
      # deliberately rather than "fixing" it. Emit `want`, not `line`.
      if (!inb && probe == target) { inb = 1; d = depth(line); buf[n++] = want; next }
      if (inb) {
        if (line ~ /^#+[ \t]/ && depth(line) <= d) { inb = 2; next }
        if (inb == 1) buf[n++] = line
      }
    }
    END {
      s = 0; e = n - 1
      while (s <= e && buf[s] == "") s++
      while (e >= s && buf[e] == "") e--
      out = ""
      for (i = s; i <= e; i++) out = out (i > s ? "\n" : "") buf[i]
      printf "%s", out
    }
  ' "$1"
}

# --- the protected blocks. Must match constitution.py PROTECTED -------------
# Kept as parallel arrays in POSIX sh (no arrays) via a here-doc of records
# separated by a tab, because this file may not assume bash.
BLOCKS=$(cat <<'EOF'
CONTRIBUTING.md	## Why it exists, and the one condition
CONTRIBUTING.md	## What never changes
docs/SUCCESSION.md	## Layer 4 - Continuation, not just preservation
EOF
)

digests=""
missing=0
echo ""
echo "  CONSTITUTION -- verified WITHOUT PYTHON (sh + awk + sha256)"
echo "  --------------------------------------------------------------"
OLDIFS=$IFS
IFS='
'
for rec in $BLOCKS; do
  f=$(printf '%s' "$rec" | cut -f1)
  o=$(printf '%s' "$rec" | cut -f2)
  path="$HERE/$f"
  if [ ! -f "$path" ]; then
    echo "    MISSING FILE  $f"
    missing=$((missing + 1))
    continue
  fi
  body=$(extract "$path" "$o")
  if [ -z "$body" ]; then
    echo "    MISSING BLOCK $f :: $o"
    missing=$((missing + 1))
    continue
  fi
  d=$(printf '%s' "$body" | sha256_stdin)
  [ "$SHOW" = "1" ] && echo "    $(printf '%.16s' "$d")  $o"
  digests="$digests$d
"
done
IFS=$OLDIFS

if [ "$missing" -gt 0 ]; then
  echo ""
  echo "  $missing protected block(s) could not be read."
  echo "  A block that has been DELETED is the most serious result there is:"
  echo "  it is an amendment that leaves no trace in what remains."
  exit 1
fi

# Sorted, then concatenated with nothing between them, after the domain tag.
root=$( { printf '%s' "covenant-constitution-v1"
          printf '%s' "$(printf '%s' "$digests" | sed '/^$/d' | sort | tr -d '\n')"
        } | sha256_stdin )

echo ""
echo "    computed  $root"

if [ ! -f "$ANCHOR" ]; then
  echo "    anchor    NOT FOUND at docs/CONSTITUTION_ANCHOR.json"
  echo ""
  echo "  Could not compare. This is not a pass."
  exit 2
fi

# Read the anchor's hash without a JSON parser: it is the first "hash" field.
anchored=$(sed -n 's/.*"hash"[[:space:]]*:[[:space:]]*"\([0-9a-f]\{64\}\)".*/\1/p' \
           "$ANCHOR" | head -n 1)
echo "    anchored  ${anchored:-<none found>}"
echo ""

if [ -z "$anchored" ]; then
  echo "  No hash found in the anchor file. Could not compare; not a pass."
  exit 2
fi
if [ "$root" = "$anchored" ]; then
  echo "  MATCH. The rules that bind the operator are the ones published."
  echo ""
  echo "  What this does and does not prove: it proves the text here is the"
  echo "  text the anchor names. It cannot prove the anchor was not changed"
  echo "  together with the text -- for that, compare against a clone nobody"
  echo "  on this machine can reach. That limit is in CONSTITUTION.md III and"
  echo "  it is not fixable by any amount of local checking."
  exit 0
fi
echo "  DIFFERENT. The protected text does not hash to the published anchor."
echo ""
echo "  This is not automatically wrong -- amendment is allowed. What is not"
echo "  allowed is amendment in SILENCE, and this is the noise. Either the"
echo "  rules changed and the anchor was not republished, or something"
echo "  changed that nobody intended. Find out which before doing anything"
echo "  else, and if it was intended, republish the anchor and say why."
exit 1
