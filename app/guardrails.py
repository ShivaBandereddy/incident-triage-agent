# app/guardrails.py (v1: untrusted-data wrapper. Regex checks are added on Day 17)
import json


def untrusted(**fields):
    """Serialize untrusted fields (alert, logs, runbook text, feedback) as JSON data.

    < and > are escaped, so a closing tag like </logs> can never appear literally.
    """
    text = json.dumps(fields, ensure_ascii=True, indent=1)
    return text.replace('<', '\\u003c').replace('>', '\\u003e')
