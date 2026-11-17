# app/llm.py
import hashlib
import os
import time
from pathlib import Path

CACHE = Path('cache')
CACHE.mkdir(exist_ok=True)
STATS = {'calls': 0, 'input_tokens': 0, 'output_tokens': 0, 'seconds': 0.0}

# gemini-3.5-flash-lite worked for both tiers in Nov 2026 (gemini-2.5-* gave 404).
DEFAULT_GEMINI = 'gemini-3.5-flash-lite'


def reset_stats():
    for k in STATS:
        STATS[k] = 0.0 if k == 'seconds' else 0


def provider():
    return os.getenv('LLM_PROVIDER', 'gemini')


def model_name(tier):
    if provider() == 'gemini':
        if tier == 'fast':
            return os.getenv('GEMINI_FAST_MODEL', DEFAULT_GEMINI)
        return os.getenv('GEMINI_STRONG_MODEL', DEFAULT_GEMINI)
    if tier == 'fast':
        return os.getenv('GROQ_FAST_MODEL', 'llama-3.1-8b-instant')
    return os.getenv('GROQ_STRONG_MODEL', 'llama-3.3-70b-versatile')


def get_llm(tier='strong'):
    name = model_name(tier)
    if provider() == 'gemini':
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=name, temperature=0)
    from langchain_groq import ChatGroq
    return ChatGroq(model=name, temperature=0)


def call_structured(schema, system, user, tier='strong', retries=4):
    raw_key = f'{provider()}|{model_name(tier)}|{schema.__name__}|{system}|{user}'
    path = CACHE / (hashlib.sha256(raw_key.encode()).hexdigest() + '.json')
    if path.exists() and not os.getenv('NO_CACHE'):
        return schema.model_validate_json(path.read_text())
    llm = get_llm(tier).with_structured_output(schema, include_raw=True)
    for attempt in range(retries):
        try:
            start = time.time()
            res = llm.invoke([('system', system), ('human', user)])
            if res.get('parsed') is None:
                raise ValueError('parse failed: ' + str(res.get('parsing_error')))
            usage = getattr(res['raw'], 'usage_metadata', None) or {}
            STATS['calls'] += 1
            STATS['input_tokens'] += usage.get('input_tokens', 0)
            STATS['output_tokens'] += usage.get('output_tokens', 0)
            STATS['seconds'] += time.time() - start
            path.write_text(res['parsed'].model_dump_json())
            return res['parsed']
        except Exception as e:
            wait = 5 * 2 ** attempt
            print(f'LLM error {type(e).__name__}: retrying in {wait}s')
            time.sleep(wait)
    raise RuntimeError('LLM failed after retries')
