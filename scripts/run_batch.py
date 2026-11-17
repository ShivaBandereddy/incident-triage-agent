# scripts/run_batch.py  -- usage: PYTHONPATH=. python scripts/run_batch.py dev 5
# USE_RAG=0 runs without RAG (Day 9 baseline); default is RAG on
import json
import os
import sys

from app.graph import build_graph

split, n = sys.argv[1], int(sys.argv[2])
incs = json.load(open(f'data/incidents_{split}.json'))[:n]
use_rag = os.getenv('USE_RAG', '1') != '0'
print('use_rag =', use_rag)
graph = build_graph(use_rag=use_rag, use_approval=False)  # batch runs never pause for a human
correct = errors = 0
for inc in incs:
    try:
        out = graph.invoke({'alert_text': inc['alert_text'], 'log_snippet': inc['log_snippet']})
        hyps = out.get('hypotheses') or []
        top = hyps[0] if hyps else None
        got = top['cause'] if top else None
        ok = got == inc['true_root_cause']
        correct += ok
        print(inc['id'], inc['difficulty'], '| expected:', inc['true_root_cause'],
              '| got:', got, round(top['confidence'], 2) if top else None,
              '| escalated:', out.get('escalated'), '| runbook:', top and top.get('runbook'), '| OK' if ok else '| MISS')
    except Exception as e:
        errors += 1
        print(inc['id'], inc['difficulty'], '| ERROR:', type(e).__name__, str(e)[:200])
print(f'\n{correct} of {len(incs)} correct, {errors} errors')
