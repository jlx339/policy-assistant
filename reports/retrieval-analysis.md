# Retrieval-only comparison

Both modes were executed against the same acquired 68-chunk snapshot and 15 frozen questions. Macro metrics include the 12 answerable cases. Full per-question rankings, model scores, and snapshot/question hashes are in [retrieval-comparison.json](retrieval-comparison.json).

| Method | Macro recall@4 | Macro precision@4 |
| --- | --- | --- |
| Dense only | 95.83% | 37.50% |
| Dense + BM25 + cross-encoder | 95.83% | 37.50% |

Both methods recovered every labeled passage for 11 answerable questions. For Q10, both found the equipment contact passage and both overlapping expense-deadline chunks, providing the two source pages needed for the cross-document answer.

For Q11 (personal email/movie use and security monitoring), both retrieved the monitoring passage but missed `c22543c9ab6131bc`, which contains the conditional permission for personal use. Several laptop-unavailability passages ranked ahead of that permission. The evidence set therefore cannot support a complete answer. This is a retrieval failure rather than an unavailable-corpus fact: the missing permission exists in the acquired corpus.

The cross-encoder changed rankings without improving gold evidence coverage on this small set. The experiment does not justify claiming hybrid superiority. Returning four passages also lowers precision when a single passage fully answers a question. A later experiment could investigate query decomposition or adaptive retrieval size, but these results must remain the baseline rather than being replaced by tuned scores without disclosure.

This report makes no claim about generated-answer correctness, faithfulness, or live latency. Those require the separate full inference run and answer review. Evidence labels were inspected by Codex against the source snapshot; that is agent source review, not human sign-off.
