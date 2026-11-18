# Findings

> Draft skeleton (Day 14 prep). Every `TBD` is filled only from real run outputs. No number is written before the run exists.
> Wording rules: counts are "k of n"; calibration is "exploratory"; per-injection-style n=2 is "indicative only"; 1 incident = 2.1 points (of 48 known on test).

## 1. Setup
- Data: 100 synthetic incidents (dev 40, test 60: 48 known cause, of which 12 carry a prompt injection; 12 unknown cause). Own noise templates, VMware/Nutanix-style signals are my own approximations. No real incident data.
- Systems: `baseline` (1 call, alert + filtered logs), `baseline_ctx` (same + all 10 runbooks), `agent_norag`, `agent_rag`.
- Model: Gemini free tier `gemini-3.5-flash-lite` for both tiers. Free tier limit is 500 requests per day, so runs were split across days.
- Test set frozen (sha256 checked by `tests/test_frozen.py`). Never tuned on test. Test run once per system with `NO_CACHE=1`, regex guardrails off for the main table.

## 2. Dev work (Day 14)
- KEYWORDS filter: 56 of 68 dev signal lines kept before, 68 of 68 after adding 8 patterns. Chosen by looking at dev, so dev numbers may be optimistic.
- Benign-line filter: TBD (round 1 result, agent_rag, dev only).
- Dev error analysis table: TBD (from `dev_agent_rag_outputs.json`).

## 3. Test results (Day 15)
TBD: paste `make_table.py test` output.

### Interpretation
- baseline vs agent_rag (k of 48): TBD. A difference of 2-3 incidents is 4-6 points; do not overclaim.
- agent_norag vs agent_rag (value of RAG): TBD.
- baseline_ctx vs agent_rag (runbook stuffing vs retrieval): TBD.
- Calibration (exploratory, bins have small n): TBD.

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
TBD

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
