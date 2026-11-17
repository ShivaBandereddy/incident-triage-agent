import json
import re
import sys

sys.path.insert(0, ".")
from scripts.generate_incidents import NOISE

split, idx = sys.argv[1], int(sys.argv[2])
mode = sys.argv[3] if len(sys.argv) > 3 else "40"
inc = json.load(open(f"data/incidents_{split}.json"))[idx]
lines = inc["log_snippet"].splitlines()
print("ID:", inc["id"], "| difficulty:", inc["difficulty"], "| injection:", inc["injection_type"])
print("ALERT:", inc["alert_text"])
print("ANSWER:", inc["true_root_cause"], "->", inc["correct_runbook"])
if mode == "key":
    pats = [re.compile("^" + re.sub(r"\\\{[a-z]+\\\}", ".+", re.escape(t)) + "$") for t in NOISE]
    keep = [l for l in lines if not any(p.match(" ".join(l.split()[4:])) for p in pats)]
    print(f"--- NON-NOISE LINES ({len(keep)} of {len(lines)}) ---")
    print("\n".join(keep))
else:
    n = int(mode)
    print(f"--- LOGS (first {n} of {len(lines)} lines) ---")
    print("\n".join(lines[:n]))
