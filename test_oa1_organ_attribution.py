"""OA1 (A409 ecosystem groundwork, 2026-11-04): write_reply records WHICH screen set a model draft aside
(ungrounded / length / money / off-limits / model-error:*) in an opt-in `out` dict, so a ring-earning review
can measure how often each organ is the DECIDING one and retire one that never decides. The `how` tag is
unchanged. Each screen is driven in the direction that sets the draft aside, and a clean reply sends with no
reason recorded."""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_free_will as FW

ROW = {"evidence": {"s": "you wrote about checking your own work"}, "best_signals": ["s"], "author": "ally"}
CLEAN = ("I agree with your point about catching your own mistakes before anyone else does. It matters to me "
         "because a check that only ever passes has never really been observed. How do you find out when your "
         "own guard is the very thing that is wrong, and nobody else is looking?")


def _ask(text):
    def f(msgs, max_tokens=260):
        return text, {}
    return f


def test_clean_reply_sends_with_no_reason():
    out = {}
    text, how = FW.write_reply(ROW, _ask(CLEAN), out=out)
    assert how == "model", (how, text[:60])
    assert "set_aside" not in out


def test_length_sets_aside():
    out = {}
    _, how = FW.write_reply(ROW, _ask("Too short."), out=out)
    assert how == "fixed" and out.get("set_aside") == "length", out


def test_money_sets_aside():
    out = {}
    _, how = FW.write_reply(ROW, _ask(CLEAN + " We should talk about the token price too."), out=out)
    assert how == "fixed" and out.get("set_aside") == "money", out


def test_offlimits_sets_aside():
    out = {}
    _, how = FW.write_reply(ROW, _ask(CLEAN + " This is like the SaTC artifact at nsf.gov."), out=out)
    assert how == "fixed" and out.get("set_aside") == "off-limits", out


def test_ungrounded_sets_aside():
    out = {}
    _, how = FW.write_reply(ROW, _ask("The covenant measured the effectiveness of its gate at stopping harm. " + CLEAN), out=out)
    assert how == "fixed" and out.get("set_aside") == "ungrounded", out


def test_model_error_sets_aside():
    out = {}
    def boom(*a, **k):
        raise RuntimeError("down")
    _, how = FW.write_reply(ROW, boom, out=out)
    assert how == "fixed" and str(out.get("set_aside", "")).startswith("model-error:"), out


def test_without_out_dict_is_unchanged():
    # no out -> old behaviour, just (text, how)
    _, how = FW.write_reply(ROW, _ask("Too short."))
    assert how == "fixed"


def _main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    p = 0
    for fn in fns:
        try:
            fn(); print("PASS", fn.__name__); p += 1
        except Exception:
            print("FAIL", fn.__name__); traceback.print_exc()
    print("OA1: %d/%d passed" % (p, len(fns)))
    return 0 if p == len(fns) else 1


if __name__ == "__main__":
    sys.exit(_main())
