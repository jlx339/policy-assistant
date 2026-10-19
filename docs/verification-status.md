# Human review confirmed — October 18, 2026

The project owner confirmed reviewing and agreeing with all draft answer judgments, including the flagged failures. The approved 30 entries are stored in eval/reviews.json and bound to the actual answers by hash. Regenerating the report produced confirmed faithfulness of 26/29 = 89.66% for dense and 18/22 = 81.82% for hybrid. Correctness among returned answers is 9/12 = 75.00% and 7/11 = 63.64%. Neither method meets the 95% faithfulness target. Earlier references to pending human review below are historical and superseded.

---

# Completed live evaluation — October 18, 2026

Thirty scored queries completed: 15 dense and 15 hybrid, no service errors. Both methods measured 95.83% recall@4 and 37.50% precision@4. Dense answered 12/12 answerable queries, hybrid 11/12; median warm latency was 1.48s and 2.16s respectively. Actual outputs and model/snapshot metadata are in reports/results.json. See reports/evaluation-analysis.md for substantive failures that the runtime verifier missed.

Codex source review of all outputs is prepared separately from the official human review file. Human-reviewed faithfulness and correctness remain undefined. No video, Google Doc publication, or final course-form submission has occurred.

---

# Latest verification — October 18, 2026

The current suite passes **58 tests**, including real cached model inference, the LangGraph flow, UI citation formatting, structured claim rendering, rate-limit classification, and interrupted-evaluation checkpoint/resume behavior. Run:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false RUN_MODEL_TESTS=1 .venv/bin/python -m pytest -q
```

Live calls run in the user's network-enabled terminal. The latest home-office lookup returned the correct Compass / expenses@gitlab.com answer with its evidence citation. Prior batch checks returned answers for laptop security, public computers, and travel, plus clarification for the vague policy question; these are smoke checks rather than a full reviewed benchmark. Subsequent structured-output changes still require full evaluation.

Actual retrieval comparison is saved in `reports/retrieval-comparison.json`: dense and hybrid both achieved 95.83% macro recall@4 and 37.5% precision@4 across the 12 answerable cases. Q11 missed the personal-use permission passage in both modes. No hybrid improvement or reviewed faithfulness result is claimed.

The evaluator now waits 65 seconds between questions and checkpoints every result. Resume with `--resume`; changes to the snapshot, questions, model, requested modes, or pipeline invalidate resume. The complete live run and independent answer review remain outstanding.

The following entries are historical and superseded where they describe dependencies, models, or smoke tests as unavailable.

---

# Latest search fix

The real reranker model is downloaded. Its float32 CPU inference returned NaN scores on this Mac (torch 2.14.1, transformers 5.20.1, sentence-transformers 5.7.0). Model parameters were finite; changing attention implementations did not resolve the issue. Converting the macOS CPU reranker to float64 produced finite scores and ranked the correct onboarding evidence first. The change affects reranking only and does not require rebuilding the embedding index.

A real cached-model regression first failed on NaN scores, then passed after the fix. The complete suite with that integration enabled passed all 47 tests:

```bash
RUN_MODEL_TESTS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false .venv/bin/python -m pytest -q
```

The actual Pipeline.retrieve call now succeeds on the user's onboarding question and returns ca17f2d61c1584a3 first. Restart Streamlit to discard the previously cached float32 model. Float64 may increase reranking memory and latency; full live-query timing remains to be measured. Provider generation is still unverified from the sandbox due to network restrictions.

---

# Verification Status

Dependencies and the public corpus are now installed. All 46 tests pass, including LangGraph integration. The active snapshot has 68 chunks; the largest final input is 202 tokens, safely within the embedding model limit. The warning about a 754-token section arose during pre-split tokenization, not embedding of an oversized final chunk.

A real dense-only retrieval baseline was run on the acquired snapshot: macro recall@4 95.83% and precision@4 37.5% across the 12 answerable cases. Results are in reports/retrieval-baseline.json. No generated answers, hybrid reranking quality, or faithfulness are measured by this baseline. Source-reviewed labels cover all 15 questions and bind to the snapshot and question hashes; review was performed by Codex, not a human sign-off.

Groq configuration values are present without exposing credentials. The provider smoke call fails with OpenAIConnectionError because this sandbox cannot resolve external hosts. The embedding model is cached; an offline load confirms the reranker still requires its first download. Final project acceptance remains pending those live checks.

The following sections record the earlier offline implementation phase; the status above supersedes their initial dependency/snapshot blockers.

## Checks performed

- Python 3.11.17 virtual environment created in this repository.
- Offline component and Streamlit AppTest suite: 45 passed, 1 skipped after the final review fixes. The skipped test is the actual LangGraph orchestration integration; that dependency is unavailable.
- Source compilation: `python -m compileall -q src app.py` passed.
- Setup script syntax: `bash -n scripts/setup.sh` passed.
- Case schema: exactly 15 distinct cases with the agreed category distribution validated.
- Git whitespace check: `git diff e1c1739..HEAD --check` passed.
- Evaluation CLI correctly exits unsuccessfully with a missing-index explanation; no synthetic quality result is emitted.

The test virtual environment temporarily reads existing cached pytest/NumPy/Streamlit packages from another project's environment through an ignored local `.pth` file. That other project was not changed. This is sufficient for offline behavior checks, not evidence of a successful clean install. `scripts/setup.sh` removes the cached-package link before installing the real dependency set. A separate ignored source-path `.pth` allows local CLI checks before editable package installation.

## External blockers

Shell requests to the GitLab handbook fail DNS resolution. Dependency installation from PyPI also fails DNS resolution, and the full embedding, reranking, and LangGraph dependencies are not cached. No generation provider has been configured in this project. Browser-based source inspection was possible, but it is not a local downloaded snapshot and does not establish real retrieval results.

A network-enabled terminal must run `bash scripts/setup.sh`, configure `.env`, and follow the ingestion/index and evaluation-labeling steps in README.md. After installation, run the full test suite and confirm the LangGraph test no longer skips.

## Design rulings

- Create an independent repository on `feat/policy-assistant` instead of a linked worktree: no existing app checkout needed protection, and the supplied reference repository stays untouched. The cost of changing this later is relocating the workspace.
- Use standard-library HTML extraction and a compact tested BM25 scorer instead of BeautifulSoup/rank-bm25: preserve planned behavior while reducing unavailable dependencies. Broader HTML patterns may need extraction adjustments.
- Reuse read-only cached packages for offline tests while downloads are blocked. The cost is that a full reproducible installation and lock remain pending.
- Combine retrieval and reranking in one LangGraph node because the retriever owns both operations. The cost is less granular graph tracing.

## Code review and regression fixes

A separate read-only reviewer examined the implementation and independently reproduced four important issues. Each was reproduced with a failing test before the fix, followed by the passing suite:

- Stale evaluation reviews could certify changed answers. Reviews now require a hash bound to the actual question, answer, status, expected facts, and full evidence.
- Index building could activate vectors for chunks different from the staged corpus. It now validates persisted content, the corpus hash, unique IDs, and staged identity before activation.
- A non-string model status could raise an exception instead of falling back. Status types are now validated before set membership.
- Navigation expressed as an ARIA role could be indexed as content. Extraction now excludes navigation and related boilerplate roles and containers.

The reviewer found no separate minor issues. Real corpus extraction quality, provider compatibility, LangGraph runtime integration, and real RAG quality remain unverified because external dependencies and network are unavailable. Those are acceptance work, not waived checks.

## Remaining acceptance work

Acquire and inspect the real pages, download model weights, activate the index, configure and smoke-test generation, exercise live UI queries, freeze source-reviewed labels, run both retrieval modes on the same 15 questions, independently review the actual answers, and complete measured success/failure analysis. Then finish the Google Doc, real demo recording, code publication/ZIP delivery, and form submission.

No external publication or submission has occurred. The current report is an explicit pending-evaluation status file, not the required final scored report.
