# Lab 07 starter: ingestion, retrieval, context, and agent

Run the commands from the repository root unless a command explicitly changes directory. This is the implementation guide for the L3B Day 07 submission. Use Python 3.12 for V2 preparation/tests and the Lab 06 environment for model embeddings and PostgreSQL access. All commands below are examples; **the final test command is deliberately omitted** because that locked test was already run once.

## Architecture and data

- Ingestion: 9 source PDFs, 389 physical pages; V1 has 420 chunks and reviewed V2 has 332. The expected Chapter 3 PPT/PPTX tenth source file is absent. V2 preserves chunk/source IDs, source path, page, and metadata (`subject`, `chapter`, `content_type`, `extraction_quality`).
- Embeddings: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensions. V2 is stored in PostgreSQL 16 + pgvector with cosine distance under `D07_discrete_math_v2`; Lab 06 A/B strategies are separate.
- Retrieval: Dense pgvector, TF-IDF, and Hybrid Reciprocal Rank Fusion (RRF) share the 332 V2 chunks and citations. C filtering is SQL-level in the Dense implementation where used. TF-IDF is local lexical ranking.
- Context: C0 takes the original TF-IDF Top-3 in rank order up to 800 Unicode characters. C1 is evidence-aware packing from the same retrieved candidates. Saved dev comparison favored C0; A2 R1/R2 did not improve aggregate dev retrieval, so the frozen agent uses R0/C0.
- Agent: A1 uses OpenRouter chat function calling. The model decides to invoke `search_discrete_math`; that tool runs TF-IDF Top-3 and C0. Citation structure is validated against context chunk IDs/source/pages; semantic entailment requires human source audit. One repair maximum reuses the same context.

## Environment and setup

Create the Python 3.12 environment and install the ingestion/test dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r starter/requirements-ingestion-v2.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The separate `requirements-indexing.txt` is for the established Lab 06 indexing environment compatibility path. Indexing and Dense/Hybrid retrieval also require the Lab 06 Python environment with `sentence-transformers`, `psycopg`/pgvector and its local model cache, plus PostgreSQL 16 with pgvector. Database settings are read by the shared Lab 06 configuration; see `starter/index_discrete_math_v2.py` and the Lab 06 setup. The V2 corpus JSON and original PDFs are local/ignored inputs; Git alone cannot recreate them. No database dump or model weights are included.

Configure `.env` locally from [`.env.example`](../.env.example); do not commit it. `OPENROUTER_API_KEY`, `LAB07_LLM_MODEL`, `LAB07_LLM_BASE_URL`, input/output price estimates, and `LAB07_EXTERNAL_CORPUS_OK` control a new API evaluation. `OPENROUTER_API_KEY` and `LAB07_LLM_MODEL` are needed only for a new API evaluation. Set `LAB07_EXTERNAL_CORPUS_OK=1` only when the permission to send the relevant source content to an external provider is confirmed. Course/submission permission is not blanket public redistribution permission. Prices in `.env` are estimates/caps; actual billing is read from provider usage when available. Never print or share the key.

## Ingestion and indexing (writes the Lab 07 database)

These commands are only needed to recreate the local V2 data/index; the submitted database already had 332 vectors. They do not modify Lab 06 A/B strategies, but do write the separate Lab 07 strategy:

```powershell
.\.venv\Scripts\python.exe starter\index_discrete_math.py --prepare-only
.\.venv\Scripts\python.exe starter\improve_discrete_math.py
$Day6Python = "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe"
& $Day6Python starter\index_discrete_math_v2.py
```

Indexing requires local source PDFs and the approved V2 JSON. Do not run it just to launch the UI/agent; it re-embeds and writes PostgreSQL. The 256/332 `needs_review` flags identify potentially incomplete mathematical/table/diagram extraction; no missing visual data is synthesized.

## Retrieval and dev experiments

Read-only live retrieval (requires the existing Lab 07 database and Lab 06 Python environment):

```powershell
& $Day6Python starter/retrieval_v2.py --strategy dense --query "What is a minimum spanning tree?" --top-k 3
& $Day6Python starter/retrieval_v2.py --strategy tfidf --query "What is a minimum spanning tree?" --top-k 3
& $Day6Python starter/retrieval_v2.py --strategy hybrid_rrf --query "What is a minimum spanning tree?" --top-k 3
```

Dev-only retrieval comparison and A2/context experiments create new local runs; they do not call the LLM. A2 uses saved R0 candidates and V2 data offline; C0/C1 uses saved TF-IDF traces:

```powershell
& $Day6Python starter\evaluate_retrieval_v2.py
.\.venv\Scripts\python.exe starter/retrieval_a2.py
.\.venv\Scripts\python.exe starter\context_engineering_v2.py
```

The benchmark files are read-only. Keep dev/test separation and do not use gold evidence for query, filters, or context selection. Aggregate retrieval metrics are gold-location measures (Hit@1/Evidence Hit@3); Context Evidence Rate is checked after packing. They do not assert that a generated answer is grounded.

## Agent evaluation and cost boundaries

A1 dev evaluation invokes OpenRouter and can incur cost. Only run a new dev experiment when explicitly intended, permission is confirmed, `.env` is configured, and the limits are reviewed:

```powershell
& $Day6Python starter/run_agent_a1_dev.py --max-api-calls 51 --max-total-tokens 30000 --max-cost-usd 0.10 --max-completion-tokens 300
```

The final test ran once on 2026-11-16. **Do not invoke `run_agent_a1_test.py` again.** Its source, prompts, corpus/benchmark hashes and outputs are frozen in the local run manifest. For submission review, use `report/individual/agent_final_evaluation_test.md`, `artifacts/final_evaluation_public.json`, `artifacts/final_test_manifest_public.json`, and `artifacts/final_test_trace_sanitized.json`. Full query/context/answer traces are restricted local artifacts under ignored `starter/results/`; provide them to the instructor only through a permission-appropriate restricted channel if required.

## Tests, UI/demo, and reproducibility

Unit tests are local and do not call OpenRouter or run benchmark queries:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q starter tests
```

One opt-in PostgreSQL integration test requires explicit `RUN_LIVE_V2_TESTS=1`; it is not part of the ordinary unit-test command. A complete rebuild from Git also requires licensed/authorized PDFs, locally generated V2 chunks, the Lab 06 model environment/cache, and PostgreSQL credentials. Reproduction of API answers additionally requires a valid OpenRouter account/key, permission for external source excerpts, model/provider availability and budget; provider routing can vary. The historical final run is reproducible by inspecting its manifest/hashes, not by rerunning the test.

Demo from saved evidence only: show a grounded answer (`t01`), a correct missing-evidence abstention (`t07`), and a false refusal/failure (`t04`) using the restricted raw trace/report. Explain the difference between source evidence in context and citation validator acceptance. Do not make a new API call for the demo.

Data permissions: the submitter reports instructor permission for Lab 07 and submission to the instructor. That scope does not itself authorize publishing PDFs, all chunks, or excerpts on the public repository. Original PDFs, V1/V2 chunk data and full traces are ignored; some tracked benchmark/audit files contain excerpts and still need public-scope confirmation. Do not force-add raw content or secrets. PDF text extraction can lose formulas, truth-table structure, matrices and graph details; retain `needs_review` and disclose uncertainty.
