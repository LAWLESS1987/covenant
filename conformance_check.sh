#!/bin/sh
# conformance_check.sh
#
# An INDEPENDENT reimplementation of the covenant conformance vectors,
# written from docs/CONFORMANCE_SPEC.json alone, in POSIX sh + awk.
# It shares no code and no runtime with the original implementation:
# no Python, no jq, no external JSON parser. The JSON is hand-parsed
# by a recursive-descent parser written in awk, below.
#
# Usage:  sh conformance_check.sh [path/to/CONFORMANCE_SPEC.json]
# Exit:   0 = all vectors matched and the root reproduced
#         1 = a vector mismatched or the root differs
#         2 = environment problem (missing spec, missing sha256 tool)
#         3 = the spec could not be parsed
#
# ASSUMPTIONS THE SPEC DOES NOT STATE (see the report accompanying this file).
# Each is marked ASSUMPTION at its use site. They are guesses, not knowledge.

set -u

SELF_DIR=`dirname "$0"`
if [ $# -ge 1 ]; then
  SPEC="$1"
else
  SPEC="$SELF_DIR/docs/CONFORMANCE_SPEC.json"
fi

if [ ! -f "$SPEC" ]; then
  echo "conformance_check: spec not found: $SPEC" >&2
  exit 2
fi

# ---- pick a sha256 front end -------------------------------------------------
SHA=""
if command -v sha256sum >/dev/null 2>&1; then
  SHA="sha256sum"
elif command -v shasum >/dev/null 2>&1; then
  SHA="shasum -a 256"
elif command -v openssl >/dev/null 2>&1; then
  SHA="openssl_dgst"
fi
if [ -z "$SHA" ]; then
  echo "conformance_check: no sha256sum / shasum / openssl available" >&2
  exit 2
fi

hash_file() {
  if [ "$SHA" = "openssl_dgst" ]; then
    openssl dgst -sha256 "$1" | awk '{print $NF}'
  else
    $SHA "$1" | awk '{print $1}'
  fi
}

TMPD="${TMPDIR:-/tmp}/covconf.$$"
mkdir -p "$TMPD" || exit 2
trap 'rm -rf "$TMPD"' EXIT
trap 'rm -rf "$TMPD"; exit 130' INT
trap 'rm -rf "$TMPD"; exit 143' TERM

# ---- the engine --------------------------------------------------------------
cat > "$TMPD/engine.awk" <<'AWK_ENGINE_EOF'
# ============================================================================
# A JSON reader, a canonical JSON writer, and the two operations ("attest"
# and "climb") reconstructed from the vectors' input -> expected pairs.
# ============================================================================

function fatal(m) {
  printf("FATAL: %s\n", m)
  FATAL = 1
  exit 3
}

# ---------------------------------------------------------------- tokenizer --
function tokenize(   n, i, c, e, s) {
  n = length(TXT); i = 1; tn = 0
  while (i <= n) {
    c = substr(TXT, i, 1)
    if (c == " " || c == "\t" || c == "\n" || c == "\r") { i++; continue }
    if (c == "{" || c == "}" || c == "[" || c == "]" || c == ":" || c == ",") {
      tn++; ttype[tn] = "p"; tval[tn] = c; i++; continue
    }
    if (c == "\"") {
      i++; s = ""
      while (i <= n) {
        c = substr(TXT, i, 1)
        if (c == "\\") {
          e = substr(TXT, i + 1, 1)
          if      (e == "\"") s = s "\""
          else if (e == "\\") s = s "\\"
          else if (e == "/")  s = s "/"
          else if (e == "n")  s = s "\n"
          else if (e == "t")  s = s "\t"
          else if (e == "r")  s = s "\r"
          else if (e == "b")  s = s sprintf("%c", 8)
          else if (e == "f")  s = s sprintf("%c", 12)
          else if (e == "u")  fatal("\\uXXXX escapes are not supported by this reader")
          else                fatal("unknown escape \\" e)
          i += 2; continue
        }
        if (c == "\"") { i++; break }
        s = s c; i++
      }
      tn++; ttype[tn] = "s"; tval[tn] = s; continue
    }
    if (c == "-" || (c >= "0" && c <= "9")) {
      s = ""
      while (i <= n) {
        c = substr(TXT, i, 1)
        if (c == "-" || c == "+" || c == "." || c == "e" || c == "E" || (c >= "0" && c <= "9")) {
          s = s c; i++
        } else break
      }
      tn++; ttype[tn] = "n"; tval[tn] = s; continue
    }
    if (c >= "a" && c <= "z") {
      s = ""
      while (i <= n) {
        c = substr(TXT, i, 1)
        if (c >= "a" && c <= "z") { s = s c; i++ } else break
      }
      if (s != "true" && s != "false" && s != "null") fatal("bad literal '" s "'")
      tn++; ttype[tn] = "l"; tval[tn] = s; continue
    }
    fatal("unexpected character '" c "' at offset " i)
  }
}

# ------------------------------------------------------------------- parser --
# Node store:
#   ntype[id] = obj | arr | str | num | bool | null
#   nval[id]  = scalar text
#   objects: ocnt[id], okeys[id,k]=key, oval[id,key]=child, ohas[id,key]=1
#   arrays:  acnt[id], aval[id,k]=child
function mk(t, v,   id) { nid++; ntype[nid] = t; nval[nid] = v; return nid }

function pv(   t, v) {
  t = ttype[tp]
  if (t == "p") {
    v = tval[tp]
    if (v == "{") return pobj()
    if (v == "[") return parr()
    fatal("unexpected '" v "'")
  }
  if (t == "s") { tp++; return mk("str", tval[tp - 1]) }
  if (t == "n") { tp++; return mk("num", tval[tp - 1]) }
  if (t == "l") {
    tp++
    if (tval[tp - 1] == "null") return mk("null", "null")
    return mk("bool", tval[tp - 1])
  }
  fatal("unexpected end of input")
}

function pobj(   id, k, ch, c) {
  id = mk("obj", "")
  tp++                                   # consume '{'
  c = 0
  if (ttype[tp] == "p" && tval[tp] == "}") { tp++; ocnt[id] = 0; return id }
  while (1) {
    if (ttype[tp] != "s") fatal("object key expected")
    k = tval[tp]; tp++
    if (!(ttype[tp] == "p" && tval[tp] == ":")) fatal("':' expected")
    tp++
    ch = pv()
    c++
    okeys[id SUBSEP c] = k
    oval[id SUBSEP k]  = ch
    ohas[id SUBSEP k]  = 1
    if (ttype[tp] == "p" && tval[tp] == ",") { tp++; continue }
    if (ttype[tp] == "p" && tval[tp] == "}") { tp++; break }
    fatal("',' or '}' expected in object")
  }
  ocnt[id] = c
  return id
}

function parr(   id, ch, c) {
  id = mk("arr", "")
  tp++                                   # consume '['
  c = 0
  if (ttype[tp] == "p" && tval[tp] == "]") { tp++; acnt[id] = 0; return id }
  while (1) {
    ch = pv()
    c++
    aval[id SUBSEP c] = ch
    if (ttype[tp] == "p" && tval[tp] == ",") { tp++; continue }
    if (ttype[tp] == "p" && tval[tp] == "]") { tp++; break }
    fatal("',' or ']' expected in array")
  }
  acnt[id] = c
  return id
}

# ------------------------------------------------------- canonical JSON out --
# "canonical JSON of expected (sorted keys, no spaces)" -- spec note.
function jstr(s,   i, n, c, o, b) {
  n = length(s); o = "\""
  for (i = 1; i <= n; i++) {
    c = substr(s, i, 1)
    if (c == "\"")      o = o "\\\""
    else if (c == "\\") o = o "\\\\"
    else if (c == "\n") o = o "\\n"
    else if (c == "\t") o = o "\\t"
    else if (c == "\r") o = o "\\r"
    else {
      b = ORD[c]
      if (b != "" && b < 32) o = o sprintf("\\u%04x", b)
      else o = o c
    }
  }
  return o "\""
}

function canon(id,   t, i, j, n, ks, tmp, out) {
  t = ntype[id]
  if (t == "obj") {
    n = ocnt[id]
    for (i = 1; i <= n; i++) ks[i] = okeys[id SUBSEP i]
    isort(ks, n)
    out = "{"
    for (i = 1; i <= n; i++) {
      if (i > 1) out = out ","
      out = out jstr(ks[i]) ":" canon(oval[id SUBSEP ks[i]])
    }
    return out "}"
  }
  if (t == "arr") {
    n = acnt[id]
    out = "["
    for (i = 1; i <= n; i++) {
      if (i > 1) out = out ","
      out = out canon(aval[id SUBSEP i])
    }
    return out "]"
  }
  if (t == "str")  return jstr(nval[id])
  if (t == "num")  return nval[id]
  if (t == "bool") return nval[id]
  return "null"
}

function isort(a, n,   i, j, t) {
  for (i = 2; i <= n; i++) {
    t = a[i]; j = i - 1
    while (j >= 1 && (a[j] "") > (t "")) { a[j + 1] = a[j]; j-- }
    a[j + 1] = t
  }
}

function jarr(a, n,   i, o) {
  o = "["
  for (i = 1; i <= n; i++) { if (i > 1) o = o ","; o = o jstr(a[i]) }
  return o "]"
}

# ------------------------------------------------------------ octal escapes --
# The root's byte stream contains NUL bytes, which no shell variable can hold.
# So awk emits the whole stream as a printf(1) format made of \NNN escapes and
# the shell materialises it. Every byte is escaped, so no % can appear.
function oct(s,   i, n, c, b, o) {
  n = length(s); o = ""
  for (i = 1; i <= n; i++) {
    c = substr(s, i, 1)
    b = ORD[c]
    if (b == "") fatal("byte outside the ASCII table in '" s "'")
    o = o sprintf("\\%03o", b)
  }
  return o
}

# -------------------------------------------------------- symbolic roots map --
function resolve(sym) { return (sym in SYM) ? SYM[sym] : sym }

# --------------------------------------------------------------- the verdict --
# Shared core of both operations. Given the roots actually spoken by the
# answering parties (av[1..ansn]) and a quorum, decide the verdict, the
# reference root, and how many answerers are outliers.
#
# ASSUMPTION (spec silent): the reference root is the most-held root among the
#   answers, ties broken by the lexicographically smallest root VALUE. The
#   vectors cannot distinguish this from "the root of the first answerer in
#   sorted order" -- both yield ["y","z"] for the three-way vector.
# ASSUMPTION (spec silent): quorum shortfall outranks disagreement, so a level
#   that is both short of quorum and internally split reports UNPROVEN.
function decide(av, ansn, q,   dn, dv, dc, i, j, found, bc, outn) {
  dn = 0
  for (i = 1; i <= ansn; i++) {
    found = 0
    for (j = 1; j <= dn; j++) if (dv[j] == av[i]) { dc[j]++; found = 1; break }
    if (!found) { dn++; dv[dn] = av[i]; dc[dn] = 1 }
  }
  bc = -1; D_BEST = ""
  for (j = 1; j <= dn; j++) {
    if (dc[j] > bc || (dc[j] == bc && (dv[j] "") < (D_BEST ""))) { bc = dc[j]; D_BEST = dv[j] }
  }
  outn = 0
  for (i = 1; i <= ansn; i++) if (av[i] != D_BEST) outn++
  D_OUTN = outn
  if (ansn < q)      D_VERDICT = "UNPROVEN"
  else if (outn > 0) D_VERDICT = "DIVERGED"
  else               D_VERDICT = "AGREE"
}

# ------------------------------------------------------------- op "attest" ---
function attest_run(inp,   rm, n, i, nm, ch, ansn, ans, av, siln, sil, q,
                          outn, outl, agreed) {
  rm = oval[inp SUBSEP "roots"]
  n = ocnt[rm]
  for (i = 1; i <= n; i++) nm[i] = okeys[rm SUBSEP i]
  # ASSUMPTION (spec silent): answered/outliers/silent are ordered by witness
  # name, ascending. The vectors' witnesses are already x<y<z in file order,
  # so file order and sorted order are indistinguishable here.
  isort(nm, n)

  ansn = 0; siln = 0
  for (i = 1; i <= n; i++) {
    ch = oval[rm SUBSEP nm[i]]
    if (ntype[ch] == "null") { siln++; sil[siln] = nm[i] }
    else                     { ansn++; ans[ansn] = nm[i]; av[ansn] = resolve(nval[ch]) }
  }

  # ASSUMPTION (spec silent): the default quorum is 2 when "quorum" is absent.
  # Every attest vector has exactly 3 witnesses, so a literal 2 and a
  # "majority of witnesses" rule agree on all of them.
  q = (ohas[inp SUBSEP "quorum"]) ? (nval[oval[inp SUBSEP "quorum"]] + 0) : DEFQUORUM

  decide(av, ansn, q)

  outn = 0
  for (i = 1; i <= ansn; i++) if (av[i] != D_BEST) { outn++; outl[outn] = ans[i] }

  agreed = (D_VERDICT == "AGREE") ? "true" : "false"
  return "{\"agreed\":" agreed \
         ",\"answered\":" jarr(ans, ansn) \
         ",\"outliers\":" jarr(outl, outn) \
         ",\"silent\":" jarr(sil, siln) \
         ",\"verdict\":\"" D_VERDICT "\"}"
}

# -------------------------------------------------------------- op "climb" ---
# A node is a LEVEL if it carries "children", otherwise a CARRIER holding a
# "root". ASSUMPTION (spec silent): that is the discriminator; the spec never
# names the node shapes or says what a node carrying both would mean.
#
# A level attests over its children. A child contributes its root only if it
# AGREES; any other verdict is silence (vector S.silence.upward).
# ASSUMPTION (spec silent): "divergences" counts LEVELS whose verdict is
#   DIVERGED, not outlier carriers. No vector separates the two -- every
#   diverged level in the vectors has exactly one outlier.
# ASSUMPTION (spec silent): an UNPROVEN level adds nothing to the count.
# ASSUMPTION (spec silent): levels use the default quorum; no climb vector
#   carries a "quorum" field, so whether climb honours one is unknown.
function ev(node,   ci, cn, i, kv, kn) {
  if (ohas[node SUBSEP "children"]) {
    ci = oval[node SUBSEP "children"]
    cn = acnt[ci]
    kn = 0
    for (i = 1; i <= cn; i++) {
      ev(aval[ci SUBSEP i])
      if (EV_SPEAKS) { kn++; kv[kn] = EV_ROOT }
    }
    decide(kv, kn, DEFQUORUM)
    if (D_VERDICT == "DIVERGED") DIVCOUNT++
    EV_VERDICT = D_VERDICT
    EV_SPEAKS  = (D_VERDICT == "AGREE") ? 1 : 0
    EV_ROOT    = EV_SPEAKS ? D_BEST : ""
    return
  }
  if (ohas[node SUBSEP "root"]) {
    EV_ROOT    = resolve(nval[oval[node SUBSEP "root"]])
    EV_SPEAKS  = 1
    EV_VERDICT = "AGREE"
    return
  }
  fatal("tree node is neither a level (children) nor a carrier (root)")
}

function climb_run(inp) {
  DIVCOUNT = 0
  ev(oval[inp SUBSEP "tree"])
  # ASSUMPTION (spec silent): clean == (divergences == 0).
  return "{\"clean\":" ((DIVCOUNT == 0) ? "true" : "false") \
         ",\"divergences\":" DIVCOUNT \
         ",\"speaks_upward\":" (EV_SPEAKS ? "true" : "false") \
         ",\"verdict\":\"" EV_VERDICT "\"}"
}

# --------------------------------------------------------------------- main --
BEGIN {
  for (i = 1; i < 128; i++) ORD[sprintf("%c", i)] = i
  NULBYTE = "\\000"
  DEFQUORUM = 2
  nid = 0; tn = 0
}

{ TXT = TXT $0 "\n" }

END {
  if (FATAL) exit 3
  tokenize()
  tp = 1
  top = pv()
  if (ntype[top] != "obj") fatal("top level of the spec is not an object")

  SPECSTR = nval[oval[top SUBSEP "spec"]]
  PUBROOT = nval[oval[top SUBSEP "root"]]

  rmap = oval[top SUBSEP "roots"]
  for (i = 1; i <= ocnt[rmap]; i++) {
    k = okeys[rmap SUBSEP i]
    SYM[k] = nval[oval[rmap SUBSEP k]]
  }

  vecs = oval[top SUBSEP "vectors"]
  nv = acnt[vecs]
  for (i = 1; i <= nv; i++) {
    nd = aval[vecs SUBSEP i]
    vid[i] = nval[oval[nd SUBSEP "id"]]
    vnode[vid[i]] = nd
  }
  isort(vid, nv)                          # "for each vector sorted by id"

  fails = 0
  # "sha256 over spec, then for each vector sorted by id, a NUL byte, the id,
  #  a NUL byte, and the canonical JSON of expected"
  # ASSUMPTION: "over spec" means the value of the "spec" field, the version
  # string, not the whole document.
  FMTC = oct(SPECSTR)                     # stream built from MY results
  FMTP = FMTC                             # stream built from the PUBLISHED expected

  print "vector                          result"
  print "------------------------------  ------"
  for (i = 1; i <= nv; i++) {
    id  = vid[i]
    nd  = vnode[id]
    inp = oval[nd SUBSEP "input"]
    exq = oval[nd SUBSEP "expected"]
    op  = nval[oval[inp SUBSEP "op"]]

    if      (op == "attest") got = attest_run(inp)
    else if (op == "climb")  got = climb_run(inp)
    else { got = "<unknown op \"" op "\">" }

    want = canon(exq)
    if (got == want) {
      printf("%-30s  PASS\n", id)
    } else {
      fails++
      printf("%-30s  FAIL\n", id)
      printf("    expected: %s\n", want)
      printf("    got     : %s\n", got)
    }
    FMTC = FMTC NULBYTE oct(id) NULBYTE oct(got)
    FMTP = FMTP NULBYTE oct(id) NULBYTE oct(want)
  }

  printf("\n%d of %d vectors matched.\n", nv - fails, nv)

  print FMTC   > (OUT "/fmt_computed")
  print FMTP   > (OUT "/fmt_published")
  print PUBROOT > (OUT "/pubroot")
  print fails  > (OUT "/fails")
  print nv     > (OUT "/count")
}
AWK_ENGINE_EOF

awk -v OUT="$TMPD" -f "$TMPD/engine.awk" "$SPEC"
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "conformance_check: the spec could not be parsed or evaluated" >&2
  exit 3
fi

FAILS=`cat "$TMPD/fails"`
PUBROOT=`cat "$TMPD/pubroot"`
FMTC=`cat "$TMPD/fmt_computed"`
FMTP=`cat "$TMPD/fmt_published"`

# Materialise the byte streams. Every byte is a \NNN escape, so there is no
# format-specifier hazard and no need for a --  the format holds no %.
printf "$FMTC" > "$TMPD/stream_computed.bin"
printf "$FMTP" > "$TMPD/stream_published.bin"

ROOT_COMPUTED=`hash_file "$TMPD/stream_computed.bin"`
ROOT_PUBLISHED_INPUTS=`hash_file "$TMPD/stream_published.bin"`

echo ""
echo "root from MY results        : $ROOT_COMPUTED"
echo "root from published expected: $ROOT_PUBLISHED_INPUTS"
echo "root published in the spec  : $PUBROOT"

STATUS=0
if [ "$FAILS" -ne 0 ]; then STATUS=1; fi
if [ "$ROOT_COMPUTED" != "$PUBROOT" ]; then
  echo ""
  echo "ROOT MISMATCH: the root recomputed from this implementation's results"
  echo "does not equal the root published in the spec."
  STATUS=1
else
  echo ""
  echo "ROOT MATCHES."
fi

exit $STATUS
