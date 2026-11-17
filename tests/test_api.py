"""API tests. No LLM calls: all requests here are rejected before the graph runs."""
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)
BODY = {'alert_text': 'ALERT: test', 'log_snippet': 'line'}


def test_requires_key(monkeypatch):
    monkeypatch.setenv('TRIAGE_API_KEY', 'secret')
    assert client.post('/triage', json=BODY).status_code == 401
    assert client.post('/triage', json=BODY, headers={'X-API-Key': 'wrong'}).status_code == 401


def test_denies_all_when_key_unset(monkeypatch):
    monkeypatch.delenv('TRIAGE_API_KEY', raising=False)
    assert client.post('/triage', json=BODY, headers={'X-API-Key': ''}).status_code == 401


def test_size_limit(monkeypatch):
    monkeypatch.setenv('TRIAGE_API_KEY', 'secret')
    big = {'alert_text': 'x' * 3000, 'log_snippet': 'line'}
    assert client.post('/triage', json=big, headers={'X-API-Key': 'secret'}).status_code == 422


def test_approve_unknown_thread(monkeypatch):
    monkeypatch.setenv('TRIAGE_API_KEY', 'secret')
    r = client.post('/approve', json={'thread_id': 'nope', 'approved': True},
                    headers={'X-API-Key': 'secret'})
    assert r.status_code == 404
