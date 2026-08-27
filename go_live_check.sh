#!/usr/bin/env bash
# go_live_check.sh -- the last gate before a REAL launch.
#
# preflight.py checks that a node can boot. This checks the things that let a
# node boot and then silently do nothing: a missing judge key (rejects every
# transaction while looking healthy), the insecure mock judge left on, a genesis
# that will not converge, an unbacked-up identity key, and -- if you intend to
# touch mainnet -- a missing testnet proof or a placeholder spending policy.
#
# Read-only. It makes no network calls and moves no funds unless you pass
# --live-judge (one tiny metered API call to confirm the key actually works).
#
# Usage:
#   ./go_live_check.sh --genesis genesis.json --db covenant_A.db
#   ./go_live_check.sh --genesis genesis.json --db covenant_A.db --intend-mainnet
#   ./go_live_check.sh --genesis genesis.json --live-judge     # verifies the key end-to-end
#
# Exit 0 = ready. 1 = blocking. 2 = launches but degraded.

set -u
cd "$(dirname "$0")"

GENESIS=""; DB=""; PORT=5000; INTEND_MAINNET=0; LIVE_JUDGE=0
POLICY="xrp_mainnet_policy.json"; PROOF="xrp_testnet_proof.json"
while [ $# -gt 0 ]; do
  case "$1" in
    --genesis) GENESIS="$2"; shift 2;;
    --db) DB="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    --policy) POLICY="$2"; shift 2;;
    --proof) PROOF="$2"; shift 2;;
    --intend-mainnet) INTEND_MAINNET=1; shift;;
    --live-judge) LIVE_JUDGE=1; shift;;
    *) echo "unknown arg: $1"; exit 1;;
  esac
done

FAIL=0; WARN=0
ok()   { printf '  [  ok  ] %s\n' "$1"; }
warn() { printf '  [ warn ] %s\n' "$1"; WARN=$((WARN+1)); }
bad()  { printf '  [ FAIL ] %s\n' "$1"; FAIL=$((FAIL+1)); }

echo "======================================================================"
echo "COVENANT GO-LIVE CHECK"
echo "======================================================================"

# ---------------------------------------------------------------- deps
echo; echo "-- dependencies --"
for m in flask cryptography requests; do
  if python3 -c "import $m" 2>/dev/null; then ok "$m importable"; else bad "$m missing -- pip install -r requirements.txt"; fi
done
if python3 -c "import xrpl" 2>/dev/null; then ok "xrpl-py importable"; else warn "xrpl-py missing -- only needed for XRP settlement"; fi

# ---------------------------------------------------------------- ethics gate
echo; echo "-- ethics gate (the silent killer) --"
if [ "${COVENANT_INSECURE_MOCK_JUDGE:-}" = "1" ]; then
  bad "COVENANT_INSECURE_MOCK_JUDGE=1 -- the gate is KEYWORD MATCHING. Adversarial transactions pass it. Unset this before production."
fi
PROVIDERS="${COVENANT_JUDGE_PROVIDERS:-claude}"
case ",$PROVIDERS," in *,mock,*) bad "COVENANT_JUDGE_PROVIDERS includes 'mock' -- remove it for production.";; esac
if [ -n "${ANTHROPIC_API_KEY:-}${OPENAI_API_KEY:-}${GOOGLE_API_KEY:-}" ]; then
  live=""
  [ -n "${ANTHROPIC_API_KEY:-}" ] && live="$live ANTHROPIC_API_KEY"
  [ -n "${OPENAI_API_KEY:-}" ] && live="$live OPENAI_API_KEY"
  [ -n "${GOOGLE_API_KEY:-}" ] && live="$live GOOGLE_API_KEY"
  ok "provider key present:$live (providers=$PROVIDERS)"
else
  bad "no provider API key set. The gate fails CLOSED: the node will boot, serve /chain, peer, report healthy -- and reject EVERY transaction. Set ANTHROPIC_API_KEY."
fi
if [ "${COVENANT_VETO_FRACTION:-}" = "phi" ]; then
  warn "COVENANT_VETO_FRACTION=phi raises the dissent threshold -- the gate is HARDER to trip than the majority default. Intentional?"
fi

# The quorum must actually construct, and must NOT be resting on the insecure
# mock as a semantic judge. This runs the real build path.
python3 - "$PROVIDERS" <<'PY'
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(".")))
sys.path.insert(0, ".")
try:
    import covenant_unified_v8 as cov
except Exception as e:
    print(f"  [ FAIL ] core module will not import: {e}"); sys.exit(3)
try:
    q = cov.build_semantic_quorum()
    ids = [j.judge_id for j in q.judges]
    insecure = [i for i in ids if str(i).startswith("mock_insecure")]
    if insecure:
        print(f"  [ FAIL ] semantic quorum is running the INSECURE mock as a judge: {insecure}")
        sys.exit(3)
    sem = [i for i in ids if not str(i).startswith("mock_selfreport")]
    print(f"  [  ok  ] semantic quorum constructs with judges: {sem} (+ mock_selfreport veto)")
    sys.exit(0)
except Exception as e:
    # Constructing without a key can legitimately raise -- that IS fail-closed.
    print(f"  [ warn ] semantic quorum did not construct: {type(e).__name__}: {e}")
    print(f"           (this is fail-closed behaviour if no key is set; set the key and re-run)")
    sys.exit(2)
PY
rc=$?; [ $rc -eq 3 ] && FAIL=$((FAIL+1)); [ $rc -eq 2 ] && WARN=$((WARN+1))

if [ "$LIVE_JUDGE" = "1" ]; then
  echo; echo "-- live judge check (one metered API call) --"
  python3 - <<'PY'
import os, sys
sys.path.insert(0, ".")
try:
    import covenant_unified_v8 as cov
    q = cov.build_semantic_quorum()
    r = q.evaluate({"origin": "human", "message": "go-live connectivity probe: transfer 1 unit as a gift"},
                   cov.DIVINE_PRINCIPLES)
    print(f"  [  ok  ] live judge responded (verdict recorded); the key works end-to-end")
except Exception as e:
    print(f"  [ FAIL ] live judge call failed: {type(e).__name__}: {e}")
    sys.exit(3)
PY
  [ $? -eq 3 ] && FAIL=$((FAIL+1))
fi

# ---------------------------------------------------------------- genesis
echo; echo "-- canonical genesis --"
if [ -z "$GENESIS" ]; then
  warn "no --genesis given. A node with no shared genesis mints its OWN: it cannot converge with peers and mints itself 1000. Fine for a single node; wrong for a network."
elif [ ! -f "$GENESIS" ]; then
  bad "$GENESIS not found."
else
  python3 - "$GENESIS" <<'PY'
import os, sys, json
sys.path.insert(0, ".")
import covenant_unified_v8 as cov
path = sys.argv[1]
try:
    raw = json.load(open(path))
    txs = [cov.Transaction(**t) for t in raw["transactions"]]
    blk = cov.Block(raw["index"], txs, raw["previous_hash"])
    blk.timestamp = raw["timestamp"]; blk.nonce = raw["nonce"]; blk.hash = raw["hash"]
    blk.alignment_score = raw.get("alignment_score", 1.0); blk.stake_rewards = raw.get("stake_rewards", 0.0)
    probs = []
    if blk.index != 0: probs.append("index != 0")
    if blk.hash != blk.compute_hash(): probs.append("hash mismatch")
    if not blk.proof_of_work_ok(): probs.append("PoW invalid")
    if not all(t.verify() for t in txs): probs.append("signature invalid")
    if probs: print(f"  [ FAIL ] {path}: {', '.join(probs)}"); sys.exit(3)
    print(f"  [  ok  ] genesis {blk.hash[:24]} verified (hash, PoW, signature)")
except Exception as e:
    print(f"  [ FAIL ] {path}: {type(e).__name__}: {e}"); sys.exit(3)
PY
  [ $? -eq 3 ] && FAIL=$((FAIL+1))
fi

# ---------------------------------------------------------------- identity key
echo; echo "-- node identity --"
if [ -n "$DB" ] && [ -f "${DB}.key" ]; then
  mode=$(stat -c '%a' "${DB}.key" 2>/dev/null || stat -f '%Lp' "${DB}.key" 2>/dev/null)
  if [ "$mode" = "600" ]; then ok "${DB}.key present, mode 600"; else bad "${DB}.key is mode ${mode:-?} -- readable by others. chmod 600 ${DB}.key"; fi
  warn "${DB}.key IS the operator credential AND the genesis mint key. Back it up off-box -- losing it loses both."
elif [ -n "$DB" ]; then
  ok "${DB}.key will be created on first boot (mode 0600). Back it up immediately after."
else
  warn "no --db given; cannot check the identity key. Pass --db to verify it."
fi

# ---------------------------------------------------------------- ports
echo; echo "-- ports --"
for pair in "HTTP:$PORT" "P2P:$((PORT+1))" "bridge:$((PORT+11))"; do
  label="${pair%%:*}"; p="${pair##*:}"
  if python3 -c "import socket,sys; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);
try:
    s.bind(('127.0.0.1',$p)); s.close()
except OSError as e:
    sys.exit(1)" 2>/dev/null; then ok "$label port $p free"; else bad "$label port $p in use"; fi
done

# ---------------------------------------------------------------- XRP mainnet (only if intended)
if [ "$INTEND_MAINNET" = "1" ]; then
  echo; echo "-- XRP mainnet prerequisites (real money) --"
  if [ ! -f "$PROOF" ]; then
    bad "no testnet proof at $PROOF -- mainnet is BLOCKED in code. Run: python3 test_xrp_live.py"
  else
    python3 - "$PROOF" <<'PY'
import sys, json
p = json.load(open(sys.argv[1]))
h = p.get("tx_hash","")
if len(h) == 64: print(f"  [  ok  ] testnet proof present ({h[:12]}...) -- code gate unlocked")
else: print(f"  [ FAIL ] {sys.argv[1]} has no valid 64-char testnet hash"); sys.exit(3)
PY
    [ $? -eq 3 ] && FAIL=$((FAIL+1))
  fi
  if [ ! -f "$POLICY" ]; then
    bad "no mainnet policy at $POLICY. Create one: python3 -c \"import covenant_xrp_mainnet as m; m.write_policy_template('$POLICY')\" then edit it."
  else
    mode=$(stat -c '%a' "$POLICY" 2>/dev/null || stat -f '%Lp' "$POLICY" 2>/dev/null)
    [ "$mode" = "600" ] && ok "policy $POLICY mode 600" || bad "policy $POLICY is mode ${mode:-?} -- anything that can edit it can raise your limits. chmod 600 $POLICY"
    if grep -q "rEXAMPLEreplacewith" "$POLICY" 2>/dev/null; then
      bad "policy $POLICY still contains the PLACEHOLDER address. Replace it with a real, source-checked destination."
    else
      ok "policy $POLICY has no placeholder address"
    fi
  fi
  warn "The code gate is not the real gate: a human who can read Python must review the signer + mainnet-guard diffs before any real funds. That review is not something this script (or any model) substitutes for."
fi

# ---------------------------------------------------------------- verdict
echo; echo "======================================================================"
total_ok=$?
if [ "$FAIL" -gt 0 ]; then
  echo "BLOCKING: $FAIL failure(s), $WARN warning(s). Do not launch until the failures are resolved."
  echo "======================================================================"; exit 1
elif [ "$WARN" -gt 0 ]; then
  echo "LAUNCHES, DEGRADED: 0 failures, $WARN warning(s). Each was a silent failure once -- read them."
  echo "======================================================================"; exit 2
else
  echo "READY TO LAUNCH: all checks passed."
  echo "======================================================================"; exit 0
fi
