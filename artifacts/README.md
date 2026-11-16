# Sanitized submission evidence

This folder contains aggregate metrics, configuration/hash metadata and outcome labels only. It intentionally omits benchmark questions, expected answers, gold evidence text, retrieved chunks, full model outputs, API keys and raw contexts.

- `final_evaluation_public.json`: dev/test metrics, selected configurations, high-level per-case labels, costs and run IDs.
- `final_test_manifest_public.json`: frozen source/prompt/benchmark hashes and run limits, with account-specific spending balance removed.
- `final_test_trace_sanitized.json`: seven test case traces with retrieval IDs/ranks/scores, source/page metadata, tool events, citation checks, timing, token usage and costs. It omits question, answer, chunk text, context, evidence notes and free-text tool arguments.

Full traces remain under `starter/results/`, which is ignored by Git because traces contain PDF-derived context and model conversation data. Do not force-add them without a documented permission review. These summaries allow reviewers to inspect aggregate results and compare hashes; they are not a substitute for the private raw traces during an authorized audit.

The GitHub repository is currently public. The submitter reports teacher permission to use the documents for Lab 07/course submission. That scope does not establish permission to publish complete PDFs, the whole corpus, or every evidence excerpt. The benchmark dev/test JSON and some existing report/audit files are already tracked and contain source-derived excerpts; obtain confirmation that these exact artifacts are within the allowed scope before treating public distribution as authorized. The sanitized trace itself omits source text, but it does not grant permission for the other tracked content. Do not edit the locked benchmark in place.
