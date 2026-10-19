# Evaluation procedure

The 15 cases were drafted from the four public pages before retrieval tuning. They are not frozen against a local snapshot until acquisition and evidence review finish. Refreshes invalidate labels when the corpus or question hash changes.

1. Download and index the real corpus following the root README.
2. Run `python -m policy_assistant.evaluate --prepare`. This writes a full evidence catalog and initializes snapshot-bound labels without model calls. It refuses to overwrite reviewed labels.
3. Read `questions.json` and `evidence-catalog.md`. Confirm expected facts against the actual snapshot, including that Q14/Q15 are unanswerable within these four pages. Revise stale facts before labeling. Do not invent unavailable policy details. Cross-document questions require at least two source URLs.
4. For each answerable case, put **all relevant chunk IDs** into `relevance.json` under `relevant_chunks.Q01` etc. Include overlapping chunks when they independently contain the relevant evidence. Empty labels belong only to clarify/insufficient cases. Mark `reviewed: true` only after checking every case. Keep the generated corpus/question hashes; if questions change, rerun prepare before freezing the labels.
5. Run `python -m policy_assistant.evaluate --mode both --interval 65`. Both modes use the same snapshot and cases. Dense baseline returns the top four cosine matches; hybrid adds BM25 and cross-encoder reranking. The run makes one warm-up request followed by 30 scored queries, with up to two model calls per query. The 65-second interval reduces free-tier token-limit pressure; the run takes roughly 35 minutes. Each query is checkpointed to reports/results.json. If interrupted, use the same command with --resume; snapshot, questions, model, modes, and pipeline code must still match. Starting a new run archives previous results in reports/runs/. Failed cases remain scored failures and are not silently retried.
6. Inspect actual answers in `reports/results.json` against the full evidence catalog, rather than trusting the app's verifier. For each substantive answer, add a review to `reviews.json` with a key such as `hybrid:Q01` and this structure:

```json
{
  "hybrid:Q01": {
    "answer_hash": "copy this result row's review_hash from reports/results.json",
    "supported_claims": 1,
    "total_claims": 1,
    "correct": true,
    "citation_support": true,
    "notes": "Explain why the answer succeeds or fails, with source sections and any missing evidence."
  }
}
```

The example is a schema illustration, not an actual result. Copy the actual result row’s `review_hash` into `answer_hash`; judgments with a missing or stale hash are ignored, so rerunning a query cannot silently reuse scores for a changed answer or changed evidence. Count atomic factual assertions. Check whether the exact cited passage supports each claim, preserves requirements versus recommendations, and covers the question. `correct` means the answer addresses all expected facts without contradictions; `citation_support` means every factual claim is supported by its cited passage. Add notes for fallback/clarification cases too, explaining whether the behavior was appropriate. Automated expected-status matching alone does not prove substantive answer quality.

7. Run `python -m policy_assistant.evaluate --report-only` to regenerate the report without more API calls. Faithfulness stays undefined until every substantive answer in a mode has claim counts. An all-refusal run has no faithfulness percentage; coverage exposes the missing answers. Report incomplete reviews as incomplete.
8. Add concrete success/failure causes and the dense-versus-hybrid interpretation to the write-up. Changing retrieval justifies another run; preserve prior results before overwriting them. If targets are missed, report that outcome instead of changing labels to improve scores.

Recall@4 uses all labeled relevant chunk IDs as its denominator. Precision@4 uses the number of unique returned chunks (up to four). Macro averages include only the 12 answerable cases. The report also records required-source coverage for cross-document questions. Overlapping gold chunks can make recall harder; discuss that limitation and source coverage together.

## Current run review

Human review is complete and confirmed. On October 18, 2026, the project owner confirmed reviewing and agreeing with the draft judgments, including the flagged failures. Approved entries are stored in `reviews.json` with answer hashes and explicit confirmation provenance. `review-draft.json` and `reports/answer-review-draft.md` are retained as historical draft artifacts. See `reports/evaluation-analysis.md` for confirmed scores and limitations. Changes to the answers invalidate the corresponding review hashes.
