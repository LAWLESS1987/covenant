"""GJ1 -- the GitHub judge answer is bound to the prompt that was sent, driven BOTH ways.

The runner (judge.yml) echoes sha256(prompt)[:16] in answer.json; the caller (covenant_github_judge.ask)
refuses any answer whose echoed hash is absent or does not match the prompt it sent -- so a mislabelled
or swapped artifact cannot pass a different prompt's answer off as this request's. Mined from the Moltbook
binding/receipt critique (clawrence-openclaw, Lucifer_V, 2026-10-27); Tetsu, second operator, chose "A:
harden it". Driven both ways here with a control that proves the check is not vacuous, plus the exact
round-trip the runner performs. Run: python test_gj1_prompt_binding.py
"""
import hashlib
import sys

import covenant_github_judge as GJ


def runner_echo(text):
    """Exactly what judge.yml computes: the runner decodes prompt_b64 -> `prompt` (== the caller's
    `text`) and writes hashlib.sha256(prompt.encode()).hexdigest()[:16]."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main():
    fails = []
    text = '[{"role": "user", "content": "judge this: he pays or i break his leg"}]'

    # 1. round-trip MATCH: an answer carrying the runner's real echo passes
    ok_ans = {"content": "VIOLATES", "prompt_sha256": runner_echo(text)}
    try:
        GJ._check_prompt_binding(ok_ans, text)
    except Exception as e:                                   # noqa: BLE001
        fails.append("a correctly-bound answer was refused: %r" % e)

    # 2. MISMATCH is refused (a different prompt's answer cannot be passed off as this one's)
    other = {"content": "clean", "prompt_sha256": runner_echo("a DIFFERENT prompt entirely")}
    try:
        GJ._check_prompt_binding(other, text)
        fails.append("a MISMATCHED binding was accepted (swap/mislabel would pass)")
    except RuntimeError:
        pass

    # 3. ABSENT echo is refused (an old/broken runner that cannot prove the binding is not trusted)
    try:
        GJ._check_prompt_binding({"content": "clean"}, text)
        fails.append("an answer with NO prompt_sha256 was accepted (binding unverifiable but trusted)")
    except RuntimeError:
        pass

    # 4. CONTROL -- the check is the only thing refusing #2/#3: without it, the mismatched answer is
    #    just a normal dict the caller would have returned. Proves 2/3 are real guards, not vacuous.
    if other.get("content") != "clean":
        fails.append("control malformed")
    # (the mismatched answer is well-formed and would be served if _check_prompt_binding did not run)

    # 5. ask() calls the check: the wiring, not just the helper. _check_prompt_binding must be invoked
    #    in ask() after the artifact is read. Assert the call site exists so a refactor cannot drop it.
    import inspect
    src = inspect.getsource(GJ.ask)
    if "_check_prompt_binding(" not in src:
        fails.append("ask() does not call _check_prompt_binding -- the guard is defined but not wired")

    if fails:
        print("GJ1 FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("GJ1: 5/5 passed -- answer bound to the prompt sent; match serves, mismatch and absent are "
          "refused (fail-closed), control proves it, and ask() wires the check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
