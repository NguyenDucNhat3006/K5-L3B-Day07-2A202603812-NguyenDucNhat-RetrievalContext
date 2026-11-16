# Lab 07 - Retrieval & Context Engineering

This repository contains the Day 07 Discrete Math retrieval and agent submission for the L3B repository. It reuses the Day 06 MiniLM embedding model and pgvector setup, with a separate Lab 07 corpus/index strategy.

## Final evaluated configuration

- Corpus: Discrete Math V2, 332 chunks from 9 PDFs / 389 physical pages. The expected tenth Chapter 3 PPT/PPTX is not present and was not reconstructed.
- Embeddings: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensions; PostgreSQL 16 + pgvector, cosine distance, strategy `D07_discrete_math_v2`.
- Retrieval methods compared on dev: Dense pgvector, TF-IDF, and Hybrid RRF over the same chunk IDs and metadata. A2 R1 query expansion and R2 candidate expansion/reranking did not improve the overall dev baseline; TF-IDF R0 was retained.
- Context: C0 preserves TF-IDF Top-3 order within 800 Unicode characters. C1 was compared offline; C0 had better saved dev context coverage/quality.
- Agent: A1 uses actual OpenRouter function/tool calling for TF-IDF retrieval, citation validation, and at most one repair. Citation format validation and semantic source support are scored separately.

| Split | Grounded answer | Correct abstention | Tool use | Actual API cost |
|---|---:|---:|---:|---:|
| Dev (17; 15 answerable) | 12/15 (80%) | 2/2 | 17/17 | $0.0013042941 |
| Test (7; 5 answerable), one pass | 3/5 (60%) | 2/2 | 7/7 | $0.0006918935 |

Final test also used 16 LLM calls (including two repairs), 10,363 tokens, and mean/median latency 4.952/4.502 seconds. The A1 final test was run exactly once. Do not rerun it or use its outcomes to tune the configuration. See [the per-case audit](report/individual/agent_final_evaluation_test.md), [sanitized trace](artifacts/final_test_trace_sanitized.json), and [public manifest](artifacts/final_test_manifest_public.json). The complete raw trace remains local-only. Restricted A0/A1 instructor copies are prepared under `.private_submission/`; the A1 manifest copy redacts account-specific spending fields. The directory is excluded by the repository-root `.gitignore` rule and this worktree's `.git/info/exclude`, so these copies are not tracked or public artifacts. The reported permission covers course use and submission to the instructor; it does not establish public redistribution rights for PDFs or arbitrary excerpts.

A separate A0 retrospective pass on the already-opened test completed once: GAR 0/5, correct abstention 2/2, tool use 7/7, 14 calls, 7,049 tokens, and $0.0004882121 actual cost. It is not an independent evaluation and does not change A1's official 3/5 test GAR. See the [A0/A1 audit and comparison](report/individual/agent_a0_retrospective_test.md); raw A0 traces and audit remain in the Git-ignored `starter/results/` run directory, with a separate restricted instructor copy under `.private_submission/`.

## Setup and commands

See [starter setup and reproducibility guide](starter/README.md) for Python 3.12, package groups, environment variables, PostgreSQL, ingestion, retrieval, agent, and evaluation commands. Unit tests do not call the LLM or run the benchmark:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q starter tests
```

Live retrieval requires the Lab 06 Python environment, PostgreSQL 16 with pgvector, and the local V2 chunk file. LLM calls additionally need an OpenRouter key and explicit permission for external corpus use. The saved final test must not be rerun.

The submission materials document work toward the maximum **85 basic rubric points**; this is a preparation target, not an awarded or claimed score.

## Experiment reports

- [Personal report](report/individual/2A202603812_NguyenDucNhat.md)
- [Dense, TF-IDF, and Hybrid RRF dev comparison](report/individual/retrieval_v2_dev_comparison.md)
- [C0/C1 context engineering](report/individual/context_engineering_dev.md)
- [A1 agent dev evaluation](report/individual/agent_evaluation_dev.md)
- [A2 R0/R1/R2 dev comparison](report/individual/retrieval_a2_dev.md)
- [Final test audit and case telemetry](report/individual/agent_final_evaluation_test.md)
- [A0 retrospective test evaluation and audit](report/individual/agent_a0_retrospective_test.md)
- [A0 retrospective plan and execution record](report/individual/a0_retrospective_test_plan.md)
- [Submission readiness review](report/individual/submission_readiness_review.md)

## Data and permission scope

The submitter reports that the instructor authorized using the course documents for Lab 07 and submission to the instructor. This does **not** establish permission to publicly redistribute complete PDFs, all extracted chunks, or arbitrary excerpts. The GitHub repository is public and source-derived evidence is present in tracked benchmark/audit artifacts; those files and their public scope still require confirmation. Original PDFs and raw traces are not tracked. See [submission checklist](SUBMISSION_CHECKLIST.md) and [submission readiness review](report/individual/submission_readiness_review.md). No source license or blanket redistribution permission is claimed. PDF extraction can lose formula, matrix, table, and diagram structure; chunks marked `needs_review` must not be treated as reconstructed visual evidence.

## Submission references

- [Personal report](report/individual/2A202603812_NguyenDucNhat.md)
- [Submission checklist](SUBMISSION_CHECKLIST.md)
- [Official GUIDE](GUIDE.md) | [BENCHMARK](BENCHMARK.md) | [RUBRIC](RUBRIC.md) | [RULES](RULES.md) | [SUBMISSION](SUBMISSION.md)
