# app/nodes.py (Day 9 v1: log filter + intake + analyze_logs + hypothesize)
import re
from pathlib import Path

from app import prompts
from app.guardrails import untrusted
from app.llm import call_structured
from app.schemas import Findings, Hypotheses, Intake

CAUSES = sorted(p.stem.replace('-', '_') for p in Path('data/runbooks').glob('*.md'))
CONF_THRESHOLD = 0.5
MAX_RETRIES = 2
MAX_ALERT_CHARS = 2000
KEYWORDS = re.compile(
    r'error|fail|warn|down|expired|latency|timeout|degrad|lost|unreach|space|drift|offset|'
    r'swap|balloon|dead|refused|denied|skew|resolve|servfail|predictive|offline|flap|not responding',
    re.I,
)


def filter_logs(log_snippet, max_lines=80):
    """Keep suspicious lines, collapse near-duplicates, cap the size."""
    seen = {}
    for order, line in enumerate(log_snippet.splitlines()):
        hits = len(KEYWORDS.findall(line))
        if not hits:
            continue
        key = re.sub(r'[0-9a-f]{6,}|\d+', '#', line.lower())
        if key in seen:
            seen[key][3] += 1
        else:
            seen[key] = [hits, order, line, 1]
    items = list(seen.values())
    if len(items) > max_lines:
        items = sorted(items, key=lambda x: (-x[0], x[1]))[:max_lines]
    items.sort(key=lambda x: x[1])
    return '\n'.join(l + (f' (x{c})' if c > 1 else '') for _, _, l, c in items)


def intake(state):
    alert = state['alert_text'][:MAX_ALERT_CHARS]
    out = call_structured(Intake, prompts.INTAKE_SYSTEM, untrusted(alert=alert), tier='fast')
    return {
        'service': out.service,
        'severity': out.severity,
        'symptom': out.symptom,
        'filtered_logs': filter_logs(state['log_snippet']),
        'retries': 0,
    }


def analyze_logs(state):
    user = untrusted(
        alert=state['alert_text'][:MAX_ALERT_CHARS],
        logs=state.get('filtered_logs', '').splitlines(),
    )
    out = call_structured(Findings, prompts.LOGS_SYSTEM, user, tier='fast')
    return {'log_findings': out.findings}


def decide_escalation(hyps):
    return (not hyps) or hyps[0]['cause'] == 'unknown' or hyps[0]['confidence'] < CONF_THRESHOLD


def hypothesize(state):
    retrieval_failed = state.get('retrieval_failed', False)
    user = untrusted(
        alert=state['alert_text'][:MAX_ALERT_CHARS],
        service=state.get('service'),
        log_findings=state.get('log_findings', []),
        runbook_excerpts=[{'runbook': m['runbook'], 'text': m['text']}
                          for m in state.get('runbook_matches', [])],
        runbook_note='No runbook matched. Do not cite a runbook.' if retrieval_failed else '',
        human_feedback=state.get('human_feedback') or '',
    )
    out = call_structured(Hypotheses, prompts.hypothesis_system(CAUSES), user, tier='strong')
    hyps = sorted((h.model_dump() for h in out.hypotheses), key=lambda h: -h['confidence'])[:3]
    for h in hyps:
        h['confidence'] = min(1.0, max(0.0, h['confidence']))
        if h['cause'] not in CAUSES + ['unknown']:
            h['cause'] = 'unknown'
        if retrieval_failed:  # fallback: no runbook support, so lower confidence
            h['runbook'] = None
            h['confidence'] = round(h['confidence'] * 0.8, 3)
    return {'hypotheses': hyps, 'proposed_fix': out.proposed_fix,
            'escalated': decide_escalation(hyps)}
