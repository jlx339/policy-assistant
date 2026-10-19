# Policy Assistant Demo Script

Target duration: 4 minutes 30 seconds. Record only after live inference and evaluation work. Replace pending metrics with actual measured results before recording; never present targets as results.

## 0:00–0:30 Purpose and corpus

“This assistant helps a new remote employee find equipment, spending, and security guidance in four public GitLab handbook pages. It answers from a dated snapshot and shows the passages behind its claims.” Show the source list and snapshot date.

## 0:30–1:15 Architecture and AI coding tools

Show the architecture diagram. Explain cleaning, section-aware chunks, local embeddings, BM25 plus vector search, cross-encoder reranking, and LangGraph's generation/verification flow. Explain that Codex helped with planning, code, tests, and evaluation scaffolding, while source checks and real evaluation determine the outcome. Mention that malformed citations or failed verification trigger a fallback.

## 1:15–2:45 Two live answers

Ask: “What device evidence must I provide to IT Ops before finishing onboarding?” Show the answer's citation and actual supporting passage.

Ask: “Where should I ask about a home office purchase, and what general deadline applies when I submit the expense claim?” Show evidence from both equipment and spending pages. If a query fails, show the failure honestly and explain the report finding instead of substituting a fabricated success.

## 2:45–3:45 Edge cases

Ask: “Tell me about the policy.” Show a clarification request.

Ask: “What is the exact home office stipend amount for a new hire in Canada?” Explain why a public page pointing to internal details cannot justify an amount. Show the insufficient-evidence outcome.

## 3:45–4:30 Evaluation and learning

Show the actual 15-question report. State measured dense-versus-hybrid recall and precision, reviewed faithfulness and coverage, error count, and latency. Show one concrete retrieval success and one failure with its cause. Explain that citation IDs alone do not prove support. End with the repository link and the main learning about grounded answers and corpus boundaries.

## Recording checklist

- Model endpoint and real index are working; no mocked pipeline is used.
- All demonstrated queries are live, and snapshot dates are visible.
- API keys and environment values are hidden.
- Evaluation report contains actual results and reviewed judgments.
- Recording is at most five minutes and has an accessible share link.
