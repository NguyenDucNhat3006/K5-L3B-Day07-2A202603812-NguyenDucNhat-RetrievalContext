# Lab 07 - Retrieval and Context Engineering

L3B Lab 07 submission for Discrete Math. This repository reuses the Lab 06 MiniLM embedding model and pgvector stack with an isolated V2 strategy.

## Frozen evaluation snapshot

| Run | Grounded answer | Correct abstention | Tool use | API cost |
|---|---:|---:|---:|---:|
| A1 dev (17 questions; 15 answerable) | 12/15 (80%) | 2/2 | 17/17 | $0.0013042941 |
| A1 official test (7; 5 answerable), one pass | 3/5 (60%) | 2/2 | 7/7 | $0.0006918935 |
| A0 test retrospective (same opened split) | 0/5 | 2/2 | 7/7 | $0.0004882121 |

A0 is not an independent held-out evaluation and does not change the official A1 result. See the evaluation report for the paired descriptive comparison.

## System and corpus

- Corpus: Discrete Math V2, 332 chunks from 9 PDFs / 389 physical pages. The expected tenth Chapter 3 PPT/PPTX is absent.
- Embeddings: paraphrase-multilingual-MiniLM-L12-v2, 384 dimensions; PostgreSQL 16 + pgvector, cosine similarity, strategy D07_discrete_math_v2.
- Compared Dense pgvector, TF-IDF and Hybrid RRF on dev. TF-IDF Top-3 R0 was selected.
- Agent A1 uses OpenRouter tool calling and citation validation with at most one repair. Context C0 is limited to 800 Unicode characters.
- PDF extraction can lose formula, table, matrix and diagram structure; needs_review content is not reconstructed.

## Reports

- [Personal report](report/individual/2A202603812_NguyenDucNhat.md)
- [Experiments: ingestion, retrieval, context, and dev agent runs](report/individual/experiments.md)
- [Evaluation: A0 retrospective and A1 official test](report/individual/evaluation.md)
- [Reproducibility, rubric evidence, and data scope](report/individual/reproducibility.md)
- [Submission checklist](SUBMISSION_CHECKLIST.md)
- [Student record](STUDENT.md)
- [Starter setup and commands](starter/README.md)
- [Official GUIDE](GUIDE.md) | [BENCHMARK](BENCHMARK.md) | [RUBRIC](RUBRIC.md) | [RULES](RULES.md) | [SUBMISSION](SUBMISSION.md)

The reports document work toward the maximum 85 basic rubric points; no awarded score is claimed.

## Verification

Install the package groups described in starter/README.md, configure the local PostgreSQL connection as needed, then run:

    python -m unittest discover -s tests -v
    python -m compileall -q starter tests

The unit tests do not call the LLM or run a benchmark. The locked A1 test must not be rerun.

## Data permission

The reported instructor permission covers course use and submission to the instructor; it does not establish public redistribution rights for PDFs, chunks, or arbitrary excerpts. The GitHub repository is public and existing tracked artifacts include source-derived content. Review reproducibility.md before further public distribution. Original PDFs, raw results, and .private_submission/ are ignored by Git. The private A0/A1 packages are for a permission-appropriate restricted course channel only.
