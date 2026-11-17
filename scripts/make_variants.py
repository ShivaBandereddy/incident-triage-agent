"""Day 7: ask Gemini for wording variants of the signal-line templates (meaning unchanged).

Run in Colab (GOOGLE_API_KEY from Colab Secrets) from the repo root:
    PYTHONPATH=. python scripts/make_variants.py

Writes data/signal_variants.json. Gemini only rewrites the wording of lines I authored; it never
generates incidents or labels. Every variant is checked by code (placeholders, process prefix,
keywords, no label leak) and then reviewed by hand before it is used.
Progress is saved after every fault, so a re-run skips faults that are already done.
"""
import json
import os
import re
import time
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from scripts.generate_incidents import FAULTS

STYLES = ('terse', 'verbose', 'console')
OUT = Path('data/signal_variants.json')
SLEEP = float(os.getenv('VARIANT_SLEEP', '4'))

# Same keyword list the agent's log filter will use (Day 8, app/nodes.py)
KEYWORDS = re.compile(
    r'error|fail|warn|down|expired|latency|timeout|degrad|lost|unreach|space|drift|offset|'
    r'swap|balloon|dead|refused|denied|skew|resolve|servfail|predictive|offline|flap|not responding',
    re.I,
)
PLACEHOLDER = re.compile(r'\{(\w+)\}')

SYSTEM = '''You rewrite synthetic infrastructure log lines for a test dataset.
You get numbered log line templates. For EACH one, write 3 rewrites that keep the same meaning:
- terse: short, syslog-like, fewer words
- verbose: more descriptive wording, same facts
- console: management-console / alert-style wording
Rules:
- Keep the leading "process: " prefix exactly as in the original line.
- Keep every {placeholder} exactly as written (for example {ds}). Do not fill in values. Do not add new placeholders.
- Do not invent new facts: no new numbers, hostnames or device IDs.
- The event must stay the same. Do not change what happened.
- Never mention the root cause or any incident category.
- One line each, at most 160 characters.
Return rewrites for every index.'''


class Rewrite(BaseModel):
    index: int = Field(description='0-based index of the original line')
    terse: str
    verbose: str
    console: str


class Rewrites(BaseModel):
    rewrites: List[Rewrite]


def validate(template, text):
    '''Return None if the variant is acceptable, otherwise the reason it was rejected.'''
    text = text.strip()
    if '\n' in text or not text:
        return 'not a single line'
    if len(text) > 200:
        return 'too long'
    if text == template:
        return 'same as original'
    prefix = template.split(': ', 1)[0]
    if not text.startswith(prefix + ': '):
        return f'prefix "{prefix}:" changed'
    if set(PLACEHOLDER.findall(text)) != set(PLACEHOLDER.findall(template)):
        return 'placeholders differ'
    if re.sub(r'\{\w+\}', '', text).count('{') or re.sub(r'\{\w+\}', '', text).count('}'):
        return 'stray braces'
    try:
        text.format(**{k: 'X' for k in PLACEHOLDER.findall(template)})
    except Exception:
        return 'not formattable'
    if KEYWORDS.search(template) and not KEYWORDS.search(text):
        return 'lost all filter keywords'
    low = text.lower()
    for key, cfg in FAULTS.items():
        if key in low or key.replace('_', '-') in low or cfg['runbook'].lower() in low:
            return 'mentions an incident category'
    if 'root cause' in low:
        return 'mentions root cause'
    return None


def call_gemini(fault, templates, retries=4):
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model=os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite'))
    structured = llm.with_structured_output(Rewrites)
    user = json.dumps({'lines': [{'index': i, 'text': t} for i, t in enumerate(templates)]}, indent=1)
    for attempt in range(retries):
        try:
            out = structured.invoke([('system', SYSTEM), ('human', user)])
            if out is None:
                raise ValueError('empty parse')
            return {r.index: r for r in out.rewrites}
        except Exception as e:
            wait = 5 * 2 ** attempt
            print(f'  LLM error {type(e).__name__}: retrying in {wait}s')
            time.sleep(wait)
    raise RuntimeError(f'Gemini failed for {fault}')


def build_fault(fault, templates, rewrites):
    entries = []
    for i, template in enumerate(templates):
        item = {'index': i, 'template': template, 'variants': [], 'rejected': []}
        rw = rewrites.get(i)
        seen = {template}
        for style in STYLES:
            text = getattr(rw, style).strip() if rw else ''
            reason = validate(template, text) if rw else 'missing from response'
            if reason is None and text in seen:
                reason = 'duplicate'
            if reason is None:
                seen.add(text)
                item['variants'].append({'style': style, 'text': text})
            else:
                item['rejected'].append({'style': style, 'text': text, 'reason': reason})
        entries.append(item)
    return entries


def print_review(fault, entries):
    print(f'\n== {fault} ==')
    for e in entries:
        print(f"[{e['index']}] ORIG    : {e['template']}")
        for v in e['variants']:
            print(f"    {v['style']:<8}: {v['text']}")
        for r in e['rejected']:
            print(f"    {r['style']:<8}: REJECTED ({r['reason']}) {r['text']}")


def main():
    results = json.load(open(OUT)) if OUT.exists() else {}
    for fault, cfg in FAULTS.items():
        if fault in results:
            print_review(fault, results[fault])
            continue
        templates = cfg['signals']
        results[fault] = build_fault(fault, templates, call_gemini(fault, templates))
        OUT.write_text(json.dumps(results, indent=2))
        print_review(fault, results[fault])
        time.sleep(SLEEP)
    n_ok = sum(len(e['variants']) for v in results.values() for e in v)
    n_bad = sum(len(e['rejected']) for v in results.values() for e in v)
    print(f'\naccepted by code: {n_ok}, rejected by code: {n_bad} (still needs manual review)')


if __name__ == '__main__':
    main()
