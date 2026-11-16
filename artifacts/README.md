# Sanitized submission evidence

This folder contains aggregate metrics, configuration/hash metadata and outcome labels only. It intentionally omits benchmark questions, expected answers, gold evidence text, retrieved chunks, full model outputs, API keys and raw contexts.

- `final_evaluation_public.json`: dev/test metrics, selected configurations, high-level per-case labels, costs and run IDs.
- `final_test_manifest_public.json`: frozen source/prompt/benchmark hashes and run limits, with account-specific spending balance removed.

Full traces remain under `starter/results/`, which is ignored by Git because traces contain PDF-derived context and model conversation data. Do not force-add them without a documented permission review. These summaries allow reviewers to inspect aggregate results and compare hashes; they are not a substitute for the private raw traces during an authorized audit.

The benchmark dev/test JSON and some existing report/audit files are already tracked and contain source-derived evidence excerpts. Source redistribution rights remain unverified. Confirm permission before publishing this repository; if excerpts cannot be redistributed, use a private submission channel or a clean-history sanitized copy and provide a permitted local acquisition/reconstruction procedure. Do not edit the locked benchmark in place to make a public copy.
