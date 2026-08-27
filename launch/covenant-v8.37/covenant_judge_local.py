#!/usr/bin/env python3
"""
covenant_judge_local.py -- an OpenAI-compatible judge provider.

WHY THIS EXISTS
  The quorum's diversity check requires >= 2 distinct providers, and the core
  file's own HONESTY NOTE admits the check tests LABEL diversity, not REASONING
  diversity -- two MockJudges with different ids satisfy it while running
  identical logic. Real diversity needs genuinely different models.

  It also fixes a harder problem: claude/openai/google all need an API key and
  a live internet connection. A judge that cannot be reached RAISES, and
  QuorumJudge counts a raising judge as a VIOLATION. So on a flaky connection
  the ethics gate does not degrade -- it slams shut. Every cloud judge you add
  is another single point of failure for your own chain.

  A locally-hosted model has no key and no network dependency. That is the only
  configuration where the gate keeps working on a laptop in a car.

BOTH BACKENDS SPEAK THE SAME PROTOCOL
  DeepSeek's API and Ollama's API are both OpenAI-chat-compatible, so one class
  covers both -- only the base URL changes.

    # local, no key, works offline:
    export COVENANT_LOCAL_JUDGE_URL=http://localhost:11434/v1/chat/completions
    export COVENANT_LOCAL_JUDGE_MODEL=qwen3.6:latest
    export COVENANT_JUDGE_PROVIDERS=claude,local

    # DeepSeek's hosted API (needs a key, needs the internet):
    export DEEPSEEK_API_KEY=sk-...
    export COVENANT_JUDGE_PROVIDERS=claude,deepseek

    # Mistral's hosted API:
    export MISTRAL_API_KEY=...
    export COVENANT_JUDGE_PROVIDERS=claude,mistral

A NOTE ON WHAT THIS DOES NOT DO
  A second model is a second opinion, not a guarantee. Two models trained on
  overlapping data share blind spots, and a small quantised local model is a
  WEAKER judge than a frontier one -- it will miss things Claude catches. It
  buys independence and availability, not more intelligence.
"""
from __future__ import annotations
import os
import json
import covenant_unified_v8 as cov


import re as _re


def _extract_verdict_json(text: str) -> str:
    """Pull the verdict object out of whatever a local model actually emitted.

    The core parser takes everything from the first `{` to the last `}`. That
    is fine for a frontier model returning clean JSON and breaks on two things
    local models do constantly -- both verified against the real parser:

      * REASONING BLOCKS. deepseek-r1 and friends emit <think>...</think>
        first. Any `{` in that monologue becomes the start of the "JSON", and
        the parse dies. The judge then raises, and QuorumJudge counts a raising
        judge as a VIOLATION -- so the model reasoning out loud silently
        rejects your transaction.

      * TWO OBJECTS. A scratchpad object followed by the answer spans both,
        producing `{...}\n{...}` which is not valid JSON.

    So: strip the thinking, strip fences, then walk the text for balanced
    objects and take the LAST one that actually carries a `violates` key --
    the answer, not the scratchpad."""
    t = _re.sub(r"<think>.*?</think>", " ", text, flags=_re.S | _re.I)
    t = _re.sub(r"<\|?(?:begin|end)_of_thought\|?>", " ", t, flags=_re.I)
    t = _re.sub(r"```(?:json)?", " ", t)

    objs, depth, start, in_str, esc = [], 0, None, False, False
    for i, ch in enumerate(t):
        if in_str:
            if esc:            esc = False
            elif ch == "\\":  esc = True
            elif ch == '"':    in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth:
                depth -= 1
                if depth == 0 and start is not None:
                    objs.append(t[start:i + 1])
    for cand in reversed(objs):
        try:
            if "violates" in json.loads(cand):
                return cand
        except Exception:
            continue
    if objs:
        return objs[-1]
    raise ValueError(f"no JSON object in judge response: {text[:200]!r}")


class OpenAICompatJudge(cov._APIReasoningJudge):
    """Any endpoint that speaks the OpenAI /chat/completions shape."""
    provider = "local"
    env_var = "COVENANT_LOCAL_JUDGE_KEY"     # may be unset for a local server
    judge_id = "local:1"
    default_url = "http://localhost:11434/v1/chat/completions"
    default_model = "qwen3.6:latest"   # what is actually installed on this machine

    def __init__(self, *a, **kw):
        # A local server needs no key. The base class constructs fine without
        # one but then FAILS CLOSED at evaluate() -- "no API key, denying by
        # default" -- which for a keyless local endpoint would reject every
        # transaction for a reason that does not apply. A clearly-fake
        # placeholder gets past that check without weakening it for the real
        # cloud providers, and _call() strips it before sending.
        if not os.environ.get(self.env_var):
            os.environ[self.env_var] = "local-no-key"
        super().__init__(*a, **kw)

    def _parse_verdict(self, text: str):
        # Same contract as the base class, tolerant of how local models talk.
        return super()._parse_verdict(_extract_verdict_json(text))

    def _endpoint(self) -> str:
        return os.environ.get("COVENANT_LOCAL_JUDGE_URL", self.default_url)

    def _model(self) -> str:
        return (self.model or os.environ.get("COVENANT_LOCAL_JUDGE_MODEL")
                or self.default_model)

    def _call(self, data, principles):
        import requests
        headers = {"content-type": "application/json"}
        key = self.api_key
        if key and key != "local-no-key":
            headers["Authorization"] = f"Bearer {key}"
        resp = requests.post(
            self._endpoint(),
            headers=headers,
            json={"model": self._model(),
                  "messages": [{"role": "user",
                                "content": self._build_prompt(data, principles)}],
                  "max_tokens": 512},
            # Local models on CPU are SLOW. 30s (the cloud default) times out
            # mid-generation and the raise is then counted as a violation --
            # i.e. your own slow hardware silently rejects your transactions.
            timeout=float(os.environ.get("COVENANT_LOCAL_JUDGE_TIMEOUT", "180")),
        )
        resp.raise_for_status()
        return self._parse_verdict(resp.json()["choices"][0]["message"]["content"])


class MistralJudge(OpenAICompatJudge):
    """Mistral's platform API (api.mistral.ai), which speaks the OpenAI chat
    shape. Needs MISTRAL_API_KEY from console.mistral.ai.

    NOT the same thing as Mistral Vibe. Vibe is their chat + coding agent
    (terminal CLI, IDE plugins, mobile). It is an interactive agent, not a
    classification endpoint, and its CLI talks only to Mistral's cloud with no
    configurable base URL -- so it cannot be wired in as a judge. What you want
    here is the plain API with a model like mistral-medium-3.5.

    For a KEYLESS offline Mistral judge, use provider 'local' with Ollama and a
    Mistral open-weight model (mistral, mixtral, devstral, magistral). Same
    class, no key, no internet."""
    provider = "Mistral"
    env_var = "MISTRAL_API_KEY"
    judge_id = "mistral:1"
    default_url = "https://api.mistral.ai/v1/chat/completions"
    default_model = "mistral-medium-3.5"

    def __init__(self, *a, **kw):
        if not os.environ.get(self.env_var):
            raise ValueError(
                "MISTRAL_API_KEY is not set (get one at console.mistral.ai). "
                "For a keyless offline judge use provider 'local' with Ollama "
                "running a Mistral open-weight model.")
        cov._APIReasoningJudge.__init__(self, *a, **kw)

    def _endpoint(self): return os.environ.get("MISTRAL_JUDGE_URL", self.default_url)
    def _model(self):    return self.model or os.environ.get("MISTRAL_JUDGE_MODEL") or self.default_model


class DeepSeekJudge(OpenAICompatJudge):
    """DeepSeek's hosted API. Needs DEEPSEEK_API_KEY and the internet."""
    provider = "DeepSeek"
    env_var = "DEEPSEEK_API_KEY"
    judge_id = "deepseek:1"
    default_url = "https://api.deepseek.com/v1/chat/completions"
    default_model = "deepseek-chat"

    def __init__(self, *a, **kw):
        if not os.environ.get(self.env_var):
            raise ValueError(
                "DEEPSEEK_API_KEY is not set. For a keyless offline judge use "
                "provider 'local' with a running Ollama instead.")
        # skip OpenAICompatJudge's placeholder-key path
        cov._APIReasoningJudge.__init__(self, *a, **kw)

    def _endpoint(self): return os.environ.get("DEEPSEEK_JUDGE_URL", self.default_url)
    def _model(self):    return self.model or os.environ.get("DEEPSEEK_JUDGE_MODEL") or self.default_model


cov.JudgeProviderRegistry.register("local",    lambda i: OpenAICompatJudge(judge_id=f"local:{i}"))
cov.JudgeProviderRegistry.register("deepseek", lambda i: DeepSeekJudge(judge_id=f"deepseek:{i}"))
cov.JudgeProviderRegistry.register("mistral",  lambda i: MistralJudge(judge_id=f"mistral:{i}"))
