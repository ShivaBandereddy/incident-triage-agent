# scripts/run_cli.py  (Day 18: --split/--idx options, --save report)
# Usage:
#   PYTHONPATH=. python scripts/run_cli.py --split dev --idx 0
#   PYTHONPATH=. python scripts/run_cli.py --split dev --idx 0 --save report.md
# Old style still works: PYTHONPATH=. python scripts/run_cli.py dev 0
import argparse
import json
import sys
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.graph import build_graph


def parse_args(argv=None):
    p = argparse.ArgumentParser(description='Run the incident triage agent on one incident.')
    p.add_argument('pos', nargs='*', help='old style: SPLIT IDX')
    p.add_argument('--split', choices=['dev', 'test', 'redteam'], help='which incident file (default dev)')
    p.add_argument('--idx', type=int, help='incident index in that file (default 0)')
    p.add_argument('--save', metavar='PATH', help='save the final report (markdown) to this file')
    a = p.parse_args(argv)
    split = a.split or (a.pos[0] if a.pos else 'dev')
    if a.idx is not None:
        idx = a.idx
    else:
        idx = int(a.pos[1]) if len(a.pos) > 1 else 0
    return split, idx, a.save


def main(argv=None):
    split, idx, save = parse_args(argv)
    incs = json.load(open(f'data/incidents_{split}.json'))
    if not 0 <= idx < len(incs):
        sys.exit(f'idx {idx} out of range: {split} has {len(incs)} incidents (0 to {len(incs) - 1})')
    if split == 'test':
        print('Note: the test set is frozen. Use dev for demos and experiments.', file=sys.stderr)
    inc = incs[idx]
    print(f"Incident {inc['id']} | {inc['alert_text']}\n")

    graph = build_graph(checkpointer=MemorySaver())
    cfg = {'configurable': {'thread_id': inc['id']}}
    out = graph.invoke({'alert_text': inc['alert_text'], 'log_snippet': inc['log_snippet']}, cfg)
    while '__interrupt__' in out:
        print(json.dumps(out['__interrupt__'][0].value, indent=2))
        ans = input('Approve? (y, or type feedback to reject): ')
        decision = ({'approved': True} if ans.strip().lower() in ('y', 'yes')
                    else {'approved': False, 'feedback': ans})
        out = graph.invoke(Command(resume=decision), cfg)
    print(out['report'])
    if save:
        Path(save).write_text(out['report'])
        print(f'\nReport saved to {save}')


if __name__ == '__main__':
    main()
