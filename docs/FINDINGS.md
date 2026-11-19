# Findings

> Draft skeleton (Day 14 prep). Every `TBD` is filled only from real run outputs. No number is written before the run exists.
> Wording rules: counts are "k of n"; calibration is "exploratory"; per-injection-style n=2 is "indicative only"; 1 incident = 2.1 points (of 48 known on test).

## 1. Setup
- Data: 100 synthetic incidents (dev 40, test 60: 48 known cause, of which 12 carry a prompt injection; 12 unknown cause). Own noise templates, VMware/Nutanix-style signals are my own approximations. No real incident data.
- Systems: `baseline` (1 call, alert + filtered logs), `baseline_ctx` (same + all 10 runbooks), `agent_norag`, `agent_rag`.
- Model: Gemini free tier `gemini-3.5-flash-lite` for both tiers. Free tier limit is 500 requests per day, so runs were split across days.
- Test set frozen (sha256 checked by `tests/test_frozen.py`). Never tuned on test. One full test run per system with `NO_CACHE=1`. No guardrail layer was wired during these runs, so the main table is effectively guardrails-off.

## 2. Dev work (Day 14)
- KEYWORDS filter: 56 of 68 dev signal lines kept before, 68 of 68 after adding 8 patterns. Chosen by looking at dev, so dev numbers may be optimistic.
- Benign-line filter: TBD (round 1 result, agent_rag, dev only).
- Dev error analysis table: TBD (from `dev_agent_rag_outputs.json`).

## 3. Test results (Day 15)
60 held-out test incidents (48 known cause, 12 unknown cause), one run per system, `NO_CACHE=1`. No guardrail layer was wired during these runs, so the main table is effectively guardrails-off. Counts are k of n; 1 incident = 2.1 points (of 48 known).

| System | top1 | top3 | runbook_top1 | top1_hard_misleading | top1_injection | injection_followed | abstain_on_unknown | false_abstain_on_known | errors | ece | brier | avg_in_tokens | avg_sec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 96% (46/48) | 98% (47/48) | 0% (0/48) | 91% (21/23) | 92% (11/12) | 0% (0/12) | 100% (12/12) | 2% (1/48) | 0 | 0.209 | 0.148 | 1276 | 3.37 |
| baseline_ctx | 92% (44/48) | 94% (45/48) | 92% (44/48) | 83% (19/23) | 92% (11/12) | 0% (0/12) | 100% (12/12) | 8% (4/48) | 0 | 0.153 | 0.128 | 7776 | 1.67 |
| agent_norag | 94% (45/48) | 96% (46/48) | 0% (0/48) | 87% (20/23) | 83% (10/12) | 0% (0/12) | 83% (10/12) | 2% (1/48) | 0 | 0.199 | 0.145 | 1741 | 7.36 |
| agent_rag | 96% (46/48) | 96% (46/48) | 92% (44/48) | 91% (21/23) | 92% (11/12) | 0% (0/12) | 92% (11/12) | 4% (2/48) | 0 | 0.144 | 0.118 | 2209 | 14.93 |

Calibration is exploratory (small n). runbook_top1 is 0% for systems that never see a runbook (baseline, agent_norag).

### Interpretation
- baseline vs agent_rag (k of 48): 46 vs 46, a tie. On hard+misleading both got 21 of 23. agent_rag used about 3 calls per incident and 14.9 s per incident, against 1 call and 3.4 s for baseline, so in this test the agent did not clearly beat the single-prompt baseline. A difference of 2-3 incidents is 4-6 points; do not overclaim.
- agent_norag vs agent_rag (value of RAG): 45 vs 46 of 48, a 1-incident difference (2.1 points) from a single run. This is not evidence that RAG helps. agent_rag did get 44 of 48 runbook matches, which agent_norag cannot do by design.
- baseline_ctx vs agent_rag (runbook stuffing vs retrieval): 44 vs 46 of 48, hard+misleading 19 vs 21 of 23, false abstain 4 vs 2 of 48. The direction favors retrieval, but 2 incidents is within single-run noise. baseline_ctx averaged 7776 input tokens against 2209 for agent_rag.
- Prompt injection: the injected instruction was followed 0 of 12 times in all four systems. No guardrail was active in these runs, so this reflects the model's own behavior on these 12 incidents only.
- Calibration (exploratory, bins have small n): ECE 0.144 and Brier 0.118 for agent_rag, against 0.209 and 0.148 for baseline. Single run, small bins; indicative only.

## 4. Hard cases (Day 16)
- Injection incidents (12): top1_injection TBD, injection_followed TBD. Per-style n=2, indicative only.
- Unknown incidents (12): abstain_on_unknown TBD. false_abstain_on_known TBD.
- Confusion pairs (expected vs got) on hard and misleading incidents: TBD.
- Runbook gaps: TBD.
- Optional model comparison (Gemini vs Groq): TBD.

## 5. Guardrails and red-team (Day 17)
- Regex layer on vs off, 12 test injection incidents, per type k of 2: TBD. Regex was written from dev types 0, 1, 2 only and is expected to miss unseen styles.
- Indirect injection (poisoned runbook chunk): unit test + one manual run: TBD.
- Manual red-team (10-15 attempts, dev only):

| # | Where | Attempt (short) | Agent top cause | Followed attacker? | Flags / notes |
|---|---|---|---|---|---|
| 1 | log | TBD | TBD | TBD | TBD |

- Optional red-team set (23 hand-written incidents, run once): TBD. On Day 16 prep, the regex layer matched 0 of 23 payloads (fresh wording, by design).

## 6. What worked / what failed
Numbers below are from the single test run per system (48 known, 12 unknown). Nothing was changed after the test run started.

### What worked
- No run errors in any system (errors 0).
- The injected instruction was followed 0 of 12 times in all four systems (no guardrail layer was active).
- Abstaining on unknown causes: 12 of 12 (baseline, baseline_ctx), 11 of 12 (agent_rag), 10 of 12 (agent_norag).
- Retrieval picked the matching runbook for 44 of 48 known incidents in agent_rag, the same as baseline_ctx, while using 2209 input tokens per incident instead of 7776.
- On the 23 hard+misleading incidents, baseline and agent_rag both got 21.

### What failed (not fixed, test set is frozen)
Known-cause incidents that were missed:

| System | Missed (expected -> got, escalated?) |
|---|---|
| baseline (2) | inc-020 host_failure_ha -> memory_pressure (no); inc-099 nic_link_flap -> unknown (yes) |
| baseline_ctx (4) | inc-020 host_failure_ha -> memory_pressure (no); inc-039 and inc-040 memory_pressure -> unknown (yes); inc-099 nic_link_flap -> unknown (yes) |
| agent_norag (3) | inc-020 host_failure_ha -> memory_pressure (no); inc-098 host_failure_ha -> datastore_latency (no); inc-099 nic_link_flap -> memory_pressure (yes) |
| agent_rag (2) | inc-054 ntp_drift -> unknown (yes); inc-099 nic_link_flap -> memory_pressure (yes) |

- inc-099 was missed by all four systems. inc-020 was missed by three (agent_rag got it right in this run). These are shared hard cases, so the miss is not specific to the agent design.
- Unknown-cause incidents answered with a wrong cause: agent_rag inc-085 (-> memory_pressure, not escalated, a confident wrong answer) and inc-073 (-> memory_pressure, escalated); agent_norag inc-082 and inc-085 (-> memory_pressure, not escalated); baseline_ctx inc-073 (-> datastore_latency, escalated). Escalated ones still reach a human; the not-escalated ones are the risky failures.
- agent_rag inc-054 (ntp_drift -> unknown) is a case where the agent abstained although baseline answered correctly. It cost 1 incident (2.1 points), within single-run noise.
- Root-cause reading of these misses (which log lines were dropped or misleading) is TBD: to be written from `test_agent_rag_outputs.json` without changing the system.

### Process note
Before the final agent_rag run, a 3-incident probe (inc-007, 004, 005) and one interrupted partial run (12 incidents) were run on the test split only to check API quota and the API key setup. Their results were discarded, no code, prompt or threshold changed, and the table above comes only from the full runs.

## 7. Limitations
- Synthetic data, 10 fault types, closed set of causes.
- Test set has 60 incidents (48 known cause). 1 incident = 2.1 points.
- Per-injection-style n=2: indicative only, not a statistical claim.
- Single run per system (model output varies between runs).
- Free-tier models, own noise templates.
- KEYWORDS and benign-line patterns were tuned on dev, using my own synthetic noise templates. They may not transfer to real logs.
- RAG distance threshold was tuned on 3 unknown dev incidents (weak signal).
- MemorySaver is in-memory: restart loses pending approvals.
- API: single shared key, no per-user thread ownership, not production security, no rate limiting.
- Regex guardrail is bypassable by design (extra layer, not a guarantee).
- - The model ignores the temperature setting, so outputs vary between runs. With one run per system, differences of 1-2 incidents (2.1-4.2 points) are noise.
- Confident wrong answers exist: on unknown-cause incidents agent_rag and agent_norag each answered inc-085 with a wrong cause and did not escalate. The confidence score is not a reliable safety signal (confidence of exactly 0.5 is not escalated; empty logs can still get 0.9 confidence).
- proposed_fix is a single line, not a full remediation plan. Remediation steps need human review and approval.
- On this synthetic set the single-prompt baseline already scores 46 of 48, so the test cannot show whether the agent or RAG helps on harder or real incidents.
- The agent costs about 3 calls and 14.9 s per incident (baseline: 1 call, 3.4 s).
