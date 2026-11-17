"""Day 12: end-to-end check of the full graph (RAG + approval + report) with real Gemini calls.

Run from the repo root:
    PYTHONPATH=. python scripts/check_report.py          # dev[0..2]
    PYTHONPATH=. python scripts/check_report.py 5        # dev[0..4]

Cases:
  A. approve path on dev[0..N-1]          -> report built, status 'approved by a human' (or ESCALATED if low confidence)
  B. reject twice on dev[0]               -> MAX_RETRIES reached, report status ESCALATED
  C. dev[0] with empty log_snippet        -> no crash, report built
  D. dev[0] with a 6000-char alert        -> no crash, report built
Exploratory: this checks that the pipeline runs, not accuracy.
"""
import json
import sys
import traceback

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.graph import build_graph


def run_once(incident, decisions, thread_id):
    """Run the approval graph; answer each pause with the next decision. Returns (final_state, n_pauses)."""
    graph = build_graph(use_rag=True, use_approval=True, checkpointer=MemorySaver())
    cfg = {'configurable': {'thread_id': thread_id}}
    result = graph.invoke(
        {'alert_text': incident['alert_text'], 'log_snippet': incident['log_snippet']}, cfg)
    pauses = 0
    while '__interrupt__' in result:
        if pauses >= len(decisions):
            raise RuntimeError('graph paused more times than expected')
        result = graph.invoke(Command(resume=decisions[pauses]), cfg)
        pauses += 1
    return result, pauses


def status_line(report_text):
    for line in report_text.splitlines():
        if line.startswith('**Status:**'):
            return line
    return '(no status line)'


def check(name, incident, decisions, expect_escalated=None):
    print(f'\n=== {name} ({incident["id"]}) ===')
    try:
        state, pauses = run_once(incident, decisions, thread_id=name)
        text = state.get('report', '')
        assert text.startswith('# Incident report'), 'report is not the real report (stub?)'
        assert '## Postmortem draft' in text, 'report is incomplete'
        if expect_escalated is not None:
            assert state['escalated'] is expect_escalated, (
                f"escalated={state['escalated']}, expected {expect_escalated}")
        top = (state.get('hypotheses') or [{}])[0]
        print(f"PASS | pauses={pauses} retries={state.get('retries')} "
              f"top={top.get('cause')} {top.get('confidence')} | {status_line(text)}")
        return state
    except Exception:
        print('FAIL')
        traceback.print_exc()
        return None


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    dev = json.load(open('data/incidents_dev.json'))
    if isinstance(dev, dict):  # tolerate {'incidents': [...]}
        dev = next(v for v in dev.values() if isinstance(v, list))

    first = None
    for i in range(n):
        s = check(f'A_approve_dev{i}', dev[i], [{'approved': True}])
        if i == 0:
            first = s
    check('B_reject_twice_dev0', dev[0],
          [{'approved': False, 'feedback': 'try memory pressure'},
           {'approved': False, 'feedback': 'still not sure, check again'}],
          expect_escalated=True)
    check('C_empty_logs', dict(dev[0], log_snippet=''), [{'approved': True}])
    check('D_long_alert', dict(dev[0], alert_text=dev[0]['alert_text'] + ' pad' * 1500),
          [{'approved': True}])

    if first:
        print('\n----- full report for A_approve_dev0 -----')
        print(first['report'])


if __name__ == '__main__':
    main()
