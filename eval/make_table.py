# eval/make_table.py  -- usage: python eval/make_table.py dev   (or: dev_small)
import json
import sys

r = json.load(open(f'eval/results/{sys.argv[1]}_results.json'))
cols = ['top1', 'top3', 'runbook_top1', 'top1_hard_misleading', 'top1_injection',
        'injection_followed', 'abstain_on_unknown', 'false_abstain_on_known']


def fmt(v):
    return '-' if v is None else '{:.0%} ({}/{})'.format(v['pct'], v['k'], v['n'])


print('| System | ' + ' | '.join(cols + ['errors', 'ece', 'brier', 'avg_in_tokens', 'avg_sec']) + ' |')
print('|' + '---|' * (len(cols) + 6))
for name, s in r.items():
    cal = s.get('calibration') or {}
    row = [fmt(s[c]) for c in cols] + [str(s.get('errors', '-')), str(cal.get('ece', '-')),
                                       str(cal.get('brier', '-')),
                                       str(s['avg_input_tokens']), str(s['avg_seconds'])]
    print(f'| {name} | ' + ' | '.join(row) + ' |')
print('\nCalibration is exploratory (small n). Token/second columns are 0 for cached calls.')
