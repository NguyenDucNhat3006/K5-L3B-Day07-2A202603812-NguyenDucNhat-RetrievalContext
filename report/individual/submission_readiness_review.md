# Lab 07 - Final submission readiness review

**Review boundary:** documentation and artifact verification only. No benchmark, retrieval database, embeddings, OpenRouter call, Git commit, or push was performed. Final evaluated source/configuration and original results are preserved.

## Executive result

The selected A1/R0/C0 evaluation is reproducibly described and its one-pass final test has 7 case traces locally. Saved results remain **Dev GAR 12/15 (80%)**, **Test GAR 3/5 (60%)**, Test correct abstention **2/2**, Test tool use **7/7**, Test cost **$0.0006918935**. The test grade distribution is 0:2, 1:0, 2:3. There is no A0 test run in the inspected local result inventory, so the official same-test baseline/selected comparison is incomplete. Do not infer an A0 test score from dev.

The workspace started clean at `HEAD=origin/main=5e0c82ffd17a0cbcf7e3e2ed401f8375b4aaa831`; the documentation changes listed below are local and uncommitted. This review makes no claim that the public GitHub repository is safe for unrestricted redistribution: instructor permission is reported for Lab 07/course submission, while public sharing of source excerpts remains unverified.

## Official requirement traceability

| Requirement and official evidence | Repository evidence | Status | Remediation / boundary |
|---|---|---|---|
| Reuse Day 6 chunks/IDs/model/store, record dimensions and connection ([GUIDE section 1, lines 3-7](../../GUIDE.md#1-chuan-bi)) | `report/individual/2A202603812_NguyenDucNhat.md` section 1; `starter/index_discrete_math_v2.py`; final public manifest configuration/hashes | **Met with data-coverage limitation** | Model is MiniLM multilingual, 384d; PostgreSQL 16/pgvector; V2 strategy separate. Corpus has 9 PDFs/389 pages; expected Ch.3 PPT/PPTX is missing. |
| At least 3 distinct retrieval methods incl. dense and traceable IDs/rank/score/source/page/metadata ([GUIDE section 2, lines 9-24](../../GUIDE.md#2-thu-cac-phuong-phap-retrieval)) | `starter/retrieval_v2.py` methods `dense`, `tfidf`, `hybrid`; `report/individual/retrieval_v2_dev_comparison.md`; final sanitized trace | **Met** | Same V2 IDs/metadata. Dense/Hybrid reproduction depends on external local DB/model setup. |
| Real model controller/tool, context, citation and missing-evidence handling ([GUIDE section 3, lines 26-32](../../GUIDE.md#3-thiet-ke-agent-va-context)) | `starter/agent_a1.py`, `starter/agent_v2.py`, `starter/context_engineering_v2.py`; final report sections 2-3 | **Met with semantic-audit limitation** | Function calling is real. Validator checks citation form/identity/source/page and context membership; semantic support is a separate human audit. |
| Split sizes, no gold in retrieval, dev selection and frozen test ([BENCHMARK section 1, lines 5-17](../../BENCHMARK.md#1-bo-cau-hoi)) | `data/benchmark_v2_manifest.json`; retrieval/A2 reports; final test manifest | **Met for selected run; coverage gap** | 15+2 dev and 5+2 test; one A1 test pass. A0 test baseline is absent, so same-test baseline/selected comparison required by [BENCHMARK section 3, lines 29-40](../../BENCHMARK.md#3-agent-va-cau-tra-loi) is incomplete. |
| Hit@1/Evidence Hit@3, context rate, latency/cost, and manual context grades ([BENCHMARK section 2, lines 19-27](../../BENCHMARK.md#2-so-sanh-retrieval-va-context)) | `report/individual/retrieval_v2_dev_comparison.md`, `context_engineering_dev.md`, final audit context table | **Met for saved dev and selected-test context audit** | t01 through t05 C0 contexts graded 2/2 each. There is no A0 test context to grade. |
| Grounded 0/1/2, citations must be in context and support answer, abstention and tool-use ([BENCHMARK section 3, lines 29-42](../../BENCHMARK.md#3-agent-va-cau-tra-loi)) | Local frozen `audit_manual.json` and trace; summary in `agent_final_evaluation_test.md`; sanitized public trace | **Met for A1; restricted raw evidence** | Test distribution 0:2/1:0/2:3; final citation references 3/3 structurally valid and manually supported among released answers; 2/5 false refusals. Full query/context/answer audit should be provided via restricted instructor channel. |
| Six basic rubric categories/weights ([RUBRIC lines 3-15](../../RUBRIC.md#phan-co-ban--85-diem)) | This table and reports linked in checklist | **Partially evidenced; no self-awarded score** | Data/benchmark 13, retrieval 17, agent/context 17, evaluation 17, experiments 13, reproducibility/report 8; total 85. This review maps evidence but does not claim maximum marks. |
| No fabrication, same corpus/questions, dev-only tuning, permitted data ([RULES lines 1-8](../../RULES.md)) | Frozen manifests/hashes, separate dev runs, permission notes; no test edits in this review | **Met with rights condition** | Teacher permission is only reported at course/submission scope. Public redistribution of individual excerpts remains to be verified. |
| Submission package includes code, 3 retrieval methods, data/rebuild access, 20 answerable +4 missing, per-query traces and 2 improvement variants ([SUBMISSION lines 17-25](../../SUBMISSION.md#danh-sach-bai-nop)) | Code, 22 questions total (15+5 answerable and 2+2 missing), two dev improvements, reports, sanitized trace; raw trace ignored | **Partial** | Public sanitized trace intentionally omits query/context/answer. If evaluator requires those fields, deliver raw trace privately under course access controls. The course benchmark minimum is met; current data-source tenth file remains absent. |
| Optional advanced 100-page/90% challenge ([RUBRIC lines 17-21](../../RUBRIC.md#thu-thach-nang-cao--15-diem)) | No separate challenge evidence | **Not attempted** | No bonus claimed. |

## Local evidence line index

Line numbers below refer to the reviewed working tree at this audit and are provided to make the code-to-claim trail quick to follow.

| Evidence area | Concrete local pointers |
|---|---|
| Dataset scope, 389 pages, 332 V2 chunks, model and permission boundary | `report/individual/2A202603812_NguyenDucNhat.md:11-17`; `README.md:5-17`; V2 settings/validation in `starter/index_discrete_math_v2.py:257-318` |
| Dense, TF-IDF, Hybrid implementations and output fields | `starter/retrieval_v2.py:80-85` result shape; `:101-119` Dense; `:120-133` TF-IDF; `:134-170` Hybrid/dispatch; CLI fields `:193-205` |
| SQL/database strategy isolation and metadata verification | `starter/index_discrete_math_v2.py:108-168`, `:272-318` |
| Context C0/C1 and budget | `starter/context_engineering_v2.py:28`, `:40-73` C0, `:88-123` C1; dev comparison `report/individual/context_engineering_dev.md:13-20,24-43` |
| A1 actual tool decision, single repair, validation and trace fields | `starter/agent_a1.py:41-145`; shared citation validator `starter/agent_v2.py:105-128`; saved dev audit `report/individual/agent_evaluation_dev.md:13-32` |
| Retrieval comparison and A2 outcomes | `report/individual/retrieval_v2_dev_comparison.md:17-38`; `report/individual/retrieval_a2_dev.md:9-42` |
| Final test automatic and manual evidence | `report/individual/agent_final_evaluation_test.md:23-83,108-154`; raw trace/metrics/audit paths listed at `:92-100` (local ignored run) |
| Personal report, identity and limitations | `report/individual/2A202603812_NguyenDucNhat.md:1-17,48-97`; `STUDENT.md:1-6` |
| Environment and reproduction instructions | `starter/README.md:1-100`; `.env.example:1-8`; `starter/requirements-ingestion-v2.txt:1-2`; `starter/requirements-indexing.txt:1-2` |
| Locked public artifact schema and run hash records | `artifacts/final_test_trace_sanitized.json`; `artifacts/final_test_manifest_public.json`; `artifacts/final_evaluation_public.json` (validated with JSON parser and cross-checked against ignored raw run) |

## Final test and context audit

The raw local run `starter/results/discrete_math_v2/agent-a1-final-test-20261116T082303799998Z/` was read without modifying it. It has 7 test cases, 21 Top-3 hits, 7 retrieval calls, 16 LLM calls (including two repair calls), 10,363 tokens, mean/median latency 4,951.95/4,501.76 ms, and actual cost $0.0006918935. There were no API transport failures. t02 and t04 ended in repair/citation validation failure; they are false refusals although evidence was present. t06/t07 abstained correctly.

| Case | C0 length / 800 | Context locators | Context grade | Answer grade / finding |
|---|---:|---|---:|---|
| t01 | 604 | Ch.1 p.27, p.26 | 2 | 2; answer and citation supported |
| t02 | 747 | Ch.2 p.36, p.33 | 2 | 0; p.36 chunk has `needs_review`, but relevant readable text on audited PDF page is sufficient; citation validation rejects answer/repair |
| t03 | 694 | Ch.3 p.45, p.44 | 2 | 2; answer supported by page text |
| t04 | 678 | Ch.5 part 1 p.39, p.37 | 2 | 0; context is sufficient, uncited follow-up remains after repair |
| t05 | 787 | Ch.5 part 2 p.30; Ch.6 p.4, p.24 | 2 | 2; cited source/page supports answer |

Context grade distribution for t01 through t05 is 0:0, 1:0, 2:5. Answer-grade distribution is 0:2, 1:0, 2:3 (mean 1.2/2). Context sufficiency is not answer quality. `needs_review` stays attached to the t02 source chunk; this audit only confirms that its readable relevant text supports this particular answer, without reconstructing any missing figure/table.

### A0 test gap and independence

The local result inventory contains baseline/A0 dev results and one final test run, which is A1. No A0 test trace/run was found. The selected A1 test was run once and is preserved. Running frozen pre-test A0 code on those same test questions now would be a post-hoc descriptive comparison because the questions/results have already been opened; it cannot be presented as a pristine independent baseline test. To obtain an independent comparison, freeze A0 and A1 and evaluate both on a new untouched test set with criteria locked in advance. This review does not run either option.

### Sanitized evidence package

`artifacts/final_test_trace_sanitized.json` parses as JSON and has the matching final-test run ID, 7 cases, 21 retrieval hits and structured metadata/tool/citation/usage/latency/cost fields. It omits query text, answer text, chunk text, raw context, evidence notes, free-form arguments and secrets. Its case/hit and aggregate counts match the raw run; `final_test_manifest_public.json` records source and raw-artifact hashes. Since sanitized trace cannot prove semantic support without answer/context text, the manual PDF audit remains documented separately and raw audit remains restricted/local.

`SUBMISSION.md` asks for query, context and answer per case. Use the complete local trace only through a restricted LMS/course submission area if the teacher requires those materials and the permission covers them. Do not upload raw source-derived traces to the public GitHub repository by default.

## Experiments and failure analysis

- **A0 to A1 (dev only):** GAR improved from 9/15 to 12/15 and false refusal decreased from 6/15 to 3/15 under the same model/retrieval/context. The A1 JSON and per-claim citation instructions fixed d04/d06/d13 dev outcomes; d01/d03 remained retrieval misses and d14 remained a citation repair failure. Repair is not credited as the cause of all gains. A0 test is missing.
- **A2 R0/R1/R2:** R1 query expansion and R2 candidate expansion/reranking did not improve aggregate dev metrics over R0; R2 moved d14 ranking but did not resolve d01/d03 overall. R0 was retained for simplicity.
- **C0/C1:** Saved dev audit rates C0 above C1 (context evidence 13/15 vs 12/15; mean context quality 1.733 vs 1.667 on 0-2 scale). C0 is the selected 800-character configuration.
- **Test degradation:** GAR is 80% dev versus 60% test on a very small answerable sample; one question changes test GAR by 20 percentage points. t02/t04 show the difference between adequate retrieved context and successful citation-validated output.
- **Known limits:** 332 chunks from 9 PDFs/389 pages, missing expected Ch.3 PPT/PPTX; 256 chunks flagged `needs_review`; extraction may lose formula, matrix, table or graph structure. TF-IDF Vietnamese tokenization is simple. Semantic citation validation is manual. No 100-page advanced challenge. Permission is scoped; no redistribution license is claimed.

## Source and repository access

Instructor permission is reported for use in Lab 07 and submission to the instructor. It does not establish public rights to complete PDFs or all excerpts. The public repository has tracked source-derived artifacts to review against the exact permission scope:

- `data/benchmark_v2_dev.json`, `data/benchmark_v2_test.json`, `data/benchmark_v2_manifest.json`
- `data/example_questions.json`
- `report/individual/context_engineering_dev_audit.json`
- `report/individual/ingestion_v2_review.md`
- `report/individual/agent_final_evaluation_test.md` (page-level evidence descriptions)

No original PDFs, `.env`, or API key should be added. `.gitignore` does not remove already tracked files or historical revisions. The public sanitized trace is designed to avoid raw text, but public scope for any document-derived metadata should still be checked. The latest visibility previously checked was public; verify visibility again before submission. No public redistribution permission or source license is asserted here.

## Reproducibility boundaries

From tracked files, one can inspect code, tests, sanitized results, hashes and instructions. Rebuilding the dataset requires locally available authorized PDFs and the V1/V2 input workflow; the expected tenth PPT/PPTX is missing. Recreating vectors/retrieval requires PostgreSQL 16 + pgvector and the Lab 06 Python environment/model cache; it writes the Lab 07 index, so it was not done during this review. A new agent run also needs `.env`, an OpenRouter key, provider availability, budget and external-use permission. Historical final test reproducibility is through the frozen manifest and raw trace, not by re-running it.

## Demo for evaluator (saved artifacts only)

1. Use t01 to show a grounded answer and matching citation.
2. Use t07 to show a correct abstention when the requested detail is not evidenced.
3. Use t04 to show a real citation/repair failure despite sufficient context.

Use the restricted trace for query/answer/context detail if required. Do not call the API or rerun benchmark during demo.

## Files changed in this local review

- `README.md` - corrected Day 07 identity/scope, results and links.
- `starter/README.md` - architecture, setup, safe command boundaries and reproducibility requirements.
- `SUBMISSION_CHECKLIST.md` - current Git checkpoint, rubric mapping, data permission, trace access and A0 gap.
- `report/individual/agent_final_evaluation_test.md` - context/answer grade distributions, per-case telemetry, A0 gap, trace scope and demo.
- `report/individual/2A202603812_NguyenDucNhat.md` - A0 test gap and semantic-vs-structural citation precision.
- `report/individual/submission_readiness_review.md` - this audit.

These are proposed documentation-only commit candidates; none have been staged. Do not commit/push until the user reviews public-scope implications and approves the diff.

## Checks performed

Pending execution at time of writing: unit tests, compileall, Markdown links, JSON parsing, secret scan, `git diff --check`, and final Git status. Results will be appended after those checks. No benchmark, API, database, or re-embedding run is permitted in this review.
