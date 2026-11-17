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

- 5 of 5 correct, 0 errors (Day 9 baseline without RAG: 4 of 5).
- inc-006 (decoy): now datastore_latency 0.85, runbook datastore-latency.md, not escalated. Day 9 had datastore_full 0.85.
- All 5 cited runbook values are real file names.
- Caveat: n=5, 3 of 5 are datastore_latency, one incident changed, one run each (model sampling is not controlled). Consistent with the runbook "How to tell this apart" hint helping, but not proof. Full dev 40 comparison comes on Day 12/13.


### Fallback test (Colab, subprocess, no LLM calls)

- `rag.search('datastore latency high', max_distance=0.1)` returned `[]`.
- `search_runbooks` with the default threshold returned datastore-latency.md, datastore-full.md, storage-path-down.md with `retrieval_failed = False`.
- With `RAG_MAX_DISTANCE=0.1`, `search_runbooks` returned `{'runbook_matches': [], 'retrieval_failed': True}`.
- Note: calling `rag.build_index()` inside a notebook kernel right after `pip install` hit an opentelemetry ImportError (stale packages in the kernel). Not a code bug; run scripts as subprocesses or restart the session.
