# A0 retrospective test plan and execution record

## Decision

At plan creation, no A0 test run existed; the only test trace was the frozen A1 run `agent-a1-final-test-20261116T082303799998Z`. Following separate user approval, one A0 retrospective pass completed on all seven cases in `agent-a0-retro-test-20261116T151349722949Z`. The A1 run remains unchanged.

Because the test questions and A1 outcomes had already been opened, the completed A0 pass on those same seven questions is a **retrospective paired baseline comparison**, not an untouched independent test. It describes A0 versus A1 on identical questions and must not be used for tuning or advertised as independent generalization. A fresh locked test set would be needed for an independent comparison.

## Recovered A0 configuration and provenance

| Component | Verified A0 dev setting / evidence |
|---|---|
| Agent policy | Pre-A1 `run_v2_agent()` from `starter/agent_v2.py`; model makes a real function/tool decision; no A1 citation-aware repair loop. The answer generation follows the original JSON response instruction appended with retrieved context. |
| System prompt | `agent_v2.SYSTEM`; SHA-256 of its evaluated UTF-8 string: `15581527595b44a879acf2a65104a879e6ade6c2ab032b19cd966b0e19a16300`. The constant is unchanged across commits `c8a19d5`, `42aeb34`, and current HEAD. The tool schema/description is `agent_v2.TOOL`. |
| Model/provider | Request model `z-ai/glm-5.3-flash:floor`; the A0 dev manifest says OpenRouter model-suffix routing with provider price caps and `require_parameters`. Response metadata identifies the actual model/provider per call. |
| Retriever/context | TF-IDF Top-3 over the same 332-chunk V2 corpus; C0 preserves ranked whole chunks within 800 Unicode characters. No gold-based filters. Context/retrieval implementations were not changed by the later API adapter commit. |
| Corpus / dev benchmark | V2 SHA-256 `979a0baaf2f34735592bde1aeaf2bdb29b5a8f336f3f0bcb3fee699056f57990`; dev benchmark SHA-256 `84db26d01f9f4d5c3589f3f433d9a0c62a1db22feda079553755a32fbd3416ac`. |
| A0 dev run | `agent-dev-20261116T054605035184Z`; 17 cases; 9/15 manually grounded (60%); grade distribution 0:6, 1:0, 2:9; false refusal 6/15; missing-evidence abstention 2/2; tool use 17/17; citation structure among answered 9/9; manual semantic citation support 10/10 references. 34 LLM calls, 17,005 tokens, mean/median latency 4,059.48/3,744.07 ms, actual API cost $0.0011231227. |
| Source provenance limit | The A0 run manifest records model, retrieval/context configuration, cost caps, corpus and benchmark hashes, but not source/prompt hashes. The original runner was later changed to use OpenRouter; the final checked-in API adapter commit is after the A0 run. The system prompt hash is recoverable and unchanged, but the run's exact byte-for-byte runner/client snapshot cannot be proven from its manifest. The retrospective run must disclose this limitation and hash the exact code used. |

The matching A0 run has complete raw traces and `metrics_reviewed.json`. The reviewed metrics support the A0 dev scores above; the automatic file alone intentionally marks groundedness and semantic support as requiring manual review. Do not calculate A0 test results by extrapolating these dev measurements.

## Execution record (one pass complete)

The approved run used the recovered A0 `run_v2_agent()` behavior, `agent_v2.SYSTEM`/`TOOL`, model `z-ai/glm-5.3-flash:floor`, TF-IDF Top-3, C0 800 Unicode characters, and the original seven test cases. The test/corpus hashes, source and prompt hashes, caps and provenance notes were written to the manifest before the first LLM request. A one-shot sentinel was created; traces and partial metrics were persisted after every case.

Result: 7/7 cases completed, 14 calls, 7,049 tokens, $0.0004882121 actual cost; no API failure and no hard cap reached. A0 GAR was 0/5, correct abstention 2/2, tool use 7/7. Manual grades, citations, failure reasons and A0/A1 comparison are in [the retrospective audit](agent_a0_retrospective_test.md). Run manifest and output hashes are in the ignored run directory. No test/corpus changes, database writes or re-embedding occurred.

The run is retrospective because the test and A1 outcomes were previously opened. It cannot be described as an independent baseline test. Prompt/tool hashes match the historical references, but the old A0 runner/API adapter snapshot cannot be proven byte-identical because the A0 dev manifest did not record source hashes.

## Approval and rerun boundary

The user approved this single A0 retrospective pass and the configured caps; it is complete. The local one-shot sentinel prevents accidental repetition. Do not rerun A0 or A1 on these questions. An independent comparison would require a new test set that has not been opened.
