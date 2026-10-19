# Remote Work Policy Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Native execution is recommended for this small, sequential build; do not dispatch agents without the user's selection.

**Goal:** Deliver a cited policy Q&A app and evidence-backed Project 1 evaluation and submission materials.

**Architecture:** Snapshot four public GitLab handbook pages, build a local hybrid index, and orchestrate retrieval, reranking, generation, and verification through LangGraph. Streamlit and a CLI evaluator share the same pipeline.

**Tech Stack:** Python 3.11+, LangChain Core and OpenAI integration, LangGraph, sentence-transformers, NumPy, rank-bm25, BeautifulSoup, requests, Streamlit, pytest, python-dotenv.

**Spec:** [Agreed design](../specs/2026-10-17-policy-assistant-design.md), consolidated from the approved conversation.

## Global Constraints

- Keep the cloned solution untouched; acknowledge it as a reference and describe the original implementation differences.
- Download only these pages; do not recursively crawl linked content.
- No retry loops.
- Never commit secrets or print them.
- Targets: at least 95% faithfulness, 80% macro evidence recall@4, and median warm-query latency under 10 seconds.
- Report actual results even when targets are missed; report cold startup separately.
- Do not publish or upload without user authorization.

## Review Focus

- Navigation-heavy or empty pages must not silently become the knowledge base (Task 1).
- Changed or partially downloaded sources must not corrupt the previous complete index (Tasks 1–2).
- Fewer than four candidates and duplicate results must produce valid rankings and metrics (Tasks 2 and 5).
- Malformed model output, unknown citations, or checker failures must produce fallback (Task 3).
- Missing credentials, unavailable models, and provider errors must leave the UI usable and evaluation errors visible (Tasks 3–5).

## File structure

All paths below are relative to `policy-assistant/`.

| File | Responsibility |
| --- | --- |
| `pyproject.toml`, `requirements.lock`, `.env.example`, `.gitignore` | Dependencies, configuration template, generated-file exclusions |
| `sources.json` | Four approved URLs and attribution metadata |
| `src/policy_assistant/models.py` | Shared typed records |
| `src/policy_assistant/ingest.py` | Download, clean, chunk, stage snapshots |
| `src/policy_assistant/retrieval.py` | Build/load persistent index, dense/hybrid retrieval, reranking |
| `src/policy_assistant/config.py`, `prompts.py`, `pipeline.py` | Provider configuration, prompts, graph and answer guards |
| `app.py` | Streamlit chat and evidence display |
| `eval/questions.json`, `eval/relevance.json`, `eval/reviews.json` | Frozen cases, evidence labels, human judgments |
| `src/policy_assistant/evaluate.py` | Run comparison, calculate metrics, generate report |
| `tests/test_ingest.py`, `test_retrieval.py`, `test_pipeline.py`, `test_evaluate.py` | Offline behavior tests using small fixtures and fake model clients |
| `README.md`, `docs/project-writeup.md`, `docs/demo-script.md`, `reports/evaluation.md` | Setup, documentation, demo, measured findings |
| `data/`, `reports/results.json` | Generated snapshots/index and raw evaluation output |

## Task 1: Reproducible public corpus

**Files:** Setup files, `sources.json`, `models.py`, `ingest.py`, `tests/test_ingest.py`.

**Interfaces:** `Source(url: str, title: str)`; `Chunk(id: str, text: str, source_url: str, section: str, section_url: str)`; `ingest(sources: list[Source], output_dir: Path) -> list[Chunk]`. Snapshot manifest records hashes and fetched-at timestamps. Package modules use the `src/` layout.

- [ ] Check local Python tooling and network access. Resolve generation endpoint/model/key availability without exposing secret values; do not claim live readiness before a successful smoke call in Task 3.
- [ ] Initialize a separate repository if needed. Create project configuration and a virtual environment. Resolve compatible dependency versions and lock the successfully installed set.
- [ ] Write failing extraction tests: a fixture containing nav, script, heading, list, and table must retain the latter three and omit nav/script; an empty main body must raise an extraction error.
- [ ] Write failing chunking tests: all chunks fit the embedding input limit, IDs are stable across repeated ingestion, and headings/source metadata survive splitting.
- [ ] Write a failed-refresh test: a failed second download leaves the prior manifest and index reference unchanged.
- [ ] Run `python -m pytest tests/test_ingest.py -q`; confirm failures exercise missing behavior.
- [ ] Implement extraction and chunking with the embedding tokenizer; stage a complete versioned snapshot before activating it. Set explicit request timeouts and fail visibly on unavailable sources. Check reuse terms and record attribution.
- [ ] Run the tests until passing; then run `python -m policy_assistant.ingest` and inspect every cleaned page for usable main content and preserved headings. Record actual acquisition dates.
- [ ] Commit this independently verifiable corpus ingestion deliverable.

## Task 2: Hybrid retrieval with a dense baseline

**Files:** `retrieval.py`, `tests/test_retrieval.py`; generated files in `data/`.

**Interfaces:** `Hit(chunk: Chunk, score: float)`; `build_index(chunks: list[Chunk], output_dir: Path) -> None`; `load_index(path: Path) -> Retriever`; `Retriever.search(question: str, mode: Literal['dense', 'hybrid'] = 'hybrid', k: int = 4) -> list[Hit]`. Index metadata records model IDs, corpus hash, and chunk configuration.

- [ ] Write failing tests using fake embeddings/reranker: exact-term BM25 retrieval adds a candidate missed by dense retrieval; duplicate IDs appear once; reranking orders the candidate union correctly; fewer than four available chunks returns that many.
- [ ] Add a stale-index test: changed corpus hashes cause a clear rebuild error rather than silently serving mismatched metadata.
- [ ] Run `python -m pytest tests/test_retrieval.py -q` and confirm expected failures.
- [ ] Implement eight candidates per channel, reciprocal rank fusion with constant 60, cross-encoder reranking, and four final chunks. Dense mode returns the top four cosine hits without BM25 or reranking. Normalize vectors and reuse loaded models.
- [ ] Persist vectors, chunks, and manifest together; replace the active index only when the complete build succeeds. Load only local generated data, without pickle.
- [ ] Run offline tests, then build the real index and manually inspect one exact-term and one paraphrase query. Measure cold model loading separately.
- [ ] Commit the working retrieval deliverable.

## Task 3: Cited answers with explicit failure paths

**Files:** `config.py`, `prompts.py`, `pipeline.py`, `tests/test_pipeline.py`.

**Interfaces:** `AnswerResult(question: str, status: Literal['answer', 'clarify', 'insufficient', 'error'], answer: str, hits: list[Hit], citation_ids: list[str], elapsed_seconds: float, error: str | None)`; `run_query(question: str, mode: Literal['dense', 'hybrid'] = 'hybrid') -> AnswerResult`. Inject a fake model and retriever in tests; construct the production dependencies once.

- [ ] Write failing tests for a supported cited answer, unknown citation, factual answer without citations, unsupported answer, malformed JSON, verifier exception, empty retrieval, ambiguous question, blank question, and unavailable provider. Assert invalid/unsupported outputs never receive `status='answer'`.
- [ ] Run `python -m pytest tests/test_pipeline.py -q` and confirm expected failures.
- [ ] Implement the fixed LangGraph path from the spec. Generation returns structured status, answer, and citation IDs; factual answer text includes inline citations. Validate both the declared IDs and inline markers against retrieved IDs. The verifier receives the exact full context given to generation. Empty evidence bypasses generation with an insufficient-evidence response.
- [ ] Prompts restrict answers to snapshot evidence, preserve policy versus advice wording, ask clarification when needed, flag relevant source conflicts, and treat instructions embedded in source documents as untrusted text.
- [ ] Validate endpoint, key, and model configuration; use bounded request timeouts. Surface runtime provider failures as errors, and verification failures as insufficient evidence. No raw exception payload or secret enters the UI/report.
- [ ] Run tests, then one real provider smoke call and one cited end-to-end query. If blocked, record the blocker and keep live evaluation pending.
- [ ] Commit the working grounded-answer pipeline.

## Task 4: Working chat interface

**Files:** `app.py`, `README.md`.

**Interfaces:** UI calls `run_query` and displays `AnswerResult`; no separate retrieval or generation logic.

- [ ] Implement chat input/history, clear-history control, four example questions, source links/excerpts matched to citation IDs, snapshot date, response time, and distinct clarification/insufficient/error displays.
- [ ] Cache dependencies across Streamlit reruns. Missing configuration or index shows actionable setup instructions and keeps the page usable.
- [ ] Document macOS/Linux environment setup, environment variables, ingestion/index build, launch, evaluation, and manual refresh commands. Do not expose implementation details unnecessarily in the employee-facing flow.
- [ ] Run `python -m streamlit run app.py`; manually check a factual answer, cross-document answer, clarification, unanswerable question, missing configuration, and chat clearing. Inspect the actual browser if available; record any unverified UI behavior.
- [ ] Commit the usable app and setup instructions.

## Task 5: Frozen 15-question evaluation and actual findings

**Files:** `eval/*.json`, `evaluate.py`, `tests/test_evaluate.py`, `reports/results.json`, `reports/evaluation.md`.

**Interfaces:** Each case has `id`, `category`, `question`, `expected_status`, `expected_facts`, and `required_source_urls`; relevance labels map case IDs to relevant chunk IDs. `retrieval_metrics(retrieved_ids: list[str], relevant_ids: set[str]) -> dict[str, float]`; `run_evaluation(mode: Literal['dense', 'hybrid']) -> list[dict]`. Human reviews record supported/total claims, correctness, citation support, and comments per case and mode.

- [ ] Before tuning, author and freeze exactly 15 cases against the real snapshot: 6 direct, 2 paraphrase, 1 exact-term, 3 cross-document, 1 ambiguous, 2 unanswerable. Review expected facts and label every relevant chunk; confirm missing answers truly are absent from the bounded corpus.
- [ ] Write metric tests: retrieved `[a,c]`, relevant `{a,b}` gives recall 0.5 and precision 0.5; empty retrieved hits gives zeros; duplicate IDs do not inflate metrics. Unanswerable cases are excluded from retrieval macro averages; zero factual claims yields undefined faithfulness rather than a fabricated perfect score.
- [ ] Run `python -m pytest tests/test_evaluate.py -q`; confirm failures, then implement the runner and report generator with per-query errors and warm latency recording.
- [ ] Run `python -m policy_assistant.evaluate --mode both`; save answers, statuses, retrieved IDs/ranks, citations, and timing for both modes on the identical snapshot. Errors remain visible in counts; do not silently drop failed requests.
- [ ] Review each substantive answer against source evidence; save actual judgments in `eval/reviews.json`. Report automatic citation validity separately from reviewed citation support and faithfulness. Mark pending judgments unreviewed.
- [ ] Generate the report with per-case recall/precision, macro scores, cross-document source coverage, answer coverage, clarification/fallback outcomes, median warm latency, and supported/total claims. State whether targets were met.
- [ ] Explain successes, failures, and likely causes with concrete examples. Record the dense-to-hybrid iteration and any subsequent change honestly; rerun only when a change or unresolved failure justifies it.
- [ ] Run the complete offline test suite and `git diff --check`; commit the evaluator and measured report.

## Task 6: Submission package and final verification

**Files:** `README.md`, `docs/project-writeup.md`, `docs/demo-script.md`, evaluation report, optional ZIP.

- [ ] Write the Google Doc-ready overview, dataset/source list, framework fields, exact prompts/instructions, architecture, actual iterations, limitations, learnings, and how AI coding tools contributed. Link the evaluation report and acknowledge the reference solution.
- [ ] Write a timed demo script: purpose/corpus (30s), architecture and AI tool use (45s), factual and cross-document live queries (90s), ambiguity and missing evidence (60s), actual evaluation findings (45s). Total 4m30s leaves recording margin.
- [ ] Verify setup instructions in the actual environment, run `python -m pytest -q` and `git diff --check`, and record commands/results. Confirm no secrets, virtual environment, or model cache enter version control or the ZIP. Check reuse terms before including snapshots.
- [ ] Produce a requirement checklist linking every Project 1 requirement to its actual artifact; leave unfinished external deliverables unchecked.
- [ ] Prepare a local ZIP or repository ready for upload. Do not claim GitHub publication before it happens.
- [ ] User records the actual live demo (at most 5 minutes), or authorizes available recording assistance. Confirm the video exists and has an accessible link.
- [ ] Place project documentation in Google Docs with user-authorized tooling or user action; confirm its shareable link.
- [ ] Upload code to GitHub when authorized (or use the permitted ZIP path), then submit the documentation, video, code, and evaluation links through the handout form. The Builder of the Week deadline is October 18, 2026, 11:59 p.m. PT; later submissions remain accepted per the handout.

## Execution handoff

Recommended approach: native execution in this session because the tasks share a small set of interfaces and the user wants a fast build. Review this checklist before implementation. API credentials and network access must be resolved early; a mocked pipeline cannot satisfy the working live bot requirement. External recording, Google Docs, publication, and form submission remain explicit final deliverables rather than assumed outcomes.
