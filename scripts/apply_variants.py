"""Day 7: swap the wording of some signal lines in the existing incidents with approved variants.

Run once from the repo root, BEFORE the test set is frozen:
    PYTHONPATH=. python scripts/apply_variants.py

Needs data/signal_variants.json (written by scripts/make_variants.py).
- Does NOT call the generator or any LLM. Labels and alert_text are never changed.
- About half of the signal lines (and decoy lines, which use the same templates) become variants.
  The choice is deterministic per (incident id, line number), so running it again changes nothing.
- The 10 hand-edited incidents (scripts/apply_manual_edits.py) are skipped.
- Variants rejected by hand are listed in REJECTED_BY_HAND.
- Writes the files only if every check passed.
"""
import json
import random
import re
from pathlib import Path

from scripts.apply_manual_edits import EDITS

DATA = Path('data')
SHARE = 0.5  # fraction of eligible lines that get a variant

REJECTED_BY_HAND = {
    ('host_failure_ha', 0, 'terse'): '"down" is stronger than "not responding"',
    ('nic_link_flap', 3, 'console'): '"deactivated" suggests an admin disabled the NIC',
    ('datastore_full', 1, 'terse'): 'lost the word "usage", could be any alarm',
    ('raid_degraded', 0, 'terse'): '"SMART fail" is not the same as "predictive failure"',
    ('raid_degraded', 1, 'verbose'): '"physically unplugged" implies a person pulled the drive',
}


def template_regex(template):
    '''Regex that matches a formatted line of this template and captures the placeholder values.'''
    seen = set()

    def sub(m):
        name = m.group(1)
        if name in seen:
            return f'(?P={name})'
        seen.add(name)
        return f'(?P<{name}>.+?)'

    return re.compile('^' + re.sub(r'\\\{(\w+)\\\}', sub, re.escape(template)) + '$')


def load_templates():
    raw = json.load(open(DATA / 'signal_variants.json'))
    out = []
    for fault, entries in raw.items():
        for e in entries:
            ok = [v['text'] for v in e['variants'] if (fault, e['index'], v['style']) not in REJECTED_BY_HAND]
            out.append({'fault': fault, 'rx': template_regex(e['template']), 'variants': ok,
                        'variant_rx': [template_regex(v) for v in ok]})
    return out


def process(inc, templates, examples):
    lines = inc['log_snippet'].split('\n')
    changed = 0
    for i, line in enumerate(lines):
        parts = line.split(' ', 4)
        hits = [t for t in templates if t['rx'].match(parts[4])]
        if len(hits) != 1 or not hits[0]['variants']:
            continue
        rng = random.Random(f"variants|{inc['id']}|{i}")
        if rng.random() >= SHARE:
            continue
        t = hits[0]
        new = rng.choice(t['variants']).format(**t['rx'].match(parts[4]).groupdict())
        lines[i] = ' '.join(parts[:4]) + ' ' + new
        changed += 1
        if len(examples) < 4:
            examples.append((parts[4], new))
    inc['log_snippet'] = '\n'.join(lines)
    return changed


def has_signal(inc, templates):
    '''True if at least one line still matches the incident's own fault (original or variant wording).'''
    own = [t for t in templates if t['fault'] == inc['true_root_cause']]
    for line in inc['log_snippet'].split('\n'):
        msg = line.split(' ', 4)[4]
        if any(t['rx'].match(msg) or any(v.match(msg) for v in t['variant_rx']) for t in own):
            return True
    return False


def main():
    templates = load_templates()
    files = {s: json.load(open(DATA / f'incidents_{s}.json')) for s in ('dev', 'test')}
    examples, problems = [], []
    for split, items in files.items():
        n_inc = n_lines = 0
        for inc in items:
            if inc['id'] in EDITS:
                continue
            c = process(inc, templates, examples)
            n_inc += bool(c)
            n_lines += c
            if inc['true_root_cause'] != 'unknown' and not has_signal(inc, templates):
                problems.append(inc['id'])
        print(f'{split}: {n_lines} lines replaced in {n_inc} incidents')
    for old, new in examples:
        print('  before:', old)
        print('  after :', new)
    if problems:
        raise SystemExit(f'incidents with no recognisable signal line left: {problems}. Nothing written.')
    for split, items in files.items():
        (DATA / f'incidents_{split}.json').write_text(json.dumps(items, indent=2))
    print('done. Hand-edited incidents skipped:', len(EDITS))


if __name__ == '__main__':
    main()
