"""Day 7 one-off: hand-edit one incident per fault type (one extra clue line + one reworded line).

Run once from the repo root, BEFORE the test set is frozen:
    python scripts/apply_manual_edits.py

- Does NOT call the generator. It edits data/incidents_dev.json and data/incidents_test.json in place.
- Labels (true_root_cause, correct_runbook, ...) and alert_text are never changed.
- Idempotent: an incident that already has its edits is skipped.
- Writes the files only if every edit succeeded.
"""
import json
from pathlib import Path

DATA = Path('data')

# For each incident: 'add' = (anchor message, new message, seconds after anchor; negative = before)
#                    'replace' = (old message, new message)
# Messages are the log text after "Oct DD HH:MM:SS host ".
EDITS = {
    'inc-002': {  # datastore_latency
        'add': [('vmkernel: Device naa.87fd7312742b performance has deteriorated. I/O latency increased from 8 ms to 271 ms',
                 'vpxd: Alarm Datastore I/O latency on ds-prod-06 changed from Green to Yellow', 10)],
        'replace': [('hostd: Datastore ds-prod-06 read latency 271 ms exceeds threshold',
                     'hostd: Datastore ds-prod-06 average read latency 271 ms over last 5 min, alarm limit 100 ms')],
    },
    'inc-009': {  # storage_path_down
        'add': [('vmkernel: NMP: lost path redundancy to naa.ca29ed8d87cc, 1 active path remaining',
                 'hostd: Multipath alert: device naa.ca29ed8d87cc now has 1 of 2 paths active', 20)],
        'replace': [('vmkernel: qlnativefc: vmhba1: LOOP DOWN detected',
                     'vmkernel: qlnativefc: vmhba1: LOOP DOWN detected, FC port offline')],
    },
    'inc-016': {  # host_failure_ha
        'add': [('fdm: host esx-host-09 is not responding',
                 'fdm: Restarting VMs on remaining hosts after failure of esx-host-09', 20)],
        'replace': [('fdm: host esx-host-09 is not responding',
                     'fdm: host esx-host-09 is not responding, no heartbeat on management network or datastore')],
    },
    'inc-023': {  # nic_link_flap
        'add': [('vmkernel: Link: vmnic3 link state down',
                 'vmkernel: Link: vmnic3 link state up', 45)],
        'replace': [('vmkernel: Net: uplink vmnic3 marked down by beacon probing, failover to remaining uplink',
                     'vmkernel: Net: vmnic3 beacon probe timeout, uplink marked down, traffic failed over to remaining uplink')],
    },
    'inc-031': {  # datastore_full
        'add': [('hostd: Snapshot consolidation failed for app-25: insufficient space on ds-prod-05',
                 'hostd: Cannot extend thin disk of app-25 on ds-prod-05: no space left on device', 8)],
        'replace': [('hostd: Datastore ds-prod-05 free space 1% below 5% threshold',
                     'hostd: Datastore ds-prod-05 nearly full, 1% free (threshold 5%)')],
    },
    'inc-044': {  # dns_failure
        'add': [('resolver: SERVFAIL for vcenter.corp.local from 10.0.0.2',
                 'vpxa: cannot connect to vcenter.corp.local, host name could not be resolved', 60)],
        'replace': [('resolver: failed to resolve vcenter.corp.local: Name or service not known',
                     'resolver: lookup of vcenter.corp.local failed: Name or service not known')],
    },
    'inc-051': {  # ntp_drift
        'add': [('ntpd: time sync lost, offset 4.1 s',
                 'sshd: Kerberos ticket rejected for admin: KRB_AP_ERR_SKEW', 20)],
        'replace': [('ntpd: time sync lost, offset 4.1 s',
                     'ntpd: lost synchronization with upstream servers, offset 4.1 s')],
    },
    'inc-038': {  # memory_pressure
        'add': [('vmkernel: Swap: VM app-29 swapped 8188 MB to disk',
                 'vmkernel: MemSched: free memory 312 MB, host memory state is low', -120)],
        'replace': [('vmkernel: Swap: VM app-29 swapped 8188 MB to disk',
                     'vmkernel: Swap: VM app-29 has 8188 MB paged out to host swap file')],
    },
    'inc-058': {  # cert_expiry
        'add': [('vpxa: Authentication failed: certificate verify failed (certificate has expired)',
                 'rhttpproxy: SSL certificate for esx-host-04 not valid after 2026-10-21 00:00:00 UTC', 30)],
        'replace': [('vpxd: TLS handshake failed: certificate has expired',
                     'vpxd: TLS handshake with esx-host-04 failed: peer certificate has expired')],
    },
    'inc-066': {  # raid_degraded
        'add': [('kernel: megaraid_sas: Physical drive removed, enclosure 252 slot 2',
                 'storcli: VD0 is no longer Optimal: state Degraded, 1 of 2 drives online', 30)],
        'replace': [('storcli: Rebuild started on VD0 slot 2',
                     'storcli: Rebuild in progress on VD0, target drive slot 2')],
    },
}


def msg_of(line):
    return line.split(' ', 4)[4]


def ts_of(line):
    parts = line.split(' ', 4)
    h, m, s = (int(x) for x in parts[2].split(':'))
    return int(parts[1]) * 86400 + h * 3600 + m * 60 + s


def make_line(ref_line, new_ts, msg):
    parts = ref_line.split(' ', 4)
    day, rem = divmod(new_ts, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    return f'{parts[0]} {day} {h:02d}:{m:02d}:{s:02d} {parts[3]} {msg}'


def find_one(lines, msg):
    idx = [i for i, l in enumerate(lines) if msg_of(l) == msg]
    if len(idx) != 1:
        raise ValueError(f'expected exactly 1 line, found {len(idx)} for: {msg}')
    return idx[0]


def apply_edit(inc, edit):
    """Return True if edited, False if already applied. Raises on any problem."""
    lines = inc['log_snippet'].split('\n')
    msgs = {msg_of(l) for l in lines}
    done = all(n in msgs for _, n in edit['replace']) and all(m in msgs for _, m, _ in edit['add'])
    if done:
        return False
    for anchor, msg, delta in edit['add']:  # adds first, anchors are original lines
        i = find_one(lines, anchor)
        new_ts = ts_of(lines[i]) + delta
        pos = 0
        for j, l in enumerate(lines):
            if ts_of(l) <= new_ts:
                pos = j + 1
        lines.insert(pos, make_line(lines[i], new_ts, msg))
    for old, new in edit['replace']:
        i = find_one(lines, old)
        lines[i] = ' '.join(lines[i].split(' ', 4)[:4]) + ' ' + new
    stamps = [ts_of(l) for l in lines]
    if stamps != sorted(stamps):
        raise ValueError('timestamps out of order after edit')
    inc['log_snippet'] = '\n'.join(lines)
    return True


def main():
    files = {s: json.load(open(DATA / f'incidents_{s}.json')) for s in ('dev', 'test')}
    found, edited, skipped = set(), 0, 0
    for split, items in files.items():
        for inc in items:
            if inc['id'] in EDITS:
                found.add(inc['id'])
                if apply_edit(inc, EDITS[inc['id']]):
                    edited += 1
                    print(f"{inc['id']} ({split}, {inc['true_root_cause']}): edited")
                else:
                    skipped += 1
                    print(f"{inc['id']} ({split}, {inc['true_root_cause']}): already applied")
    missing = set(EDITS) - found
    if missing:
        raise SystemExit(f'ids not found in data files: {sorted(missing)}')
    if edited:
        for split, items in files.items():
            (DATA / f'incidents_{split}.json').write_text(json.dumps(items, indent=2))
    print(f'done: edited {edited}, already applied {skipped}')


if __name__ == '__main__':
    main()
