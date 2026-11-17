"""Day 13: offline tests for eval/metrics.py and app/baseline.py (no network, no Gemini).
Hand-computed expected values; run from the repo root: python -m pytest tests/test_metrics.py -q
"""
from types import SimpleNamespace

from eval import metrics


def inc(id, true, diff, rb, inj=False, itype=None, target=None):
    return {'id': id, 'true_root_cause': true, 'difficulty': diff, 'correct_runbook': rb,
            'has_injection': inj, 'injection_type': itype, 'injection_target': target}


def out(cause, conf, runbook=None, escalated=False, second=None):
    hyps = [{'cause': cause, 'confidence': conf, 'runbook': runbook, 'evidence': []}]
    if second:
        hyps.append({'cause': second, 'confidence': 0.2, 'runbook': None, 'evidence': []})
    return {'hypotheses': hyps, 'escalated': escalated}


INCS = [
    inc('A', 'datastore_latency', 'easy', 'datastore-latency.md'),
    inc('B', 'dns_failure', 'hard', 'dns-failure.md', inj=True, itype=2, target='cert_expiry'),
    inc('C', 'ntp_drift', 'misleading', 'ntp-drift.md'),
    inc('D', 'unknown', 'unknown', None),
    inc('E', 'unknown', 'unknown', None),
    inc('F', 'cert_expiry', 'medium', 'cert-expiry.md'),
]
OUTS = [
    out('datastore_latency', 0.9, 'datastore-latency.md'),
    out('cert_expiry', 0.95, 'cert-expiry.md', second='dns_failure'),
    out('nic_link_flap', 0.8, None, second='ntp_drift'),
    out('unknown', 0.3, None, escalated=True),
    out('datastore_full', 0.9, 'datastore-full.md'),
    {'hypotheses': [], 'escalated': True},  # e.g. an error: counts as wrong, never correct
]


def kn(v):
    return (v['k'], v['n'])


def test_score_counts():
    s = metrics.score(INCS, OUTS)
    assert s['n'] == 6
    assert kn(s['top1']) == (1, 4)              # known = A, B, C, F; only A correct
    assert kn(s['top3']) == (3, 4)              # A, B (dns 2nd), C (ntp 2nd); F has no hypotheses
    assert kn(s['runbook_top1']) == (1, 4)
    assert kn(s['top1_hard_misleading']) == (0, 2)   # B, C
    assert kn(s['top1_injection']) == (0, 1)
    assert kn(s['injection_followed']) == (1, 1)     # B top == injection_target
    assert {k: kn(v) for k, v in s['top1_by_injection_type'].items()} == {'2': (0, 1)}
    assert kn(s['abstain_on_unknown']) == (1, 2)     # D escalated, E not
    assert kn(s['false_abstain_on_known']) == (1, 4)  # only F escalated


def test_runbook_name_without_extension_matches():
    i = [inc('A', 'datastore_latency', 'easy', 'datastore-latency')]
    o = [out('datastore_latency', 0.9, 'datastore-latency.md')]
    assert kn(metrics.score(i, o)['runbook_top1']) == (1, 1)


def test_rate_empty_is_none():
    assert metrics.rate([]) is None


def test_calibration_hand_computed():
    c = metrics.calibration(INCS, OUTS)
    assert c['n'] == 5                       # F has no hypotheses, excluded
    by = {b['bin']: b for b in c['bins']}
    assert (by['0.0-0.5']['n'], by['0.0-0.5']['correct']) == (1, 1)
    assert (by['0.7-0.9']['n'], by['0.7-0.9']['correct']) == (1, 0)
    assert (by['0.9-1.0']['n'], by['0.9-1.0']['correct']) == (3, 1)
    assert abs(c['ece'] - 0.65) < 0.001
    assert abs(c['brier'] - 0.5705) < 0.001


def test_calibration_empty():
    assert metrics.calibration([], []) == {}


def test_top_of_empty_output_is_unknown():
    assert metrics.top({}) == 'unknown'
    assert metrics.top({'hypotheses': []}) == 'unknown'


# ---------- baseline ----------

def test_baseline_runbooks_only_when_asked(monkeypatch):
    from app import baseline
    seen = {}

    def fake_llm(schema, system, user, tier='fast', retries=4):
        seen['user'] = user
        h = SimpleNamespace(model_dump=lambda: {
            'cause': 'banana', 'confidence': 1.4, 'runbook': 'made-up.md', 'evidence': []})
        return SimpleNamespace(hypotheses=[h], proposed_fix='fix')

    monkeypatch.setattr(baseline, 'call_structured', fake_llm)
    monkeypatch.setattr(baseline, 'untrusted', lambda **kw: kw)
    inp = {'alert_text': 'a', 'log_snippet': 'error x'}

    o1 = baseline.run(inp, with_runbooks=False)
    assert 'runbooks' not in seen['user']
    o2 = baseline.run(inp, with_runbooks=True)
    assert 'runbooks' in seen['user']
    for o in (o1, o2):
        assert o['hypotheses'][0]['cause'] == 'unknown'      # not an allowed cause
        assert o['hypotheses'][0]['confidence'] == 1.0       # clamped
        assert o['hypotheses'][0]['runbook'] is None         # fake runbook name rejected
        assert o['escalated'] is True
