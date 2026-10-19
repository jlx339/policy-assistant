# Full evaluation findings

The actual run contains 30 scored queries: the same 15 frozen questions for dense and hybrid retrieval, using the same acquired snapshot and Groq `openai/gpt-oss-120b`. Requests were paced 65 seconds apart. Source-reviewed gold labels were prepared before this run. Results are preserved in [results.json](results.json); per-question outputs are in [evaluation.md](evaluation.md).

| Measured outcome | Dense | Hybrid + reranker |
| --- | --- | --- |
| Questions | 15 | 15 |
| Provider/service errors | 0 | 0 |
| Recall@4, 12 answerable cases | 95.83% | 95.83% |
| Precision@4, 12 answerable cases | 37.50% | 37.50% |
| Answerable cases receiving answers | 12/12 | 11/12 |
| Expected response type | 14/15 | 13/15 |
| Valid citation IDs among answers | 100% | 100% |
| Median warm query time | 1.48 s | 2.16 s |
| Confirmed claim faithfulness | 89.66% (26/29) | 81.82% (18/22) |
| Confirmed answer correctness, among answers | 75.00% (9/12) | 63.64% (7/11) |

Latency excludes the deliberate waits between queries. It includes the deterministic clarification/refusal paths and is measured on this user's environment, not a production benchmark. Response-type matching and syntactically valid citations do not establish factual correctness.

## Successes

Both modes answered the 90-day reimbursement threshold, equipment contact route, encryption/serial-number evidence, and the cross-document contact-plus-deadline question. Both correctly refused the live stock quote and exact Canadian stipend questions. Q12 combined travel security advice with the public-computer prohibition from a different page.

## Failures and causes

- **Q06, both modes — exception scope:** the answers extend an exception for external sharing to the separate prohibition on backup/redundancy. Relevant evidence was present, but generation confused the clauses and the runtime verifier accepted the error. A valid source ID did not prevent this failure.
- **Q11, both modes — retrieval and incomplete generation:** the top four miss the Spending Company Money passage containing personal-use permission and its conditions. Monitoring text is present. Both answer beyond their retrieved evidence and omit material constraints; hybrid also omits the local-law monitoring exception. The verifier should have rejected or limited those claims.
- **Q13, both modes — ambiguity handling:** “Can I do that under the policy?” receives a generic insufficient-evidence fallback. It should ask what action and policy the user means. The deterministic clarification path handles some generic policy wording, but not this form; the frozen benchmark exposes that limitation.
- **Q08, hybrid — verifier rejection:** relevant internet-redundancy evidence is retrieved, but the answer is rejected. The run preserves the final `verification_failed` result, not the rejected proposal or per-case verdict. The exact reason cannot be recovered and must not be guessed.
- **Q05/Q09 — completeness and qualification:** the review draft flags hybrid's missing USB exception details and both modes' blurred distinction between preconfigured company Macs and Day-1 Jamf installation for expensed Macs.

**Human review is complete and confirmed.** On October 18, 2026, the project owner confirmed reviewing and agreeing with all draft judgments, including the flagged failures. The approved 30 entries and their answer hashes are stored in `eval/reviews.json`. Faithfulness counts supported factual claims in returned answers (dense 26/29, hybrid 18/22); correctness uses returned answers as its denominator (dense 9/12, hybrid 7/11). Neither method met the 95% faithfulness target. Refusals remain visible in coverage and response-type metrics rather than being counted as supported claims. The original review draft is retained as an audit artifact.

## Interpretation and next experiment

Hybrid retrieval did not improve recall or precision on this small corpus, answered one fewer answerable query, and had higher median latency. Dense is the stronger measured baseline for this particular run; this is not evidence that dense search generally outperforms hybrid search. The app remains configured as evaluated, and these results have not been replaced by a tuned rerun.

Before broader use, investigate preserving clause-level exceptions, clarification for unresolved references, retrieval decomposition for Q11, and retaining per-case verifier traces. Any changes should be evaluated as a new version against the same frozen cases. Expand the test set beyond 15 questions to reduce the risk of tuning to these examples.
