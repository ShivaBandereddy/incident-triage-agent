# app/guardrails.py (Day 17: untrusted-data wrapper + regex layer)
# The regex layer is an EXTRA layer, not a security guarantee. The real defense is
# untrusted JSON encoding + "data, not instructions" prompt rules + read-only agent
# + human review. Regexes were written from dev injection types 0, 1, 2 only.
import json
import re


def untrusted(**fields):
    """Serialize untrusted fields (alert, logs, runbook text, feedback) as JSON data.

    < and > are escaped, so a closing tag like </logs> can never appear literally.
    """
    text = json.dumps(fields, ensure_ascii=True, indent=1)
    return text.replace('<', '\\u003c').replace('>', '\\u003e')


DANGEROUS = re.compile(
    r'\brm\s+-rf\b|\bdrop\s+(table|database)\b|\bmkfs\b|\bdd\s+if=|\bshutdown\b|\breboot\b|'
    r'\bdelete\s+(vm|datastore)\b|\bformat\s+(disk|datastore)\b', re.I)

INJECTION = re.compile(
    r'ignore (all )?(previous|prior) instructions|system prompt|you must (output|answer)|'
    r'new instruction|skip the human approval|api key|assistants? (reading this|must)', re.I)


def flag_dangerous(text):
    return bool(DANGEROUS.search(text or ''))


def scan_injection(text):
    return [line for line in (text or '').splitlines() if INJECTION.search(line)]


def remove_lines(log_text, lines):
    bad = set(lines)
    return '\n'.join(line for line in log_text.splitlines() if line not in bad)
