"""Freeze check for the test set (frozen 2026-11-17).

If this test fails, data/incidents_test.json was changed. Do not just update the hash.
Re-running scripts/generate_incidents.py overwrites the test set and will trigger this failure.
A legitimate change must be recorded in docs/FINDINGS.md (what changed and why).
"""
import hashlib
from pathlib import Path

FROZEN_SHA256 = 'de8e51a209754aaee9408c422673d48880884a14346034cd568cf1097bcbf3a5'


def test_test_set_is_frozen():
    digest = hashlib.sha256(Path('data/incidents_test.json').read_bytes()).hexdigest()
    assert digest == FROZEN_SHA256, (
        'data/incidents_test.json changed after the freeze. '
        'Restore it from git (git checkout data/incidents_test.json).'
    )
