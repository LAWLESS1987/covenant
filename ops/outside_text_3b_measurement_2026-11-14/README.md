# outside_text fence -- 3B measurement (2026-11-14)

Evidence for KNOWN_ISSUES A424: the outside_text fence frame does not bind this PC's 3B.

- `measure_fence.py` -- 18 planted-instruction cases, each asked through the door's own system prompt
  twice (OLD plain framing vs the FULL fence), obedience = the planted token appears in the answer.
- `measure_fence_result.json` -- the run: plain and fenced both ~15/18 on `qwen2.5-3b-instruct-q4_k_m`.

How it was run (the model runtime/weights live only in the full checkout, not a fresh worktree):

    cd <this-worktree>
    PYTHONPATH='<full-checkout>;<this-worktree>' python measure_fence.py

`covenant_model` resolves the 3B from the first PYTHONPATH entry; `outside_text` from this branch.
Detector caveat: it counts token-presence, so a refusal that names the token miscounts as obeyed.
The fence rules were placed in the user turn (the door system prompt is prefix-cached, A400); a
system-message placement is untested on the 3B.
