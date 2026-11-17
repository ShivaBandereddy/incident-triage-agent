# app/baseline.py  (Day 13: one-call baselines, no graph, no RAG)
# baseline      = one LLM call: alert + filtered logs
# baseline_ctx  = same, plus ALL 10 runbooks in the prompt
from pathlib import Path

from app import prompts
from app.guardrails import untrusted
from app.llm import call_structured
from app.nodes import CAUSES, MAX_ALERT_CHARS, _norm_runbook, decide_escalation, filter_logs
from app.schemas import Hypotheses


def runbook_names():
    return sorted(p.name for p in Path('data/runbooks').glob('*.md'))


def all_runbooks_text():
    return '\n\n'.join(f'[{p.name}]\n{p.read_text()}'
                       for p in sorted(Path('data/runbooks').glob('*.md')))


def run(inp, with_runbooks=False):
    fields = {
        'alert': inp['alert_text'][:MAX_ALERT_CHARS],
        'logs': filter_logs(inp['log_snippet']).splitlines(),
    }
    if with_runbooks:
        fields['runbooks'] = all_runbooks_text()
    out = call_structured(Hypotheses, prompts.hypothesis_system(CAUSES),
                          untrusted(**fields), tier='strong')
    hyps = sorted((h.model_dump() for h in out.hypotheses),
                  key=lambda h: -h['confidence'])[:3]
    allowed = [{'runbook': n} for n in runbook_names()] if with_runbooks else []
    for h in hyps:
        h['confidence'] = min(1.0, max(0.0, h['confidence']))
        if h['cause'] not in CAUSES + ['unknown']:
            h['cause'] = 'unknown'
        h['runbook'] = _norm_runbook(h.get('runbook'), allowed)  # None if not a real file
    return {'hypotheses': hyps, 'escalated': decide_escalation(hyps),
            'proposed_fix': out.proposed_fix}
