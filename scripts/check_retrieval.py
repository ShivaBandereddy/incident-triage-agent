# scripts/check_retrieval.py -- usage: PYTHONPATH=. python scripts/check_retrieval.py
# Threshold sweep on DEV only. No LLM calls: query = alert + filtered logs (plan version).
import json

from app import rag
from app.nodes import filter_logs

incs = json.load(open('data/incidents_dev.json'))
rag.build_index()
for md in (1.0, 1.2, 1.4, 1.6, 9.9):
    hits = n = unk_nomatch = n_unk = 0
    missed = []
    for inc in incs:
        query = inc['alert_text'] + '\n' + filter_logs(inc['log_snippet'])[:2000]
        got = [m['runbook'] for m in rag.search(query, k=3, max_distance=md)]
        if inc['correct_runbook']:
            n += 1
            if inc['correct_runbook'] in got:
                hits += 1
            else:
                missed.append((inc['id'], inc['correct_runbook'], got))
        else:
            n_unk += 1
            unk_nomatch += (len(got) == 0)
    print(f'max_distance={md}: hit@3 {hits}/{n} | unknown incidents with no match {unk_nomatch}/{n_unk}')
    if md == 1.4:
        for m in missed:
            print('   miss:', m)
