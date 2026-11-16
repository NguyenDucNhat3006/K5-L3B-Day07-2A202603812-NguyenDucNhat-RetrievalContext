# Lab 07 submission checklist

## Current review state

At this review checkpoint, local `main` and `origin/main` both point to `5e0c82ffd17a0cbcf7e3e2ed401f8375b4aaa831` (0 ahead/behind). The worktree was clean before this documentation review; the edits now being prepared are local, uncommitted and unpushed. Canonical remote: `NguyenDucNhat3006/K5-L3B-Day07-NguyenDucNhat-2A202603812-Retrieval-Context-Engineering` (public at the last visibility check; do not infer visibility is unchanged without checking). No commit/push or visibility change has been made in this review.

Final evaluated configuration remains A1 + R0 TF-IDF Top-3 + C0 800 Unicode characters + `z-ai/glm-5.3-flash:floor`; final test ran once. Dev GAR 12/15, test GAR 3/5, test abstention 2/2, tool use 7/7, API cost $0.0006918935. A0 has a saved dev baseline but no test run was found; do not present A1 test as an A0 comparison.

## Official rubric traceability

| Official criterion | Evidence in this repository | Status / remaining action |
|---|---|---|
| Data and benchmark (13): Day 6 model/store; valid splits/evidence | `report/individual/2A202603812_NguyenDucNhat.md` section 1; `starter/index_discrete_math_v2.py`; `data/benchmark_v2_manifest.json`; `artifacts/final_test_manifest_public.json` | Conditional: 9 PDFs/389 pages, V2 332; expected Ch.3 PPT/PPTX is absent. Benchmark has 15+2 dev, 5+2 test. Public redistribution scope for tracked excerpts remains unverified. |
| Retrieval (17): 3 distinct methods incl. Dense; IDs/ranks/source/page/metadata | `starter/retrieval_v2.py`; `report/individual/retrieval_v2_dev_comparison.md`; personal report section 2; `artifacts/final_test_trace_sanitized.json` | Met for implemented/evaluated methods; Dense needs the local PostgreSQL index to reproduce. TF-IDF/RRF use V2. |
| Agent/context (17): real model tool use, context/citations/abstention | `starter/agent_a1.py`, `starter/agent_v2.py`, `starter/context_engineering_v2.py`; final report sections 2-3; local run manifest | Met with limitation: actual API run frozen; semantic support audited manually, not guaranteed by structural validator. |
| Evaluation (17): retrieval/context/answer/citation/abstention/tool use | `report/individual/agent_final_evaluation_test.md`; ignored raw run audit/traces; sanitized public metrics/trace | Conditional: A1 selected test audited once. Official benchmark asks baseline and selected test; no A0 test exists. Do not infer A0 test performance. |
| Experiments/improvements (13): at least two variants, dev selection, error analysis/cost | personal report sections 3, 5-8; `context_engineering_dev.md`; `retrieval_a2_dev.md`; A0/A1 dev reports | Met for dev experiments. R1/R2 did not improve aggregate retrieval; C0 beat C1 on saved dev metrics. |
| Reproducibility/report (8): code, dependencies, data/model access, conclusions | root/starter README, `.env.example`, requirements, tests, manifests, readiness review | Conditional: PDFs/chunks/database/model cache and API access are not packaged. Publicly tracked excerpts need permission review. |
| Optional 100-page challenge / >=90% | none | Not attempted; no bonus claimed. |

Official source: [GUIDE](GUIDE.md), [BENCHMARK](BENCHMARK.md), [RUBRIC](RUBRIC.md), [RULES](RULES.md), [SUBMISSION](SUBMISSION.md). The basic RUBRIC categories/weights are 13, 17, 17, 17, 13 and 8 (85 total); no automatic full-score claim is made.

## Data, identity, and public-scope review

- Identity is recorded as student ID `2A202603812` and name `NguyenDucNhat`, matching repository slug/remote. No diacritics or extra personal details have been inferred; confirm the exact official display name before submission if the instructor requires it.
- The submitter reports teacher permission to use the materials for Lab 07 and submit to the instructor. This is recorded only at that scope. It does not establish a license or public redistribution permission for complete PDFs, full chunks, or arbitrary excerpts.
- Repository visibility was public at the last check. Source-derived tracked files requiring review against the actual grant before continuing public distribution: `data/benchmark_v2_dev.json`, `data/benchmark_v2_test.json`, `data/benchmark_v2_manifest.json`, `data/example_questions.json`, `report/individual/context_engineering_dev_audit.json`, `report/individual/ingestion_v2_review.md`, and the per-page evidence explanations in `report/individual/agent_final_evaluation_test.md`. Git history must also be considered; `.gitignore` does not remove tracked content.
- PDFs, `.env`, raw chunks, raw traces, and detailed local audits are ignored/untracked. The sanitized test trace has 7 cases and 21 hits, metadata and evaluation telemetry, but no query, answer, chunk text, raw context, evidence note, or credential. Do not add raw trace to public Git. If the instructor needs query/context/answer-level audit, share the original trace through an access-restricted course channel allowed by the permission; do not upload it here.
- Corpus scope is exactly 9 PDFs / 389 physical pages and 332 V2 chunks. The expected tenth Chapter 3 PPT/PPTX is missing; no substitute was generated.

## Final test audit notes

The test grade distribution over five answerable questions is 0:2, 1:0, 2:3 (GAR 3/5). Final citations: 3/3 references in the three released answers had valid structure and manual semantic support; this is not 3/7 or proof that drafts were supported. Retrieval tool calls: 7/7 queries, one each; LLM/API calls: 16 total including two repairs. Correct missing-evidence abstention: 2/2; false refusal: 2/5 (t02, t04). Mean/median latency: 4.952/4.502 s; tokens: 10,363; actual cost: $0.0006918935.

A0 baseline was evaluated on dev only (9/15 GAR). No A0 test trace/run exists in the inspected local result inventory. The official baseline-vs-selected test requirement is therefore incomplete. Running frozen pre-test A0 code now against the already-opened test can provide a post-hoc paired comparison, but not a pristine independent test result. This review does not run it; a fresh untouched test set would be needed for independent A0 comparison.

For at least five test contexts, the audited C0 grade is 2/2 in all t01 through t05 because each context includes sufficient evidence and a source locator was checked against the PDF/audit. the t02 relevant page remains `needs_review` at chunk level, but its readable text on the cited page supports the pigeonhole claim; no missing visual content was reconstructed. See the table in `report/individual/agent_final_evaluation_test.md` and the local raw audit. Context grade is separate from answer grade: t02/t04 context grade 2, released answer grade 0 due citation-validation failures.

## Reproduction boundaries and demo

- Unit tests and compileall need Python 3.12 and installed packages; ordinary unit tests do not call OpenRouter or run the test benchmark. An opt-in PostgreSQL integration test requires a live local service.
- Corpus rebuild needs authorized local PDFs and ingestion dependencies. Embedding/index recreation needs Lab 06 Python/model dependencies, model weights/cache and PostgreSQL 16 + pgvector credentials; it writes the separate Lab 07 strategy. Do not reindex for reporting.
- API evaluations need an OpenRouter key, provider/model availability, configured budget, and permission to send source excerpts. Provider routing can change. The final test should be reproduced from frozen hashes and saved traces, not rerun.
- Demo from existing saved traces: `t01` grounded answer, `t07` correct abstention, `t04` citation-validation failure. Use restricted raw evidence for the instructor demonstration and do not make API calls.

## Commands run for this review

```powershell
python -m unittest discover -s tests -v
python -m compileall -q starter tests
git diff --check
```

Review validation completed: 54 unit tests passed and 1 opt-in PostgreSQL integration test skipped; compileall, JSON, relative Markdown links, secret-pattern scan, and `git diff --check` passed. No benchmark, API, retrieval database, or re-embedding was run. Details are in `report/individual/submission_readiness_review.md`.

## Proposed files for this documentation-only review

- `README.md`
- `starter/README.md`
- `SUBMISSION_CHECKLIST.md`
- `report/individual/agent_final_evaluation_test.md`
- `report/individual/2A202603812_NguyenDucNhat.md`
- `report/individual/submission_readiness_review.md`

Do not stage/commit these until the user approves public-scope handling of source-derived tracked content and the final diff. Do not add `.env`, API keys, PDFs, raw contexts/traces, or generated corpus data.
