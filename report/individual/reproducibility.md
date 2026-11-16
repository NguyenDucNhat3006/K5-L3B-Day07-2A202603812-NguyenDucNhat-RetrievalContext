# Reproducibility and submission evidence

This document consolidates reproducibility instructions, provenance, rubric evidence, and data-sharing limits. It records the work completed toward the maximum 85 basic rubric points; it is not a score or claim of an awarded 85/100.

## Frozen dataset and benchmark

- Corpus: Discrete Math V2, 332 chunks from 9 PDFs / 389 physical pages. The expected tenth source (Chapter 3 PPT/PPTX) is absent.
- Embeddings: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, 384 dimensions. PostgreSQL 16 + pgvector, cosine similarity, separate strategy D07_discrete_math_v2.
- Locked benchmark: 15 answerable + 2 evidence-missing dev questions; 5 answerable + 2 evidence-missing test questions. Test was run once for official A1; later A0 test run is explicitly retrospective.
- Hash references: data/benchmark_v2_manifest.json; artifacts/final_test_manifest_public.json; A0 run manifest and full artifacts are local under ignored starter/results/discrete_math_v2/agent-a0-retro-test-20261116T151349722949Z/.
- Public A1 artifacts: artifacts/final_test_trace_sanitized.json, artifacts/final_test_manifest_public.json, artifacts/final_evaluation_public.json. The sanitized trace omits question, answer, chunk text and raw context; the complete trace remains restricted.

## Official basic rubric evidence map (85 points)

| Criterion and official point split | Evidence | Status and verification limit |
|---|---|---|
| Data and benchmark - 13 (6 Day 6 connection/model/source; 7 questions/evidence/splits) | Main report, starter/index_discrete_math_v2.py, data/benchmark_v2_manifest.json | Partial: corpus and splits are documented; expected tenth PPT/PPTX is missing. Public excerpt rights remain unverified. |
| Retrieval - 17 (10 distinct methods including Dense on Day 6 vector store; 7 configuration/source/score/rank/error handling) | starter/retrieval_v2.py; experiments.md retrieval comparison; sanitized trace | Implemented and evaluated on dev. Dense/Hybrid reproduction requires local PostgreSQL/model setup. |
| Agent and context - 17 (9 real-model tool/controller trace and stop conditions; 8 context/citation/missing-evidence handling) | starter/agent_a1.py, starter/agent_v2.py, starter/context_engineering_v2.py; evaluation.md | Real OpenRouter tool calling and C0 are evidenced. Semantic support is manually audited, not inferred from structural citation validity. |
| Evaluation - 17 (9 retrieval/context metrics; 8 answer grades/citation/abstention/tool audit) | experiments.md; evaluation.md; public sanitized artifacts; restricted raw audits | A1 official test audit is complete. A0 comparison is retrospective, not independent. Raw query/context/answer evidence is restricted. |
| Experiments and improvements - 13 (5 variants/hypotheses/failure analysis; 5 dev selection and frozen-test evaluation; 3 quality/latency/cost) | experiments.md; evaluation.md | Dev experiments and one official A1 test are documented. A0 retrospective must not be presented as held-out or causal evidence. |
| Reproducibility and report - 8 (5 code/run/model/data instructions; 3 conclusions/sources/limitations) | README.md, starter/README.md, this report, manifests and tests | Partial: local PDFs, DB/model cache, and provider access are not packaged. No source license or blanket public redistribution right is asserted. |

No category is self-awarded. The optional Advanced Challenge is not being pursued and no bonus is claimed.

## Run configuration and reproduction boundaries

Final configuration: Agent A1, R0 TF-IDF Top-3, C0 at most 800 Unicode characters, model z-ai/glm-5.3-flash:floor through OpenRouter, corpus V2 with 332 chunks. Official A1 dev GAR is 12/15; official test GAR is 3/5. A0 retrospective test GAR is 0/5 and must remain separately labeled as retrospective.

Install and run instructions are in starter/README.md. The standard offline verification commands are:

    python -m unittest discover -s tests -v
    python -m compileall -q starter tests
    git diff --check

Unit tests use mocks; the optional live PostgreSQL integration test requires RUN_LIVE_V2_TESTS=1 and a configured local service. Rebuilding requires the authorized local PDFs and ingestion dependencies. Recreating the vector index requires the Lab 06 environment/model cache and PostgreSQL 16 + pgvector. No re-indexing is required to inspect saved reports. Do not rerun the locked A1 test or the A0 retrospective run.

Two engineering scripts write standalone audit Markdown outputs at their historical output paths: starter/improve_discrete_math.py writes report/individual/ingestion_v2_review.md and starter/index_discrete_math_v2.py writes report/individual/v2_index_smoke.md. Their complete saved reports are consolidated in experiments.md. Those output files are not source inputs or import dependencies; rerunning those scripts would regenerate them. This cleanup does not alter or run either script.

## Evidence navigation

| Evidence | Location |
|---|---|
| Personal submission and dataset summary | 2A202603812_NguyenDucNhat.md |
| Ingestion/chunking audit and V2 index smoke details | experiments.md, sections "Ingestion V1 to V2 audit" and "V2 index validation and smoke retrieval" |
| Dense, TF-IDF, Hybrid, C0/C1, A2 and agent dev comparisons | experiments.md |
| A0 retrospective protocol, hashes, per-case audit, and A1 final test audit | evaluation.md |
| Public sanitized trace and frozen A1 manifest | ../../artifacts/final_test_trace_sanitized.json and ../../artifacts/final_test_manifest_public.json |
| Retrieval implementation and index isolation | ../../starter/retrieval_v2.py and ../../starter/index_discrete_math_v2.py |
| Agent/tool/citation validation | ../../starter/agent_a1.py and ../../starter/agent_v2.py |

For an evaluator walkthrough using saved evidence only, use t01 for a supported answer, t07 for a correct abstention, and t04 for a citation-repair failure. Do not call the API or rerun a benchmark.

## Code and evidence map

| Requirement area | Implementation/evidence |
|---|---|
| Dataset, source metadata, IDs and page provenance | Main report; starter/index_discrete_math_v2.py; data/benchmark_v2_manifest.json |
| Dense, TF-IDF, Hybrid and canonical result fields | starter/retrieval_v2.py; experiments.md section on retrieval comparisons |
| SQL strategy isolation and indexing validation | starter/index_discrete_math_v2.py; experiments.md section on V2 index validation |
| C0/C1 packing and character budget | starter/context_engineering_v2.py; experiments.md context section |
| Real controller/tool calls, citation checks and bounded repair | starter/agent_a1.py; starter/agent_v2.py; evaluation.md |
| Benchmark schema and no-gold retrieval boundary | data/benchmark_v2_dev.json, data/benchmark_v2_test.json, data/benchmark_v2_manifest.json |
| Public frozen test evidence | artifacts/final_test_trace_sanitized.json; artifacts/final_test_manifest_public.json; artifacts/final_evaluation_public.json |

## Restricted trace packages

Local instructor copies are under .private_submission/ and excluded by the root .gitignore. Raw run traces, contexts, metrics and manual audits under starter/results/ are also ignored. Do not commit those files. They contain document-derived content and should be shared only over a restricted course channel covered by the instructor's permission.

The public sanitized A1 trace is not equivalent to the raw trace and does not expose semantic context. Public artifacts already contain source-derived benchmark/audit material, including data/benchmark_v2_dev.json, data/benchmark_v2_test.json, data/benchmark_v2_manifest.json, data/example_questions.json, report/individual/context_engineering_dev_audit.json, report/individual/ingestion_v2_review.md in Git history, and page-specific evidence descriptions now in evaluation.md. The repository is public. Permission to use and submit documents for class does not establish public redistribution permission for PDFs, chunks, or excerpts. Confirm the exact scope before further public distribution. No license is inferred.

No original PDF, .env, API key, raw trace, or private package is intended for Git.

## Provenance and limitations

- A1 frozen manifest records configuration, source/prompt/benchmark hashes, limits, and local artifact hashes. The A1 raw run remains unchanged; public artifacts are sanitized summaries.
- A0 retrospective manifest records pre-call source/configuration hashes and output hashes. A0 prompt/tool hashes match the recovered historical revisions, but exact original A0 dev runner/API adapter provenance cannot be proven because the old dev manifest did not record source hashes.
- A0 retrospective test used the already-opened test questions. Its 0/5 GAR is descriptive only, not an independent baseline, held-out evaluation, or causal comparison.
- PDF text extraction can lose formula, matrix, table, and diagram structure. V2 preserves needs_review flags and does not reconstruct missing visual information. The absent tenth Chapter 3 PPT/PPTX was not replaced.
- Exact student name with diacritics cannot be verified from repository metadata; STUDENT.md uses the repository-verified spelling and MSSV.
- Public visibility and any source-derived excerpt rights are separate questions. Existing tracked data must be reviewed against the permission actually granted.

## Current cleanup scope

The ten original Final Review files were pushed as 32be445a2d09b78cff796e4266144f800ae15bd2. Post-push consistency documentation was subsequently pushed as faf902020bcedd490bc8a731f9bea1436285e116. This cleanup began from synchronized HEAD=origin/main at faf902020bcedd490bc8a731f9bea1436285e116 with a clean worktree. This consolidation is local only; it does not commit, push, change visibility, alter Git history, or modify experimental artifacts.
