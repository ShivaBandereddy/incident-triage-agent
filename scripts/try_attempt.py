# scripts/try_attempt.py (Day 17 manual red-team helper, DEV incidents only)
# usage: PYTHONPATH=. python scripts/try_attempt.py dev 3 log 'your attempt text'   (where = log or alert)
import json
import sys

from app.graph import build_graph

split, idx, where, text = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
if split != 'dev':
    sys.exit('manual red-team runs on dev only')
inc = json.load(open(f'data/incidents_{split}.json'))[idx]
alert, logs = inc['alert_text'], inc['log_snippet']
if where == 'alert':
    alert += ' ' + text
else:
    logs += '\n' + text
out = build_graph(use_approval=False).invoke({'alert_text': alert, 'log_snippet': logs})
top = out['hypotheses'][0] if out.get('hypotheses') else None
print('expected:', inc['true_root_cause'])
print('got:', top and top['cause'], top and round(top['confidence'], 2))
print('flags:', out.get('security_flags'))
print('fix:', out.get('proposed_fix'))
