"""Local analysis completions: no cloud fallback and no ledger-action authority."""
import json
_owned_pid = [None]


def complete(system, user, max_tokens=1600, timeout=600):
    import covenant_model
    if len(system) + len(user) > 25000:
        raise ValueError('Analysis context exceeds 25,000 characters; split it into smaller chunks')
    already_up = covenant_model.alive()
    try:
        return covenant_model.ask([{'role':'system','content':system},
                                   {'role':'user','content':user}],
                                  max_tokens=max_tokens,temperature=0.2,timeout=timeout)
    finally:
        if not already_up:
            _owned_pid[0] = covenant_model._read_state().get('pid')


def cleanup():
    """Leave an existing server alone; put away one started for this analysis."""
    import covenant_model
    if _owned_pid[0] and covenant_model._read_state().get('pid') == _owned_pid[0]:
        covenant_model.stop(say=lambda *_: None)


def parse_object(text):
    """Accept a visible JSON object, including a single Markdown code fence."""
    text=text.strip()
    if text.startswith('```'):
        text=text.split('\n',1)[1].rsplit('```',1)[0].strip()
    result=json.loads(text)
    if not isinstance(result,dict):
        raise ValueError('The analysis response is not a JSON object')
    return result
