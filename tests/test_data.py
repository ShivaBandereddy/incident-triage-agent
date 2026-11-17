"""Dataset sanity tests. No LLM calls, no API keys needed (safe for CI)."""
import json
from pathlib import Path

import pytest


def load(split):
    return json.load(open(f'data/incidents_{split}.json'))


def test_sizes():
    assert len(load('dev')) == 40
    assert len(load('test')) == 60


def test_unique_ids():
    ids = [i['id'] for s in ('dev', 'test') for i in load(s)]
    assert len(ids) == len(set(ids)) == 100


def test_split_labels():
    for s in ('dev', 'test'):
        assert all(i['split'] == s for i in load(s))


def test_test_mix():
    t = load('test')
    assert sum(i['true_root_cause'] == 'unknown' for i in t) == 12
    assert sum(i['has_injection'] for i in t) == 12
    assert {i['injection_type'] for i in t if i['has_injection']} == {0, 1, 2, 3, 4, 5}
    regular = [i for i in t if i['true_root_cause'] != 'unknown' and not i['has_injection']]
    assert len(regular) == 36


def test_dev_mix():
    d = load('dev')
    assert sum(i['true_root_cause'] == 'unknown' for i in d) == 3
    assert {i['injection_type'] for i in d if i['has_injection']} == {0, 1, 2}


def test_runbooks_exist():
    assert len(list(Path('data/runbooks').glob('*.md'))) == 10
    for s in ('dev', 'test'):
        for i in load(s):
            if i['correct_runbook']:
                assert Path('data/runbooks', i['correct_runbook']).exists()


def test_required_fields():
    keys = {'id', 'alert_text', 'log_snippet', 'true_root_cause', 'correct_runbook',
            'difficulty', 'has_injection', 'injection_type', 'injection_target', 'split'}
    for s in ('dev', 'test'):
        for i in load(s):
            assert keys <= set(i)
            assert i['alert_text'] and i['log_snippet']


def test_redteam_if_present():
    if not Path('data/incidents_redteam.json').exists():
        pytest.skip('no red-team set')
    rt = load('redteam')
    assert 20 <= len(rt) <= 25 and all(i['has_injection'] for i in rt)
    assert not {i['id'] for i in rt} & {i['id'] for s in ('dev', 'test') for i in load(s)}
