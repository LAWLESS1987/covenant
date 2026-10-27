#!/usr/bin/env python3
"""
run_with_claude_judge.py -- run a Covenant node whose ethics gate is CLAUDE,
via a shared folder, instead of an API key or the insecure mock.

HOW IT WORKS
  The node's ethics gate calls judge.evaluate(data, principles) for every
  transaction. This launcher registers a FileJudge that:
    * writes what needs judging to  judge_queue/requests/<key>.json
    * waits for a verdict at         judge_queue/verdicts/<key>.json
    * returns that verdict to the node (or fails CLOSED on timeout)
  Claude, watching the connected folder, reads each request and writes the
  verdict. The node admits ONLY transactions Claude has approved; anything with
  no verdict waits, then fails closed. That is a real gate -- not the keyword
  mock -- with a human/Claude decision in the loop, and no API key.

  The verdict key is a hash of the transaction DATA (what the gate actually
  judges), so a verdict Claude writes in advance is found instantly and the node
  never blocks. Novel data with no verdict blocks up to COVENANT_JUDGE_TIMEOUT.

RUN (same args as the node):
  set COVENANT_DB_PATH=nodeA_prod.db
  python run_with_claude_judge.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021
"""
import os, sys, json, time, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov

QUEUE = os.path.abspath(os.environ.get("COVENANT_JUDGE_QUEUE", "judge_queue"))
REQ = os.path.join(QUEUE, "requests")
VER = os.path.join(QUEUE, "verdicts")
os.makedirs(REQ, exist_ok=True)
os.makedirs(VER, exist_ok=True)


def _key(data) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:24]


class FileJudge(cov.ReasoningJudge):
    """Defers each judgment to Claude via the shared folder. Fails CLOSED."""

    def __init__(self, judge_id="claudefile:0"):
        self.judge_id = judge_id
        self.timeout = float(os.environ.get("COVENANT_JUDGE_TIMEOUT", "180"))
        self.poll = 1.0

    def evaluate(self, data, principles):
        k = _key(data)
        vpath = os.path.join(VER, k + ".json")
        # record the pending decision so Claude can see exactly what is asked
        try:
            with open(os.path.join(REQ, k + ".json"), "w") as f:
                json.dump({"key": k, "data": data, "principles": principles,
                           "ts": time.time()}, f, indent=2, default=str)
        except Exception:
            pass
        deadline = time.time() + self.timeout
        while True:
            if os.path.exists(vpath):
                try:
                    v = json.load(open(vpath))
                    return cov.JudgmentResult(
                        bool(v.get("violates", True)),
                        f"[claude] {v.get('reasoning', '(no reasoning)')}",
                        principle_violated=v.get("principle_violated"),
                        judge_id=self.judge_id,
                        benefit_estimate=float(v.get("benefit", 0.5)))
                except Exception:
                    pass  # verdict half-written; try again next poll
            if time.time() >= deadline:
                return cov.JudgmentResult(
                    True, "no verdict from Claude within timeout -- failing closed",
                    judge_id=self.judge_id)
            time.sleep(self.poll)


cov.JudgeProviderRegistry.register(
    "claudefile", lambda i: FileJudge(judge_id=f"claudefile:{i}"))
# force this provider and make sure the insecure mock is not in play
os.environ["COVENANT_JUDGE_PROVIDERS"] = "claudefile"
os.environ.pop("COVENANT_INSECURE_MOCK_JUDGE", None)

print(f"[claude-judge] queue at {QUEUE} (requests/ and verdicts/); "
      f"timeout {os.environ.get('COVENANT_JUDGE_TIMEOUT', '180')}s, fail-closed")

if __name__ == "__main__":
    cov.main()
