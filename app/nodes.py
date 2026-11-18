# app/nodes.py (Day 14: KEYWORDS extended, dev-only analysis)
import re
from pathlib import Path

from langgraph.types import interrupt

from app import prompts, rag
from app.guardrails import untrusted
from app.llm import call_structured
from app.schemas import Findings, Hypotheses, Intake

CAUSES = sorted(p.stem.replace('-', '_') for p in Path('data/runbooks').glob('*.md'))
CONF_THRESHOLD = 0.5
MAX_RETRIES = 2
MAX_ALERT_CHARS = 2000
KEYWORDS = re.compile(
    r'error|fail|warn|down|expired|latency|timeout|degrad|lost|unreach|space|drift|offset|'
    r'swap|balloon|dead|refused|denied|skew|resolve|servfail|predictive|offline|flap|not responding|'
    r'powered on by ha|link state|low memory|memsched|alarm|(?:drive|pd) removed|rebuild|timed out',
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


def search_runbooks(state):
    query = state['alert_text'][:MAX_ALERT_CHARS] + '\n' + '\n'.join(state.get('log_findings', []))
    try:
        matches = rag.search(query, k=3)
    except Exception:  # index missing / Chroma error: continue without runbooks
        matches = []
    return {'runbook_matches': matches, 'retrieval_failed': not matches}


def _norm_runbook(value, matches):
    """Keep a cited runbook only if it is one of the retrieved files (by file name)."""
    if not value:
        return None
    name = Path(str(value).strip()).name.lower()
    for m in matches:
        if m['runbook'].lower() in (name, name + '.md'):
            return m['runbook']
    return None

def _norm_cause(raw):
    """Map formatting variants (nic-link-flap, NIC link flap, nic_link_flap.md) to a known cause key.
    Only formatting is normalized; a genuinely different cause still becomes 'unknown'."""
    s = (raw or '').strip().lower()
    if s.endswith('.md'):
        s = s[:-3]
    s = '_'.join(s.replace('-', ' ').replace('_', ' ').split())
    return s if s in CAUSES or s == 'unknown' else 'unknown'
    
def decide_escalation(hyps):
    return (not hyps) or hyps[0]['cause'] == 'unknown' or hyps[0]['confidence'] < CONF_THRESHOLD


def hypothesize(state):
    retrieval_failed = state.get('retrieval_failed', False)
    matches = state.get('runbook_matches', [])
    user = untrusted(
        alert=state['alert_text'][:MAX_ALERT_CHARS],
        service=state.get('service'),
        log_findings=state.get('log_findings', []),
        runbook_excerpts=[{'runbook': m['runbook'], 'text': m['text']}
                          for m in matches],
        runbook_note='No runbook matched. Do not cite a runbook.' if retrieval_failed else '',
        human_feedback=state.get('human_feedback') or '',
    )
    out = call_structured(Hypotheses, prompts.hypothesis_system(CAUSES), user, tier='strong')
    hyps = sorted((h.model_dump() for h in out.hypotheses), key=lambda h: -h['confidence'])[:3]
    for h in hyps:
        h['confidence'] = min(1.0, max(0.0, h['confidence']))
        h['raw_cause'] = h['cause']  # kept for transparency
        h['cause'] = _norm_cause(h['cause'])
        h['runbook'] = _norm_runbook(h.get('runbook'), matches)
        if retrieval_failed:  # fallback: no runbook support, so lower confidence
            h['runbook'] = None
            h['confidence'] = round(h['confidence'] * 0.8, 3)
    return {'hypotheses': hyps, 'proposed_fix': out.proposed_fix,
            'escalated': decide_escalation(hyps)}


def human_approval(state):
    """Pause the graph and wait for a human decision (approve, or reject + feedback)."""
    decision = interrupt({
        'hypotheses': state['hypotheses'],
        'proposed_fix': state['proposed_fix'],
        'escalated': state.get('escalated', False),
    })
    if decision.get('approved'):
        return {'approved': True}
    return {'approved': False,
            'human_feedback': decision.get('feedback', ''),
            'retries': state.get('retries', 0) + 1}


def route_after_approval(state):
    if state.get('approved'):
        return 'report'
    if state.get('retries', 0) >= MAX_RETRIES:
        return 'report'
    return 'hypothesize'


def report(state):
    """Template report, no LLM. Safe on partial state (missing keys, empty lists)."""
    hyps = state.get('hypotheses') or []
    escalated = bool(state.get('escalated')) or not state.get('approved', False)
    status = ('ESCALATED: needs human investigation' if escalated
              else 'Recommended root cause reviewed and approved by a human')
    lines = [
        '# Incident report',
        f"**Alert:** {state.get('alert_text', '-')}",
        f"**Service:** {state.get('service') or '-'} | **Severity:** {state.get('severity') or '-'}",
        f'**Status:** {status}',
        '',
        '## Root cause hypotheses',
    ]
    if state.get('retrieval_failed'):
        lines.append('_No runbook matched above the distance threshold; confidence reduced._')
    if not hyps:
        lines.append('_No hypotheses produced._')
    for i, h in enumerate(hyps, 1):
        lines.append(f"{i}. **{h['cause']}** (confidence {h['confidence']:.2f}, "
                     f"runbook: {h.get('runbook') or 'none'})")
        lines += [f'   - evidence: {e}' for e in h.get('evidence') or []]
    lines += ['', '## Recommended steps (for human review, never auto-run)',
              state.get('proposed_fix') or '-',
              '', '## Key log findings']
    findings = state.get('log_findings') or []
    lines += [f'- {f}' for f in findings] if findings else ['- (none)']
    if state.get('security_flags'):
        lines += ['', '## Security flags'] + [f'- {s}' for s in state['security_flags']]
    lines += ['', '## Postmortem draft', '- Impact: TBD', '- Timeline: TBD', '- Follow-ups: TBD']
    return {'report': '\n'.join(lines), 'escalated': escalated}
