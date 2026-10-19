# Remote Work Policy Assistant

Week 2 · Project 1: Enterprise Q&A with Retrieval-Augmented Generation

## 1. Project overview

The Remote Work Policy Assistant helps new remote employees find answers about equipment, expenses, laptop security, and working while traveling. It searches four public GitLab handbook pages, generates an answer from the retrieved passages, and displays citations that link back to the handbook.

The project addresses a common onboarding problem: related policies are spread across several pages, and a question may require information from more than one document. For example, someone buying home-office equipment may need both a contact route and the deadline for submitting an expense claim.

The goal was to build a small, inspectable RAG application using real enterprise documents. It should distinguish an answer supported by the available documents from a vague question or a question the snapshot cannot answer. This is an independent student project, not an official GitLab service.

## 2. Dataset and scope

The knowledge base contains four English-language pages:

| Source | Information covered |
| --- | --- |
| [Home Office Equipment and Supplies](https://handbook.gitlab.com/handbook/finance/procurement/office-equipment-supplies/) | Equipment expense questions, Compass, and the expense-team contact route |
| [Spending Company Money](https://handbook.gitlab.com/handbook/finance/spending-company-money/) | Expense submission, the 90-day rule, and spending expectations |
| [Acceptable Use Policy](https://handbook.gitlab.com/handbook/people-group/acceptable-use-policy/) | Device security, endpoint management, removable media, file sharing, and public computers |
| [Working While Traveling](https://handbook.gitlab.com/handbook/company/culture/all-remote/working-while-traveling/) | Connectivity, public WiFi, equipment, and travel recommendations |

The pages were acquired on October 18, 2026 UTC—October 17 locally in Vancouver—and indexed into **68 chunks**. Each chunk retains a stable ID, source URL, and section reference. Snapshot timestamps and hashes identify the corpus used for evaluation. Refreshing the knowledge base requires downloading the pages and rebuilding the index; the app does not continuously track handbook changes.

The public equipment page links to an internal expense policy, but that internal content is outside this dataset. The assistant therefore cannot establish an exact home-office stipend for a Canadian employee. Likewise, a static policy snapshot cannot supply a live stock price.

GitLab’s handbook is shared under [CC BY-SA 4.0](https://handbook.gitlab.com/handbook/about/handbook-usage/). Source attribution is retained, and downloaded snapshots are excluded from the code package by default.

## 3. RAG design and implementation

The application uses Streamlit for chat, LangChain for model interfaces, and LangGraph for a fixed retrieval → generation → verification flow.

| Stage | Implementation and reason |
| --- | --- |
| Ingestion | Download only the selected pages, extract main content, and remove navigation, scripts, and other page furniture. Preserve headings, lists, tables, and links. |
| Chunking | Build section-aware chunks of about 200 tokens with up to 30 tokens of overlap. Heading prefixes retain context; the largest final embedding input is 202 tokens. |
| Embedding | Use `sentence-transformers/all-MiniLM-L6-v2` locally on CPU. Store normalized vectors in NumPy with JSON metadata, avoiding a hosted vector database for this small corpus. |
| Hybrid retrieval | Retrieve eight dense candidates and eight BM25 candidates, combine them using reciprocal rank fusion, deduplicate, and rerank to four passages with `cross-encoder/ms-marco-MiniLM-L-6-v2`. |
| Baseline | Retrieve the four highest cosine-similarity passages without BM25 or reranking. Evaluate this baseline on the same questions. |
| Generation | Use Groq’s `openai/gpt-oss-120b` with low reasoning effort and a 4,096-token completion budget. Strict structured output returns individual claims with their source IDs. |
| Verification | Construct citations deterministically, reject IDs outside the retrieved evidence, and ask the model to check claim support, citation support, and response appropriateness. |

The UI renders short numbered source links and shows the supporting passages. Original chunk IDs remain in stored results for validation and evaluation. Each question is searched independently; conversation history is displayed but does not resolve references such as “that.” Provider failures are shown as service errors, separately from insufficient evidence.

## 4. Prompt design

The generation prompt limits answers to the supplied evidence, treats document text as data rather than instructions, and forbids inventing policy facts. It also distinguishes mandatory policy from recommendations, preserves deadlines and exceptions, and asks for concise paragraphs or separate Markdown bullets.

The model chooses among three response types: answer, clarification, or insufficient evidence. For the configured Groq model, an answer consists of structured claim/source pairs. The application adds the citation syntax rather than relying on the model to format it consistently.

The verification prompt checks whether every factual claim is supported, whether its cited passage supports it, and whether the response type fits the question. The exact prompts and structured-output adapter are versioned in `src/policy_assistant/prompts.py` and `pipeline.py`.

The verifier is a runtime safeguard using the same configured model, not an independent human judgment. Evaluation showed that it can accept incorrect interpretations.

## 5. Evaluation and results

The frozen evaluation set contains **15 questions**: six direct lookups, two paraphrases, one exact-term question, three cross-document questions, one ambiguous question, and two unanswerable questions. Expected facts and gold evidence labels were inspected against the downloaded corpus by Codex and bound to the corpus and question hashes.

Both retrieval methods were tested, producing **30 scored query results**. Requests were spaced 65 seconds apart to reduce Groq rate-limit pressure. Each completed case was checkpointed so an interrupted run could resume without repeating completed cases.

| Metric | Dense baseline | Hybrid with reranking |
| --- | --- | --- |
| Macro recall@4 | 95.83% | 95.83% |
| Macro precision@4 | 37.50% | 37.50% |
| Answerable questions receiving answers | 12/12 | 11/12 |
| Expected response type | 14/15 | 13/15 |
| Valid citation IDs among returned answers | 100% | 100% |
| Provider/service errors | 0 | 0 |
| Reviewed faithfulness (supported factual claims) | 89.66% (26/29) | 81.82% (18/22) |
| Reviewed answer correctness, among returned answers | 75.00% (9/12) | 63.64% (7/11) |
| Median warm query time | 1.48 seconds | 2.16 seconds |

Retrieval averages cover the 12 answerable cases. Latency excludes the deliberate pauses between questions. Response-type matching measures whether the app answered, clarified, or refused as expected; it does not establish factual correctness. Valid citation IDs establish that a source was retrieved, not that it supports the claim.

The initial targets were at least 80% recall@4, 95% supported factual claims, and median warm latency below 10 seconds. Both methods met the retrieval and latency targets in this run. **Human review is complete and confirmed.** The project owner reviewed and confirmed the source-review judgments, including flagged failures. Faithfulness was 89.66% for dense and 81.82% for hybrid, so neither met the 95% target. These percentages count supported factual claims in returned answers; refusals contain no answer claims and are assessed separately through coverage and response type. Reviewed correctness was 75.00% and 63.64% among returned answers, respectively; it is not an all-question success rate.

### Successes

Both methods found the expense deadline, equipment contact route, and encryption/serial-number requirements. The cross-document purchase question combined the equipment contact information with the spending-page deadline. Both methods also refused to invent a stock quote or an exact Canadian stipend amount.

### Failures and why they happened

- **Backup exception scope:** Both answers incorrectly extended an exception for external file sharing to the separate prohibition on backups using other services. The relevant text was retrieved, but generation confused the clauses and the verifier accepted the error.
- **Personal laptop use:** Both methods missed a passage containing the permission and conditions for personal use. The returned answers went beyond their cited evidence or omitted important qualifications. This combined a retrieval gap with inadequate verification.
- **Ambiguous reference:** “Can I do that under the policy?” received an insufficient-evidence fallback instead of a clarification question. The app’s clarification handling does not cover every ambiguous formulation.
- **Connectivity question:** Hybrid retrieved relevant evidence but rejected the answer during verification. The run retained the final failure status, but not the per-case rejected proposal and verdict, so the exact cause cannot be reconstructed.

Hybrid search did not improve retrieval scores on this dataset. It was slower and answered one fewer answerable question. Dense is the stronger measured baseline for this run; a 15-question experiment does not establish that it is generally better than hybrid retrieval.

## 6. Iterations and lessons learned

The supplied enterprise Q&A example informed the overall RAG pattern, but this project uses a separate implementation, real public documents, local indexes, explicit citations, and bounded answer verification.

Live testing revealed issues that fixture tests alone did not catch:

- The macOS float32 reranker produced NaN scores. Using float64 for this CPU reranker restored finite inference, with additional memory and latency cost.
- Streamlit’s source watcher triggered unused Transformers vision imports. Disabling the watcher stopped the traceback flood; Python edits now require a manual restart.
- A 900-token completion budget truncated JSON. Raising the budget allowed complete responses, while lower reasoning effort reduced token pressure.
- Grouped citations and missing inline citations caused valid content to fail formatting checks. Structured claim/source pairs moved citation rendering into application code.
- Provider failures during verification were initially mistaken for missing evidence. Explicit service-error handling made the difference visible.

The current suite passes **58 tests**, including cached-model inference, LangGraph flow, UI formatting, citation validation, service-error handling, and evaluation checkpoint/resume behavior. These tests check implementation behavior; they do not replace real answer-quality evaluation.

The main learning is that retrieval quality, output formatting, and factual support are separate problems. More complex retrieval did not improve this small benchmark, and model agreement did not prevent exception-scope errors. Future work should focus on preserving qualifications, resolving ambiguity, decomposing cross-document questions, and retaining verifier traces before adding more pipeline complexity.

Extraction also needs improvement: tokenizer decoding leaves awkward spacing in URLs and email addresses, and some chunks retain footer text. Cleaner source text and better chunk boundaries may reduce distraction. A larger, separately held-out question set would make future comparisons more reliable.

## 7. AI tool use and deliverables

Codex assisted with planning, implementation, tests, debugging, evaluation scaffolding, documentation, and draft source review. A separate code-review agent identified issues with stale review binding, staged-corpus validation, malformed status handling, and navigation filtering; regression tests were added for those findings. The project owner ran network-enabled setup and live evaluation commands and checked the UI. The project owner completed and confirmed the answer-quality review, including the documented failures, on October 18, 2026. The confirmed judgments and answer hashes are stored in eval/reviews.json.

The code package includes source configuration, ingestion and retrieval code, the chat application, prompts, tests, the frozen questions and labels, actual evaluation outputs, and source-review notes. `reports/evaluation.md` contains per-question results; `reports/evaluation-analysis.md` explains their interpretation. A demo script is prepared for a recording under five minutes. Publishing this write-up to Google Docs and recording/submitting the video remain separate submission steps.
