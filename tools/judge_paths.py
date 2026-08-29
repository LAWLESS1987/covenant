#!/usr/bin/env python3
"""judge_paths.py -- what judges can this node actually reach, and are they
independent? Read-only. Builds nothing into a chain, changes no config.

WHY. CONSTRAINT_COVERAGE.md argues that a single invariant core is never
complete, so PLURALITY is the coverage strategy: several judges with different
C, a median rather than a verdict. That argument is only worth anything if the
judges are really different and really reachable. Three ways it can quietly not
be true, all of which this reports:

  1. NAME COLLISION. JudgeProviderRegistry.register() is
     `cls._providers[name] = factory` with no guard, and BOTH
     covenant_judge_local.py and covenant_judge_ollama.py register "local".
     Measured 2026-08-29: after importing local then ollama,
     COVENANT_JUDGE_PROVIDERS=local silently changes from
     OpenAICompatJudge to OllamaJudge. The ethics gate's reasoning engine is
     selected by import order, with no warning anywhere.

  2. ADVERTISED BUT UNBUILDABLE. available_providers() lists names whose
     factory raises. A path that is listed and cannot be walked is worse than
     an absent one, because a quorum config referencing it looks valid.

  3. THE FAIREST JUDGE IS NOT ON THE LIST. covenant_semantic_judge registers
     itself as "semantic" only when install() is called with a registry. It is
     deterministic, versioned by model_id, needs no API key and no vendor, and
     is the only judge in this system with a MEASURED false-negative rate
     (SEM3/SEM5). By default it is not selectable.

Run:  python3 tools/judge_paths.py
"""
import importlib, os, sys, traceback

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "mock")
os.environ.setdefault("COVENANT_INSECURE_MOCK_JUDGE", "1")

import covenant_unified_v8 as cov

# --- instrument register() BEFORE importing any judge module, so collisions
#     are OBSERVED rather than inferred from reading the source.
_LOG = []          # (name, module_that_registered, replaced_something)
_orig = cov.JudgeProviderRegistry.register.__func__


def _tracking(cls, name, factory):
    caller = "?"
    for fr in traceback.extract_stack()[::-1]:
        if "covenant_unified_v8" not in fr.filename and "judge_paths" not in fr.filename:
            caller = os.path.basename(fr.filename); break
    _LOG.append((name, caller, name in cls._providers))
    return _orig(cls, name, factory)


cov.JudgeProviderRegistry.register = classmethod(_tracking)

OPTIONAL = ["covenant_judge_local", "covenant_judge_ollama"]
for m in OPTIONAL:
    try:
        importlib.import_module(m)
    except Exception as e:
        print(f"note: {m} not importable ({type(e).__name__}) -- skipped")

# semantic registers only via install(); try it, read-only
try:
    import covenant_semantic_judge as sjm
    for cand in ("semantic_judge_model.json",
                 os.path.join("pending-v8.38", "semantic_judge_model.json")):
        p = os.path.join(HERE, cand)
        if os.path.exists(p):
            sjm.install(cov.ReasoningJudge, dict, cov.JudgeProviderRegistry, p)
            break
except Exception as e:
    print(f"note: semantic judge not installed ({type(e).__name__}: {str(e)[:60]})")

print("\n" + "=" * 70)
print("PATHS TO OTHER JUDGES")
print("=" * 70)

collisions = [(n, c) for n, c, dup in _LOG if dup]
print(f"\n1. REGISTRATIONS OBSERVED ({len(_LOG)})")
for n, c, dup in _LOG:
    print(f"   {'!! REPLACED' if dup else '   new     '}  {n:<12} registered by {c}")
if collisions:
    print(f"\n   *** {len(collisions)} SILENT COLLISION(S). register() has no guard, so the")
    print("       winner is whichever module imported LAST:")
    for n, c in collisions:
        print(f"         {n!r} -> finally {c}")
else:
    print("\n   no collisions in this import set.")

print("\n2. CAN EACH ADVERTISED PATH ACTUALLY BE WALKED?")
ok, broken = [], []
for name in sorted(cov.JudgeProviderRegistry.available_providers()):
    try:
        j = cov.JudgeProviderRegistry.build(name, 0)
        impl = f"{type(j).__module__}.{type(j).__name__}"
        ok.append((name, impl))
        print(f"   OK      {name:<12} {impl}")
    except Exception as e:
        broken.append((name, f"{type(e).__name__}: {str(e).splitlines()[0][:60]}"))
        print(f"   BROKEN  {name:<12} {broken[-1][1]}")
if broken:
    print(f"\n   *** {len(broken)} provider(s) are LISTED but cannot be built. A quorum")
    print("       naming one looks valid and is not.")

print("\n3. DISTINCT IMPLEMENTATIONS (what plurality is actually available)")
impls = {}
for name, impl in ok:
    impls.setdefault(impl, []).append(name)
for impl, names in sorted(impls.items()):
    flag = "  <-- several names, one class" if len(names) > 1 else ""
    print(f"   {impl:<44} {','.join(names)}{flag}")
print(f"\n   names: {len(ok)}   distinct classes: {len(impls)}")
print("""
   CAREFUL, and this tool got it wrong before saying so: several names over one
   CLASS is not necessarily one judge. covenant_judge_ollama registers named
   configs (pc_qwen, pc_mid, pc_small) that may point at DIFFERENT MODELS, and a
   different model is a different C -- which is exactly the diversity
   CONSTRAINT_COVERAGE.md argues for. But `model` is None at construction here
   (resolved later from config/env), so weight-level diversity CANNOT be
   determined statically. This tool does not claim it either way.

   What can be said: quorum_diversity_report keys on the IMPLEMENTATION, not on
   the model. So three ollama judges running three different models count as ONE
   independent judge. That errs safe -- under-counting independence is the right
   direction for a gate -- but it gives no credit for genuinely diverse local
   models, which is a quiet disincentive to the plurality the coverage argument
   depends on.""")

print("\n4. IS THE DETERMINISTIC JUDGE REACHABLE?")
have = "semantic" in cov.JudgeProviderRegistry.available_providers()
print(f"   'semantic' registered: {'YES' if have else 'NO'}")
if not have:
    print("   It is the only judge here with a measured false-negative rate,")
    print("   needs no API key and no vendor -- and is not selectable by default.")

print("\n5. DIVERSITY MACHINERY")
for n in ("quorum_diversity_report", "quorum_diversity_warnings"):
    print(f"   cov.{n}: {'present' if hasattr(cov, n) else 'ABSENT'}")
print("\n(read-only; nothing was configured or changed)")
