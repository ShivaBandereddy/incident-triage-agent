# eval/run_eval.py  (Day 13)
# Usage (repo root):  PYTHONPATH=. python -u eval/run_eval.py dev baseline,agent_rag
# Systems: baseline, baseline_ctx, agent_norag, agent_rag
# Env: EVAL_SLEEP (seconds after each incident, default 3), LIMIT (first N incidents),
#      EVAL_TAG (result file suffix, e.g. _small), ONLY_INJECTION=1, NO_CACHE=1 (real cost/latency)
import json
import os
import sys
import time
from pathlib import Path

from app import baseline, llm
from app.graph import build_graph
from eval.metrics import calibration, score, top

SLEEP = float(os.getenv('EVAL_SLEEP', '3'))
AGENT_RAG = build_graph(use_rag=True, use_approval=False)
AGENT_NORAG = build_graph(use_rag=False, use_approval=False)
Path('eval/results').mkdir(parents=True, exist_ok=True)


def reset_stats():
    fn = getattr(llm, 'reset_stats', None)
    if fn:
        fn()
    else:
        for k in list(llm.STATS):
            llm.STATS[k] = 0


def run_system(name, inc):
    inp = {'alert_text': inc['alert_text'], 'log_snippet': inc['log_snippet']}
    if name == 'baseline':
        return baseline.run(inp, with_runbooks=False)
    if name == 'baseline_ctx':
        return baseline.run(inp, with_runbooks=True)
    if name == 'agent_rag':
        return AGENT_RAG.invoke(inp)
    if name == 'agent_norag':
        return AGENT_NORAG.invoke(inp)
    raise ValueError(f'unknown system: {name}')


def slim(inc, o):
    """Small per-incident record for error analysis (Day 14)."""
    return {
        'id': inc['id'], 'difficulty': inc['difficulty'],
        'expected': inc['true_root_cause'], 'got': top(o),
        'hypotheses': o.get('hypotheses') or [], 'escalated': o.get('escalated'),
        'log_findings': o.get('log_findings'),
        'retrieved': [m['runbook'] for m in (o.get('runbook_matches') or [])],
        'retrieval_failed': o.get('retrieval_failed'),
        'error': o.get('error'),
    }


def main(split, systems):
    incs = json.load(open(f'data/incidents_{split}.json'))
    if os.getenv('ONLY_INJECTION'):
        incs = [i for i in incs if i['has_injection']]
    if os.getenv('LIMIT'):
        incs = incs[:int(os.environ['LIMIT'])]
    tag = os.getenv('EVAL_TAG', '')
    out_path = Path(f'eval/results/{split}{tag}_results.json')
    results = json.load(open(out_path)) if out_path.exists() else {}
    for name in systems:
        reset_stats()
        outs, errors = [], 0
        print(f'\n##### {name} on {split}{tag}: {len(incs)} incidents', flush=True)
        for inc in incs:
            try:
                o = run_system(name, inc)
            except Exception as e:  # count as an error, never as a correct answer
                errors += 1
                o = {'hypotheses': [], 'escalated': True, 'error': f'{type(e).__name__}: {str(e)[:200]}'}
            outs.append(o)
            ok = top(o) == inc['true_root_cause']
            print(inc['id'], inc['difficulty'], '| expected:', inc['true_root_cause'], '| got:', top(o),
                  '| escalated:', o.get('escalated'), '| OK' if ok else '| MISS',
                  ('| ERROR ' + o['error']) if o.get('error') else '', flush=True)
            time.sleep(SLEEP)
        s = score(incs, outs)
        s['errors'] = errors
        s['calibration'] = calibration(incs, outs)
        n = len(incs)
        st = llm.STATS
        s['avg_calls'] = round(st.get('calls', 0) / n, 2)
        s['avg_input_tokens'] = round(st.get('input_tokens', 0) / n)
        s['avg_output_tokens'] = round(st.get('output_tokens', 0) / n)
        s['avg_seconds'] = round(st.get('seconds', 0) / n, 2)
        s['cost_note'] = ('cached calls count as 0; use NO_CACHE=1 for real cost/latency'
                          if not os.getenv('NO_CACHE') else 'NO_CACHE=1 run')
        results[name] = s
        json.dump([slim(i, o) for i, o in zip(incs, outs)],
                  open(f'eval/results/{split}{tag}_{name}_outputs.json', 'w'), indent=2)
        failures = [{'id': i['id'], 'difficulty': i['difficulty'],
                     'expected': i['true_root_cause'], 'got': top(o)}
                    for i, o in zip(incs, outs) if top(o) != i['true_root_cause']]
        json.dump(failures, open(f'eval/results/{split}{tag}_{name}_failures.json', 'w'), indent=2)
        json.dump(results, open(out_path, 'w'), indent=2)  # saved after every system
        print(f'--- {name}: top1 {s["top1"]}, errors {errors}', flush=True)
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2].split(','))
