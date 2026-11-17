# Dev log (dev set only, test set frozen)

All numbers are k of n counts on the dev set. Confidence/calibration notes are exploratory.

## Day 9 (17 Nov 2026): graph v1, no RAG

- Run: `PYTHONPATH=. python scripts/run_batch.py dev 5` (dev[0..4]), Gemini `gemini-3.5-flash-lite`.
- Result: 4 of 5 correct, 0 errors. Exploratory only: 3 of the 5 incidents have the same cause (datastore_latency).
- Miss: inc-006 (misleading, datastore_latency). Got datastore_full 0.85, not escalated.
  - filter_logs kept both real signal lines and the decoy "snap fail ... low space ds-prod-05".
  - analyze_logs findings were correct. The error is in hypothesize: datastore_full 0.85 rested on the decoy only; datastore_latency (correct) was rank 2 at 0.7, so top-3 recall hit, top-1 miss.
  - A confident wrong answer was not escalated (calibration issue). Kept as an error-analysis example for Day 14.
- No prompt changes made on purpose.

## Day 10: RAG

### Retrieval sweep (`scripts/check_retrieval.py`, dev 40, query = alert + filtered logs, no LLM)

| max_distance | hit@3 | unknown incidents with no match |
|---|---|---|
| 1.0 | 26 of 37 | 0 of 3 |
| 1.2 | 29 of 37 | 0 of 3 |
| 1.4 | 29 of 37 | 0 of 3 |
| 1.6 | 29 of 37 | 0 of 3 |
| 9.9 | 29 of 37 | 0 of 3 |

- Chosen: `RAG_MAX_DISTANCE = 1.2` (default in app/rag.py). It is the tightest value that loses no hits; 1.2, 1.4, 1.6 and no limit give identical results on dev.
- Honest caveat: no threshold from 1.0 to 9.9 made any of the 3 dev unknown incidents return "no match", so the threshold does not separate unknown from known incidents here (n=3, weak signal). The no-match fallback is tested only by forcing a tiny threshold (see "Fallback test" below), not by real data.
- Misses at 1.4 (8 of 37): inc-012 storage_path_down, inc-025 and inc-026 nic_link_flap, inc-046 dns_failure, inc-051, inc-053 and inc-056 ntp_drift (all 3 dev ntp_drift incidents), inc-068 raid_degraded (inc-068 has zero signal lines kept by filter_logs, a known KEYWORDS issue).
- This sweep query has no LLM log findings, so it is a pessimistic proxy: inc-012 missed here but the real graph (alert + findings) retrieved storage-path-down.md.
- Not changed yet: runbooks and chunking (hit@3 is above the 70% target). Possible dev-only improvement for Day 14: ntp_drift runbook wording, KEYWORDS.

### Graph with RAG (`run_batch.py dev 5`, same 5 incidents as Day 9)

- First run (Day 10 session): 5 of 5 correct, 0 errors (Day 9 baseline without RAG: 4 of 5).
- inc-006 (decoy): datastore_latency 0.85, runbook datastore-latency.md, not escalated. Day 9 had datastore_full 0.85.
- All 5 cited runbook values are real file names.
- UPDATE (Day 11 re-run, same code path, fresh clone): 4 of 5 correct, inc-006 MISS again (datastore_full 0.85, runbook datastore-full.md, not escalated). So inc-006 flips between runs; the first 5 of 5 is not evidence that RAG fixes it.
- Correct statement: RAG alone does not reliably fix the inc-006 decoy. Model output varies from run to run (temperature is ignored by this model) and a fresh clone has no cache/. Full dev 40 with repeated runs comes on Day 12/13.

### Fallback test (Colab, subprocess, no LLM calls)

- `rag.search('datastore latency high', max_distance=0.1)` returned `[]`.
- `search_runbooks` with the default threshold returned datastore-latency.md, datastore-full.md, storage-path-down.md with `retrieval_failed = False`.
- With `RAG_MAX_DISTANCE=0.1`, `search_runbooks` returned `{'runbook_matches': [], 'retrieval_failed': True}`.
- Note: calling `rag.build_index()` inside a notebook kernel right after `pip install` hit an opentelemetry ImportError (stale packages in the kernel). Not a code bug; run scripts as subprocesses or restart the session.

## Day 11: human approval, final graph

- Added `human_approval` (interrupt), `route_after_approval`, `report` stub ('TODO') in app/nodes.py; `build_graph(use_rag, use_approval, checkpointer)` in app/graph.py; `scripts/run_cli.py`; `run_batch.py` uses `use_approval=False`.
- Plan code fix: in `route_after_approval` the retries check was indented inside `if approved`, so rejects never hit the retry limit. Fixed (approved -> report; retries >= MAX_RETRIES -> report; else hypothesize).
- Tested in Colab (`run_cli.py dev 0`, inc-002):
  - Approve path: graph paused with hypotheses + proposed_fix, `y` gave report 'TODO'.
  - Reject path: feedback "try memory pressure" re-ran hypothesize. The model kept datastore_latency on top (0.9) and added memory_pressure at 0.4 using the feedback as evidence, so feedback is used as a hint, not blindly followed. Second reject ("still not sure, check again") hit MAX_RETRIES=2 and went to report 'TODO' without a third pause.
- One run each, one incident (n=1), so this shows the control flow works, not how often feedback helps.
- Batch re-run with `use_approval=False`: 4 of 5 (see Day 10 update above).

## Day 12 (17 Nov 2026): report node, edge cases, smoke test

### Report node
- `report` in app/nodes.py is now a template report with no LLM call: header, alert, service/severity, status, hypotheses (confidence 2 decimals, runbook or none, evidence), recommended steps ("for human review, never auto-run"), key log findings, optional security flags, postmortem draft (TBD).
- Status is ESCALATED if `escalated` is true or the human did not approve; otherwise "Recommended root cause reviewed and approved by a human".
- Safe on partial state (missing keys, empty lists).

### Tests
- `tests/test_report.py`: 13 offline tests (no network, no Gemini): report variants, empty log_snippet, 0 hypotheses, cause not in allowed list -> unknown, confidence clamp and fake runbook name -> None, retrieval_failed lowers confidence x0.8, RAG index missing, 5000-char alert truncated to 2000.
- Colab: `pytest tests -q` gave 21 passed (8 earlier + 13 new).

### End-to-end check (`scripts/check_report.py`, real Gemini, n=1 per case)
- A: approve path on dev[0..2] (inc-002, inc-003, inc-001): real report built, status "approved by a human", top cause datastore_latency 0.95 in all three. Same cause three times, so this shows the pipeline runs, not accuracy.
- B: reject twice on dev[0]: 2 pauses, retries=2, no third pause, status ESCALATED.
- C: empty log_snippet: no crash, but still datastore_latency 0.9 (the alert text itself says "latency"). Confident answer with no log evidence; calibration example for Day 14. No code change.
- D: 6000-char alert: no crash, datastore_latency 0.76 (0.95 on the normal alert). One run, could be noise.
- Cosmetic: `proposed_fix` comes back as one line "1. ... 2. ... 3. ..."; readable, not changed.

### Smoke test: `run_batch.py dev 40` (RAG on, use_approval=False), one run
- Result: 34 of 40 correct, 0 errors (one retried GoogleAPIError recovered). Part of the run may have come from cache of an interrupted earlier run on the same code, so treat as a single sample.
- 3 of 3 unknown incidents correct (unknown 0.2-0.3, escalated). Known-cause incidents: 31 of 37.
- Misses (6):
  - inc-006 (misleading): datastore_full 0.85, not escalated. Fourth run on this incident: miss, hit, miss, miss.
  - inc-019, inc-047, inc-068 (hard): unknown 0.2-0.3, escalated. All three have zero signal lines kept by filter_logs (known KEYWORDS issue). Safe failure.
  - inc-086 (hard): expected datastore_latency, got storage_path_down 0.85, not escalated. Confident wrong.
  - inc-027 (misleading): got unknown 0.95 while citing nic-link-flap.md, escalated. Contradictory (confident "unknown" with the right runbook). Cause not checked yet; raw model output to be inspected on Day 14.
- Confident wrong and not escalated: 2 of 6 misses (inc-006, inc-086). Escalated misses: 4 of 6. Calibration is exploratory.
- Not fixed on purpose. run_batch.py now flushes output and supports `EVAL_SLEEP` (seconds to wait after each incident).
- Note: `use_approval=False` has no report node, so the report node was tested with check_report.py, not the batch.

### Next
- Day 13: baseline + evaluation harness. Repeat dev 40 several times for run-to-run variance (inc-006 flip, inc-027).

- ## Day 13 (18 Nov 2026): baseline + evaluation harness

- Added `app/baseline.py` (baseline = one call, alert + filtered logs; baseline_ctx = same + all 10 runbooks), `eval/metrics.py` (pure metric functions), `eval/run_eval.py` (4 systems, per-incident try/except so an error is counted as an error, saves results/outputs/failures per system), `eval/make_table.py`, `tests/test_metrics.py` (7 offline tests).
- Changes vs the plan code: metrics moved to their own module; errors counted separately (`errors`); `runbook_top1` compares file stems; per-system `*_outputs.json` saved for Day 14 error analysis; `LIMIT` and `EVAL_TAG` env vars.
- Tests: `pytest tests -q` gave 28 passed (8 + 13 + 7).
- Small run (`LIMIT=5`, dev[0..4], one run, fresh clone): baseline 4 of 5 top1, agent_rag 4 of 5 top1. Exploratory only: 3 of the 5 incidents share one cause.
  - baseline miss: inc-012 (got raid_degraded, confidence about 0.5, not escalated).
  - agent_rag miss: inc-006 (datastore_full). The baseline got inc-006 right in this run, so nothing here shows the agent beating the baseline.
  - top3: baseline 4 of 5, agent_rag 5 of 5.
  - runbook_top1: agent_rag 4 of 5; baseline 0 of 5 by design (no runbooks), report as n/a.
  - Cost per incident (fresh cache): baseline 1 call, 1324 input tokens, 2.6 s; agent_rag 2.8 calls, 2261 input tokens, 8.2 s.
  - Calibration (exploratory, n=5): ECE and Brier hand-checked against the code (ECE baseline 0.16, agent 0.17).
- Observation to check on Day 14: escalation rule is confidence < 0.5, so exactly 0.5 is not escalated.
- Next: Day 14 full dev run, 4 systems, one run each (n=40), then error analysis.
