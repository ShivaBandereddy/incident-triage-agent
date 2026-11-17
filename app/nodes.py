# app/nodes.py (Day 8 v1: log filter + intake)
import re
from pathlib import Path

from app import prompts
from app.guardrails import untrusted
from app.llm import call_structured
from app.schemas import Intake

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
