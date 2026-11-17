# scripts/run_cli.py  -- usage: PYTHONPATH=. python scripts/run_cli.py dev 0
import json
import sys

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.graph import build_graph

split, idx = sys.argv[1], int(sys.argv[2])
inc = json.load(open(f'data/incidents_{split}.json'))[idx]
graph = build_graph(checkpointer=MemorySaver())
cfg = {'configurable': {'thread_id': inc['id']}}
out = graph.invoke({'alert_text': inc['alert_text'], 'log_snippet': inc['log_snippet']}, cfg)
while '__interrupt__' in out:
    print(json.dumps(out['__interrupt__'][0].value, indent=2))
    ans = input('Approve? (y, or type feedback to reject): ')
    decision = {'approved': True} if ans.strip().lower() in ('y', 'yes') else {'approved': False, 'feedback': ans}
    out = graph.invoke(Command(resume=decision), cfg)
print(out['report'])
