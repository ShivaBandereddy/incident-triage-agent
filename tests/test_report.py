"""Day 12: offline tests for the report node and edge cases.
No network, no Gemini calls. Run from the repo root: python -m pytest tests/test_report.py -q
"""
from types import SimpleNamespace

from app import nodes


class FakeHyp:
    def __init__(self, **kw):
        self._kw = kw

    def model_dump(self):
        return dict(self._kw)


def _hyp(cause, conf, runbook=None, evidence=None):
    return FakeHyp(cause=cause, confidence=conf, evidence=evidence or ['e1'], runbook=runbook)


def _fake_llm(hyps, fix='fix it'):
    def fake(schema, system, user, tier='fast', retries=4):
        return SimpleNamespace(hypotheses=hyps, proposed_fix=fix)
    return fake


# ---------- report node ----------

FULL = {
    'alert_text': 'DB latency high',
    'service': 'orders-db',
    'severity': 'high',
    'hypotheses': [
        {'cause': 'datastore_latency', 'confidence': 0.9,
         'runbook': 'datastore-latency.md', 'evidence': ['read latency 300ms', 'queue depth up']},
        {'cause': 'memory_pressure', 'confidence': 0.4, 'runbook': None, 'evidence': []},
    ],
    'proposed_fix': 'Check datastore load (suggestion only).',
    'log_findings': ['latency warnings on ds-prod-05'],
    'approved': True,
    'escalated': False,
}


def test_report_approved():
    out = nodes.report(dict(FULL))
    text = out['report']
    assert out['escalated'] is False
    assert text.startswith('# Incident report')
    assert 'reviewed and approved by a human' in text
    assert '1. **datastore_latency** (confidence 0.90, runbook: datastore-latency.md)' in text
    assert '2. **memory_pressure** (confidence 0.40, runbook: none)' in text
    assert '   - evidence: read latency 300ms' in text
    assert '## Recommended steps (for human review, never auto-run)' in text
    assert '- latency warnings on ds-prod-05' in text
    assert '## Postmortem draft' in text
    assert '## Security flags' not in text


def test_report_not_approved_is_escalated():
    state = dict(FULL, approved=False)
    out = nodes.report(state)
    assert out['escalated'] is True
    assert 'ESCALATED: needs human investigation' in out['report']
    assert 'approved by a human' not in out['report']


def test_report_low_confidence_approved_is_still_escalated():
    state = dict(FULL, escalated=True)
    out = nodes.report(state)
    assert out['escalated'] is True
    assert 'ESCALATED' in out['report']


def test_report_minimal_state_does_not_crash():
    out = nodes.report({'alert_text': 'x'})
    assert out['escalated'] is True
    assert '_No hypotheses produced._' in out['report']
    assert '- (none)' in out['report']


def test_report_retrieval_failed_note():
    out = nodes.report(dict(FULL, retrieval_failed=True))
    assert '_No runbook matched above the distance threshold; confidence reduced._' in out['report']


def test_report_security_flags():
    out = nodes.report(dict(FULL, security_flags=['instruction-like text in alert']))
    assert '## Security flags' in out['report']
    assert '- instruction-like text in alert' in out['report']


# ---------- edge cases ----------

def test_filter_logs_empty():
    assert nodes.filter_logs('') == ''


def test_hypothesize_zero_hypotheses(monkeypatch):
    monkeypatch.setattr(nodes, 'call_structured', _fake_llm([], fix=''))
    out = nodes.hypothesize({'alert_text': 'a', 'log_findings': []})
    assert out['hypotheses'] == []
    assert out['escalated'] is True


def test_hypothesize_cause_not_allowed_becomes_unknown(monkeypatch):
    monkeypatch.setattr(nodes, 'call_structured', _fake_llm([_hyp('banana_split', 0.9)]))
    out = nodes.hypothesize({'alert_text': 'a'})
    assert out['hypotheses'][0]['cause'] == 'unknown'
    assert out['escalated'] is True


def test_hypothesize_clamps_confidence_and_checks_runbook(monkeypatch):
    matches = [{'runbook': 'datastore-latency.md', 'text': 't'}]
    hyps = [_hyp('datastore_latency', 1.7, runbook='datastore-latency.md'),
            _hyp('datastore_full', -0.3, runbook='made-up.md')]
    monkeypatch.setattr(nodes, 'call_structured', _fake_llm(hyps))
    out = nodes.hypothesize({'alert_text': 'a', 'runbook_matches': matches})
    assert out['hypotheses'][0]['confidence'] == 1.0
    assert out['hypotheses'][0]['runbook'] == 'datastore-latency.md'
    assert out['hypotheses'][1]['confidence'] == 0.0
    assert out['hypotheses'][1]['runbook'] is None


def test_hypothesize_retrieval_failed_lowers_confidence(monkeypatch):
    monkeypatch.setattr(nodes, 'call_structured',
                        _fake_llm([_hyp('datastore_latency', 0.8, runbook='datastore-latency.md')]))
    out = nodes.hypothesize({'alert_text': 'a', 'retrieval_failed': True})
    assert out['hypotheses'][0]['runbook'] is None
    assert out['hypotheses'][0]['confidence'] == 0.64


def test_search_runbooks_index_missing(monkeypatch):
    def boom(query, k=3, **kw):
        raise RuntimeError('index missing')
    monkeypatch.setattr(nodes.rag, 'search', boom)
    out = nodes.search_runbooks({'alert_text': 'a', 'log_findings': []})
    assert out == {'runbook_matches': [], 'retrieval_failed': True}


def test_intake_truncates_long_alert_and_handles_empty_logs(monkeypatch):
    seen = {}

    def fake(schema, system, user, tier='fast', retries=4):
        seen['user'] = user
        return SimpleNamespace(service='svc', severity='high', symptom='s')

    monkeypatch.setattr(nodes, 'call_structured', fake)
    monkeypatch.setattr(nodes, 'untrusted', lambda **kw: kw)
    out = nodes.intake({'alert_text': 'A' * 5000, 'log_snippet': ''})
    assert len(seen['user']['alert']) == nodes.MAX_ALERT_CHARS == 2000
    assert out['filtered_logs'] == ''
    assert out['retries'] == 0
