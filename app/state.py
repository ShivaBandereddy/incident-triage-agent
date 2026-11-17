# app/state.py
from typing import List, TypedDict


class IncidentState(TypedDict, total=False):
    alert_text: str
    log_snippet: str
    service: str
    severity: str
    symptom: str
    filtered_logs: str
    security_flags: List[str]
    log_findings: List[str]
    runbook_matches: List[dict]
    retrieval_failed: bool
    hypotheses: List[dict]
    proposed_fix: str
    approved: bool
    human_feedback: str
    retries: int
    escalated: bool
    report: str
