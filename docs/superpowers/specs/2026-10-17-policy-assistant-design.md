# Remote Work Policy Assistant Design

Build Project 1 from the Week 2 handout: a working enterprise policy Q&A bot, a scored 15-question evaluation with failure analysis, and submission assets. Target approximately one hour for implementation; report remaining work honestly if setup or evaluation takes longer.

## User and corpus

Help new remote employees answer equipment, spending, and security questions from four English public GitLab handbook pages in a Streamlit chat, targeting 95% faithfulness.

1. https://handbook.gitlab.com/handbook/finance/procurement/office-equipment-supplies/
2. https://handbook.gitlab.com/handbook/finance/spending-company-money/
3. https://handbook.gitlab.com/handbook/people-group/acceptable-use-policy/
4. https://handbook.gitlab.com/handbook/company/culture/all-remote/working-while-traveling/

GitLab owns the source of truth. Preserve attribution and check applicable reuse terms before distributing snapshots. Download only these pages; do not recursively crawl linked content. Preserve the distinction between requirements and recommendations. Answers describe the downloaded snapshot, not guaranteed current policy.

## Pipeline

Extract main HTML content, dropping navigation, scripts, and boilerplate while retaining headings, lists, tables, and source links. Store retrieval time, content hash, source URL, and title. Refresh manually before the demo; display snapshot dates. Failed refreshes preserve the previous complete index and report failure.

Split on headings, then into roughly 200-token chunks with 30-token overlap, respecting the embedding tokenizer's actual input limit including heading prefixes. Retain stable chunk IDs, heading paths, and section URLs. Local sentence-transformers/all-MiniLM-L6-v2 embeddings and NumPy vectors persisted with JSON metadata are sufficient for four pages.

Retrieve eight BM25 and eight cosine-similarity candidates, deduplicate by chunk ID, merge with reciprocal rank fusion (constant 60), rerank using cross-encoder/ms-marco-MiniLM-L-6-v2, and retain four evidence chunks. Provide dense-only mode with the same final k for evaluation. Cache loaded models and indexes.

Use LangChain document/model interfaces and LangGraph orchestration: retrieve → rerank → generate → verify → answer or fallback. No retry loops. Generation uses a configurable OpenAI-compatible endpoint, API key, and model supplied through environment variables; resolve credentials and validate provider capabilities before live evaluation. Never commit secrets or print them.

Return an answer, clarification, or insufficient-evidence outcome. Require inline citations tied to provided chunk IDs and show excerpts with source links. Validate citation IDs deterministically and use a model support check with the same full context. Invalid output, missing required citations, unsupported claims, and verification errors return a fallback. Model checking is a guard, not independent evaluation evidence. No web fallback or invented confidence percentage. Show errors clearly rather than fabricating successful answers.

## Evaluation and acceptance

Freeze 15 questions and expected evidence before retrieval tuning: six direct, two paraphrases, one exact-term, three cross-document, one ambiguous, and two unanswerable questions (including a plausible missing-policy question). Expected facts and evidence must be derived from downloaded content. Cross-document questions require evidence from every required source. Add a conflict case only if the corpus actually contains a relevant conflict; do not alter real documents to create one.

Manually label relevant chunk IDs for answerable questions. Compare dense-only and hybrid/reranked modes on the same frozen questions and snapshot. Recall@4 is retrieved relevant chunks / all labeled relevant chunks; precision@4 is retrieved relevant chunks / number actually retrieved (zero for empty retrieval). Report macro averages over answerable questions only. Also report whether all required source documents were retrieved for each cross-document question.

Record answers, retrieved IDs and ranks, citations, status, elapsed seconds, and errors. Human review assesses correctness, claim support, citation support, clarification, and fallback. Faithfulness is supported factual claims / all factual claims in substantive answers; exclude refusals from this denominator and report answer coverage separately. Automated citation validity is separate from semantic support. Label unreviewed results as unreviewed. Targets: at least 95% faithfulness, 80% macro evidence recall@4, and median warm-query latency under 10 seconds. Report actual results even when targets are missed; report cold startup separately.

The evaluation report must explain where retrieval succeeds and fails and why, distinguishing extraction, chunking, retrieval, and generation issues. Record actual iterations, including regressions, without inventing results.

## Deliverables

Runnable Streamlit app; reproducible ingestion; configuration template; dependency lock and setup instructions; prompts; source attribution; meaningful automated tests; machine-readable evaluation output; readable evaluation report; Google Doc-ready project write-up covering overview, datasets, prompts, iterations, learnings, and AI coding tool use; and a demo script of at most five minutes.

Final submission additionally requires an actual recorded video of at most five minutes, the project documentation placed in Google Docs, and code uploaded to GitHub (the Project 1 section also permits a ZIP). Preparing local text is not completion of those external deliverables. Do not publish or upload without user authorization. Keep the cloned solution untouched; acknowledge it as a reference and describe the original implementation differences.
