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

(fill in after running scripts/check_retrieval.py and run_batch.py with RAG)
