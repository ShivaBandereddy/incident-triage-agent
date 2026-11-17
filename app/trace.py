# app/trace.py (Day 18): simple JSON-lines tracing. File is git-ignored.
import functools
import json
import os
import time


def traced(fn):
    @functools.wraps(fn)
    def wrapper(state):
        start = time.time()
        out = fn(state)
        os.makedirs('eval/results', exist_ok=True)
        with open('eval/results/traces.jsonl', 'a') as f:
            f.write(json.dumps({'node': fn.__name__, 'seconds': round(time.time() - start, 2),
                                'updated_keys': list(out.keys())}) + '\n')
        return out
    return wrapper
