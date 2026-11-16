# Agent evaluation

## Contents

- [A0 retrospective protocol and provenance](#a0-retrospective-protocol-and-provenance)
- [A0 retrospective test audit](#a0-retrospective-test-audit)
- [A1 official final test evaluation](#a1-official-final-test-evaluation)

Evaluation records for the A0 retrospective baseline and A1 official final test. A0 used the already-opened test split and is not an independent held-out evaluation. The official A1 result remains 3/5 GAR.

## A0 retrospective protocol and provenance

## A0 retrospective test plan and execution record

### Decision

At plan creation, no A0 test run existed; the only test trace was the frozen A1 run `agent-a1-final-test-20261116T082303799998Z`. Following separate user approval, one A0 retrospective pass completed on all seven cases in `agent-a0-retro-test-20261116T151349722949Z`. The A1 run remains unchanged.

Because the test questions and A1 outcomes had already been opened, the completed A0 pass on those same seven questions is a **retrospective paired baseline comparison**, not an untouched independent test. It describes A0 versus A1 on identical questions and must not be used for tuning or advertised as independent generalization. A fresh locked test set would be needed for an independent comparison.

### Recovered A0 configuration and provenance

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

### Execution record (one pass complete)

The approved run used the recovered A0 `run_v2_agent()` behavior, `agent_v2.SYSTEM`/`TOOL`, model `z-ai/glm-5.3-flash:floor`, TF-IDF Top-3, C0 800 Unicode characters, and the original seven test cases. The test/corpus hashes, source and prompt hashes, caps and provenance notes were written to the manifest before the first LLM request. A one-shot sentinel was created; traces and partial metrics were persisted after every case.

Result: 7/7 cases completed, 14 calls, 7,049 tokens, $0.0004882121 actual cost; no API failure and no hard cap reached. A0 GAR was 0/5, correct abstention 2/2, tool use 7/7. Manual grades, citations, failure reasons and A0/A1 comparison are in [the retrospective audit](evaluation.md#a0-retrospective-test-audit). Run manifest and output hashes are in the ignored run directory. No test/corpus changes, database writes or re-embedding occurred.

The run is retrospective because the test and A1 outcomes were previously opened. It cannot be described as an independent baseline test. Prompt/tool hashes match the historical references, but the old A0 runner/API adapter snapshot cannot be proven byte-identical because the A0 dev manifest did not record source hashes.

### Approval and rerun boundary

The user approved this single A0 retrospective pass and the configured caps; it is complete. The local one-shot sentinel prevents accidental repetition. Do not rerun A0 or A1 on these questions. An independent comparison would require a new test set that has not been opened.

## A0 retrospective test audit

## A0 Retrospective Baseline Evaluation - test

### Kết luận và giới hạn

Đã chạy đúng một lượt A0 trên 7 câu test đã mở trước đó. Đây là **retrospective paired comparison**, không phải đánh giá độc lập. Không sửa test/corpus, không gọi database, không embedding lại và không chạy lại A1. Run directory: `starter/results/discrete_math_v2/agent-a0-retro-test-20261116T151349722949Z/` (local, Git-ignored).

A0 đạt Grounded Answer Rate **0/5** (grade 0: 5, grade 1: 0, grade 2: 0). Cả năm câu có đáp án đều kết thúc bằng abstention vì output draft không qua kiểm tra citation inline của agent. Hai câu thiếu bằng chứng abstain đúng **2/2**. Cả 7 câu đều gọi retrieval tool. Đây là thất bại ở tầng phản hồi/citation; retrieval và context của cả năm câu answerable đều chứa gold evidence.

### Cấu hình đã khóa và provenance

- Agent: A0 `run_v2_agent()` với `agent_v2.SYSTEM` và `agent_v2.TOOL`; không dùng A1 repair.
- Model request: `z-ai/glm-5.3-flash:floor` qua OpenRouter; response model `z-ai/glm-5.3-flash`.
- Retriever: TF-IDF Top-3; context: C0 tối đa 800 ký tự Unicode.
- Corpus: Discrete Math V2, 332 chunks.
- Test hash: `3f267ab60758d16351c4e26167e3adb730df8afab5dd983e9db5eb1fa50fc384`.
- Corpus hash: `979a0baaf2f34735592bde1aeaf2bdb29b5a8f336f3f0bcb3fee699056f57990`.
- A0 system prompt hash: `15581527595b44a879acf2a65104a879e6ade6c2ab032b19cd966b0e19a16300`; tool schema hash: `4cf064351a62da7b1bb51af8d7463811d48d97460f016b43b6e081ee362e880f`.
- Prompt và tool schema đã được đối chiếu với nội dung trong hai commit lịch sử ghi trong manifest. A0 dev manifest không ghi source hashes; vì thế không thể chứng minh client/runner hoặc toàn bộ working tree ở lần A0 dev trùng byte với retrospective runner. Run này dùng một runner test-only mới và API adapter OpenRouter hiện có. Đây là sai khác provenance cần giữ rõ khi diễn giải.
- Người nộp đã xác nhận quyền dùng corpus cho Lab/nộp giảng viên và quyền gửi nội dung cho đánh giá API. Quyền này không phải quyền công khai PDF hoặc mọi trích đoạn.

### Metrics

| Chỉ số | A0 retrospective test | Diễn giải |
|---|---:|---|
| Hit@1 | 5/5 (100%) | Chỉ 5 câu answerable; exact chunk/source/page và evidence quote |
| Evidence Hit@3 | 5/5 (100%) | Gold evidence có trong Top-3 |
| Context Evidence Rate | 5/5 (100%) | Gold quote còn trong context C0 |
| Context audit mức 0 / 1 / 2 | 0 / 0 / 5 | Các context answerable đủ evidence; `needs_review` được giữ nguyên |
| Grounded Answer Rate | **0/5 (0%)** | Abstain trên cả năm câu answerable được chấm grade 0 |
| Answer grade 0 / 1 / 2 | 5 / 0 / 0 | Manual audit câu trả lời cuối của agent |
| Citation structure, câu trả lời cuối | 0/0 (N/A) | Không có citation cuối vì agent abstain cả 7 câu |
| Semantic citation support, câu trả lời cuối | 0/0 (N/A) | Không có citation cuối để đánh giá |
| Citation metadata trong draft | 9/9 references khớp chunk/source/page/context | Metadata đúng không đồng nghĩa draft đạt format |
| Semantic support các citation draft | 9/9 citation references support mệnh đề factual chính | Chỉ là diagnostic của draft bị loại; không tính như câu trả lời cuối. t05 có thêm nhận xét về proof không được cite riêng |
| Draft đáp ứng đầy đủ inline citation validator | 0/5 draft answerable | t01/t04 sai inline-ID set; t02/t03/t05 còn câu không citation |
| Abstention chính xác | 2/2 | t06, t07 |
| False refusal | 5/5 (100%) | t01-t05 có evidence nhưng agent từ chối sau validation |
| Tool-use correctness | 7/7 (100%) | Một tool call cho mỗi câu |
| LLM/API calls | 14 | 2/câu; không retry |
| Input / output / tổng tokens | 5,202 / 1,847 / 7,049 | OpenRouter usage |
| Latency mean / median | 3,720 / 3,577 ms | End-to-end mỗi câu |
| Actual API cost | **$0.0004882121** | OpenRouter-reported usage cost |

Actual provider mix: Relace 7 calls, Wafer 7 calls. Run nằm trong cap 14 calls, 20.000 tokens, $0.10; OpenRouter key preflight còn đủ hạn mức cho cap. Không lưu key hoặc số dư tài khoản vào manifest.

### Audit theo câu

| Case | Context | Result / failure | PDF evidence review | Calls | Latency (ms) | Tokens | Actual cost (USD) |
|---|---:|---|---|---:|---:|---:|---:|
| t01 | 2 | Draft correct; `inline_citation_mismatch`; final abstain, grade 0 | p.27 directly states the Modus Tollens example/conclusion; citation metadata matches, but inline chunk tag is absent | 2 | 3,403.2 | 896 | 0.0000531297 |
| t02 | 2 | Draft gives lower bound 3; `uncited_sentence`; final abstain, grade 0 | pp.36 and 33 state the 20/7 example and principle. Readable text supports the answer despite `needs_review`; no visual content reconstructed | 2 | 4,223.9 | 1,080 | 0.0000817410 |
| t03 | 2 | Draft gives 111/000; `uncited_sentence`; final abstain, grade 0 | p.45 explicitly states the extrema; earlier draft sentences lack inline citations | 2 | 2,658.9 | 930 | 0.0000558035 |
| t04 | 2 | Draft explains Theorem 1.8/connectedness; `inline_citation_mismatch`; final abstain, grade 0 | p.39 states the theorem and p.37 defines connectedness; metadata matches but inline chunk tags are absent | 2 | 3,209.1 | 1,086 | 0.0000865319 |
| t05 | 2 | Draft states the Hamilton-path theorem; `uncited_sentence`; final abstain, grade 0 | p.30 states the theorem. The extra proof-status statement is unnecessary and not separately cited | 2 | 4,678.7 | 968 | 0.0000596787 |
| t06 | N/A | Model and final agent abstain correctly | Evidence gives a lower bound but not the box number | 2 | 3,577.1 | 1,019 | 0.0000730342 |
| t07 | N/A | Model and final agent abstain correctly | The theorem asserts existence but gives no vertex order | 2 | 4,289.4 | 1,070 | 0.0000782931 |

PDF đối chiếu là các file local trong `data/discrete_math/raw/`; đường dẫn tương đối và SHA-256 của nguồn kiểm tra được lưu trong `audit_manual.json`. Các trang liên quan được trích text để xác minh mệnh đề; kết quả không dựa vào việc tái tạo nội dung hình. Trace, metrics, audit và manifest đầy đủ chỉ ở local run directory.

### So sánh cùng test với A1 đã khóa

| Chỉ số | A0 retrospective | A1 official final test |
|---|---:|---:|
| GAR trên câu answerable | 0/5 (0%) | **3/5 (60%)** |
| Grade 0 / 1 / 2 | 5 / 0 / 0 | 2 / 0 / 3 |
| Hit@1 / Evidence Hit@3 / Context Evidence Rate | 5/5 / 5/5 / 5/5 | 5/5 / 5/5 / 5/5 (chấm lại từ trace đã lưu) |
| Context audit 0 / 1 / 2 | 0 / 0 / 5 | 0 / 0 / 5 |
| Citation structure cuối | 0/0 (N/A) | 3/3 câu trả lời |
| Semantic citation support cuối | 0/0 (N/A) | 3/3 references được audit hỗ trợ |
| Abstention / false refusal | 2/2 / 5/5 | 2/2 / 2/5 |
| Tool use | 7/7 | 7/7 |
| Calls / tokens | 14 / 7,049 | 16 / 10,363 |
| Latency mean / median | 3.720 / 3.577 s | 4.952 / 4.502 s |
| API cost thực tế | $0.0004882121 | $0.0006918935 |

Hai cấu hình dùng cùng request model alias, R0/C0 và cho cùng retrieval/context evidence trên 7 câu. Kết quả mô tả cho thấy A1 phát hành được 3 câu có đáp án và false refusal ít hơn 3 câu. Không kết luận đây là hiệu quả nhân quả thuần của A1: provider routing khác số lượng call và A0 API client snapshot lịch sử không chứng minh được chính xác. Chênh lệch latency/chi phí cũng không phải so sánh hiệu năng có kiểm soát.

### Tái lập và trạng thái

Manifest ghi hashes trước call cho benchmark, corpus, code, prompt/tool và giá/cap; đồng thời ghi output hashes sau audit. One-shot sentinel tại `starter/results/discrete_math_v2/.a0-retro-test-one-shot.lock` chặn vô tình chạy lượt thứ hai. Không chạy lại A0 hay A1. Run artifacts đang bị `.gitignore` loại trừ; không commit/push raw trace.

Kết quả chính thức A1 không đổi: dev GAR 12/15 và final test GAR **3/5**, abstention 2/2, tool use 7/7, cost $0.0006918935. A0 test chỉ bổ sung baseline retrospective, không biến test set đã mở thành một đánh giá độc lập.

## A1 official final test evaluation

## Lab 07 — Final Evaluation (A1, test)

### Kết luận

Đã chạy đúng một lượt trên 7 câu test, với A1, R0 TF-IDF Top-3, C0 tối đa 800 ký tự Unicode và request model `z-ai/glm-5.3-flash:floor` qua OpenRouter. Không chạy lại, không điều chỉnh sau khi xem test, không truy cập hoặc ghi database, không re-embedding. Cả 7 câu đều hoàn tất; không có lỗi API.

**Grounded Answer Rate: 3/5 (60%)** trên câu có đáp án. Hai câu false refusal (t02, t04) đã retrieve đúng evidence và model draft trả lời đúng, nhưng cả answer và lượt repair đều bị verifier từ chối vì có câu khẳng định không gắn citation inline. A1 trả lời an toàn bằng abstention cuối cùng; điểm answer vẫn bằng 0 theo rubric vì evidence đủ và câu trả lời không được phát hành.

Hai câu thiếu bằng chứng (t06, t07) abstain đúng. Tất cả 7 câu đều gọi retrieval tool. Không có citation sai source/page hoặc citation trỏ ra ngoài context trong câu trả lời/draft đã audit.

### Cấu hình đã khóa và tái lập

- Agent A1; tối đa một repair trên mỗi câu; không thay prompt/policy trong lượt test.
- Retriever R0: TF-IDF Top-3 trên corpus Discrete Math V2 (332 chunks).
- Context C0: tối đa 800 ký tự Unicode, giữ chunk nguyên vẹn và citation metadata.
- Request model `z-ai/glm-5.3-flash:floor`, qua `https://openrouter.ai/api/v1`, có `require_parameters` và `provider.max_price` theo cấu hình.
- Hash benchmark test: `3f267ab60758d16351c4e26167e3adb730df8afab5dd983e9db5eb1fa50fc384`.
- Hash corpus V2: `979a0baaf2f34735592bde1aeaf2bdb29b5a8f336f3f0bcb3fee699056f57990`.
- Manifest lưu SHA-256 của benchmark, corpus, manifest benchmark, A1, agent adapter, context packer, retrieval, baseline, runner và hai system prompt.

Người dùng đã xác nhận riêng quyền gửi context corpus tới OpenRouter cho lượt đánh giá; `.env` bật `LAB07_EXTERNAL_CORPUS_OK=1`. Người nộp cũng xác nhận giáo viên cho phép dùng tài liệu trong phạm vi Lab 07/nộp giảng viên. Hai xác nhận này không tự cấp quyền public PDF hoặc toàn bộ trích đoạn. Manifest benchmark vẫn ghi `source_redistribution_permission: requires verification` cho tái phân phối công khai.

### Metrics tự động

| Chỉ số | Test | Ý nghĩa |
|---|---:|---|
| Câu hoàn tất | 7/7 | 5 answerable, 2 missing evidence |
| Tool-use correctness | 7/7 (100%) | Mỗi câu gọi `search_discrete_math`; một lần retrieval/câu |
| Citation structure hợp lệ | 3/3 câu đã trả lời (100%); 3/5 câu answerable có answer draft hợp lệ ngay lần đầu | t02/t04 bị từ chối do claim trong câu tiếp theo thiếu citation inline; repair không khắc phục |
| Abstention đúng | 2/2 | t06, t07 |
| False refusal | 2/5 (40%) | t02, t04; retrieval có evidence |
| Grounded Answer Rate | 3/5 (60%) | Chấm thủ công theo câu trả lời cuối cùng được phát hành, không tính draft bị verifier loại |
| Semantic support của citation cuối | 3/3 (100%) | Kiểm tra thủ công trên PDF gốc; t02/t04 drafts cũng trỏ đến nguồn evidence đúng nhưng không qua cấu trúc claim-level |
| Latency trung bình / median | 4,952 / 4,502 ms | End-to-end, gồm controller, retrieval, generation và repair nếu có |
| Input / output / tổng tokens | 7,877 / 2,486 / 10,363 | Usage trả về từ OpenRouter |
| LLM calls / repairs | 16 / 2 | Trần 21 calls; tối đa một repair/câu |
| Chi phí API thực tế | **$0.0006918935** | Tổng `usage.cost` từ response OpenRouter; ước lượng theo price caps là $0.000788258 |

#### Retrieval coverage scored from the frozen test trace

This is a post-hoc scoring pass over the immutable A1 retrieval hits and selected context; it did not rerun retrieval or call an API. Using the same exact chunk ID, source ID, page, and whitespace-normalized evidence quote checks as the dev evaluator, the unchanged gold locations score Hit@1 **5/5**, Evidence Hit@3 **5/5**, and C0 Context Evidence Rate **5/5** on the five answerable cases. The two intentionally unanswerable cases are excluded. This retrieval coverage does not imply that the generated answer was grounded: t02 and t04 had sufficient context but failed citation validation and received answer grade 0.

The run stayed within the local hard caps: $0.10, 21 calls, and 20,000 tokens. Account limit and balance details have been omitted from the public report.

### So sánh Agent A1 dev/test

| Chỉ số | Dev (17 câu) | Test (7 câu) |
|---|---:|---:|
| Grounded Answer Rate | 12/15 (80%) | 3/5 (60%) |
| Citation structure hợp lệ trên câu được trả lời | 12/12 | 3/3 |
| Citation semantic support trên câu được trả lời | 12/12 theo audit dev | 3/3 theo audit test |
| Abstention đúng | 2/2 | 2/2 |
| False refusal | 3/15 (20%) | 2/5 (40%) |
| Tool use | 17/17 | 7/7 |
| Latency mean / median | 3,627 / 3,319 ms | 4,952 / 4,502 ms |
| Tokens | 20,772 | 10,363 |
| API calls | 35 | 16 |
| Chi phí thực tế | $0.0013042941 | $0.0006918935 |



Test giảm 20 điểm phần trăm Grounded Answer Rate so với dev; mẫu test chỉ có 5 câu answerable nên một câu tương ứng 20 điểm phần trăm. Tỷ lệ false refusal tăng từ 20% lên 40%. Đây là kết quả độc lập trên test, không dùng để chọn/thay cấu hình. Citation validity và semantic support ở trên là hai kiểm tra khác nhau: verifier chủ yếu đảm bảo JSON, citation inline và đúng metadata; support được audit bằng PDF.

### Audit thủ công theo PDF

Audit được đối chiếu với text của đúng trang PDF nguồn bằng `pypdf`, sau đó đối chiếu ID/source/page với context trace. Trang vật lý trong citation là số trang đã lưu ở V2. Ký tự/spacing trích xuất không phải lúc nào cũng giống hệt chuỗi benchmark; t03 có `tốiđại` dính khoảng trắng trong text layer, nhưng câu trên PDF vẫn đọc rõ cùng nội dung.

| ID | Kết quả cuối / grade | Citation và evidence PDF | Nhận xét |
|---|---|---|---|
| t01 | Answer / 2 | `chuong-1-co-so-logic:p27:c1:v2`, PDF *Chuong 1. Co so logic*, trang 27: ví dụ Modus Tollens kết luận “A không đi học đầy đủ”. | Trả lời đúng, citation đúng chunk/source/page và trực tiếp hỗ trợ claim. |
| t02 | Abstain / 0 | Draft cite `chuong-2-phep-dem:p36:c1:v2`, PDF *Chuong 2. Phep dem*, trang 36: 20 chim, 7 ô, ít nhất một ô có `[20/7]=3` con trở lên. | Evidence được retrieve và draft trả đúng “ít nhất 3”. Answer đầu bị loại vì câu cuối “Vậy…” không có citation inline. Repair chuyển biểu thức sang `[20/7]`; citation parser nhận nhầm ngoặc vuông toán học là citation thứ hai (`inline_citation_mismatch`), ngoài lỗi câu không citation. False refusal do cấu trúc/verifier, không phải retrieval/semantic miss. |
| t03 | Answer / 2 | `chuong-3-quan-he:p45:c1:v2`, PDF *Chuong 3. Quan he*, trang 45: lời giải ví dụ nói 111 là tối đại duy nhất, 000 là tối tiểu duy nhất. | Đúng. PDF cũng có lời giải bằng Hasse diagram; kết luận xuất hiện rõ trong text trang nên không cần đoán hình. |
| t04 | Abstain / 0 | Draft cites p39 và p37; PDF *chuong 5. Do thi (phan 1)* trang 39 ghi định lý 1.8 “liên thông khi và chỉ khi ... duy nhất một thành phần liên thông”; trang 37 hỗ trợ định nghĩa liên thông. | Evidence trực tiếp có trong context. Draft đúng nội dung nhưng câu “Nói cách khác…” không có inline citation; lượt repair lặp lại uncited sentence. False refusal do verifier, không phải retrieval. |
| t05 | Answer / 2 | `chuong-5-do-thi-phan-2:p30:c1:v2`, PDF *Chuong 5. Do thi (phan 2)*, trang 30: định lý König nói đồ thị có hướng đầy đủ có đường đi Hamilton; phần chứng minh “xem tài liệu”. | Claim chính đúng; câu bổ sung về việc chứng minh được dẫn chiếu cũng đúng với trang nguồn. Citation đúng. |
| t06 | Abstain / 2 cho abstention | Không có citation cuối. PDF Chương 2 trang 36 chỉ đảm bảo tồn tại một ô chứa ít nhất 3 chim; không xác định số ô hoặc chính xác ô nào. | Không bịa số ô; abstain đúng theo benchmark absence check. |
| t07 | Abstain / 2 cho abstention | Không có citation cuối. PDF Chương 5 (phần 2) trang 30 chỉ phát biểu tồn tại đường đi Hamilton và ghi chứng minh “xem tài liệu”, không nêu thứ tự đỉnh cụ thể. | Không bịa thứ tự; abstain đúng theo benchmark absence check. |

Grounded Answer Rate dùng 5 answerable làm mẫu số; grade 2 được tính là grounded answer. Abstention Accuracy dùng riêng 2 câu thiếu evidence. Hai câu abstain sai là false refusal; không được tính là “abstention đúng”.

### Hạn chế và đối chiếu rubric Day 07

- **Dữ liệu/benchmark:** V2 332 chunks, citation có source và trang; benchmark 17 dev + 7 test đã khóa hash. Tập test chỉ chạy một lượt.
- **Retrieval:** Dense pgvector, TF-IDF, Hybrid RRF đã được xây và đánh giá dev trước đó; Final Evaluation dùng R0 theo quyết định khóa cấu hình. Test diagnostics cho thấy Hit@1 và Evidence Hit@3 đều 5/5 answerable; cả 5 evidence nằm trong C0. False refusals không bắt nguồn từ retriever.
- **Agent/context:** API tool calling thật, C0, JSON/citation validation, tối đa một repair. 7/7 truy vấn gọi tool; repair xảy ra ở t02/t04 và không tạo evidence mới.
- **Evaluation:** Retrieval/context metrics dev và manual agent audits được tách khỏi tự động checks. Final test có audit từng câu, citation metadata và support trên PDF.
- **Experiments/improvements:** A/B/C ingestion/retrieval, C0/C1, A0/A1 và R0/R1/R2 được giữ thành runs riêng; cấu hình được chọn trên dev. Test không dẫn đến thay đổi prompt hoặc retriever. Audit này phát hiện hai lỗi cần sửa trong một run dev mới: bộ parse citation nhầm `[20/7]` là citation; prompt/verifier không giúp model gắn inline citation cho từng câu khẳng định (t04).
- **Trade-offs, cost, latency:** Test tốn $0.0006918935, thấp hơn cap $0.10; trung bình 4.95 giây/câu. Tăng thêm model call/repair chưa khắc phục lỗi trích dẫn lặp câu.
- **Reproducibility/reporting:** `manifest.json` khóa hash/config; traces đầy đủ gồm controller, calls, hits, context, output, citation, usage, provider, latency và cost. Trace/results không ghi vào Git theo `.gitignore`; chỉ report/code được theo dõi.
- **Giới hạn ingestion:** PDF extraction làm hỏng hoặc mất layout công thức, bảng, ma trận và hình; các chunk `needs_review` không được dùng để suy đoán dữ liệu thị giác. Giáo viên đã cho phép dùng tài liệu cho bài học/nộp bài theo xác nhận của người nộp; chưa có căn cứ trong repo cho quyền public PDF, corpus hoặc mọi excerpt.
- **Nâng cao:** Không đánh giá challenge riêng 100 trang/90%; không tuyên bố đạt bonus.

#### Công việc còn lại

1. Sửa lỗi A1 validation/prompt ở một run mới trên dev trước khi cân nhắc benchmark test khác; không thay kết quả run khóa hiện tại. Ưu tiên phân biệt bracket công thức với `[chunk_id]`, rồi kiểm tra repair có bao phủ citation cho từng câu.
2. Lưu lại phạm vi giáo viên cho phép dùng tài liệu cho Lab 07/nộp bài. Nếu muốn duy trì public repository, xác nhận riêng rằng benchmark/audit excerpts cụ thể được phép public; quyền gửi context tới OpenRouter trong lượt này là xác nhận riêng, không phải quyền public PDF.
3. Nếu cần semantic citation support tự động, bổ sung evaluator riêng; cấu trúc citation hợp lệ hiện không tự chứng minh entailment.

### Artifacts và lệnh tái lập

Run: `starter/results/discrete_math_v2/agent-a1-final-test-20261116T082303799998Z/`

- `manifest.json`: hash, cấu hình, permission/budget preflight và trạng thái complete.
- `traces.json`: trace đầy đủ của 7 câu, ghi sau từng câu.
- `metrics_auto.json`: metrics tự động; grounded/semantic fields được audit riêng.
- `reviews_template.json`: schema review cho lần kiểm tra, không thay audit đã hoàn thành.
- `audit_manual.json`: audit theo câu và evidence PDF.

Preflight tests: `python -m unittest discover -s tests -v` (54 passed, 1 PostgreSQL live test skipped). Chỉ chạy lệnh API này một lần; chạy lại sẽ tạo một lượt test mới:

```powershell
python starter/run_agent_a1_test.py --max-api-calls 21 --max-total-tokens 20000 --max-cost-usd 0.10
```

### Final test context and answer grade audit

Per BENCHMARK, context grade 0 means no evidence, 1 means partial evidence or missing conditions/source, and 2 means sufficient evidence with a traceable citation. Each of the five answerable test contexts receives context grade 2 after matching selected-context IDs to the raw trace and checking cited physical PDF pages. Lengths below count Unicode characters in `selected_context`, not tokens. Only IDs in the final context appear; other Top-3 hits were not packed.

| Case | Context chars / budget | Locators in C0 | Context grade | Audit reason |
|---|---:|---|---:|---|
| t01 | 604/800 | Ch.1 p.27, p.26 | 2 | p.27 states the Modus Tollens conclusion directly; source and page match. |
| t02 | 747/800 | Ch.2 p.36, p.33 | 2 | p.36 contains the pigeonhole condition and lower bound 3; the physical page was checked. Chunk p.36 remains `needs_review`, but its relevant readable text is sufficient for this claim. No missing visual content was reconstructed. |
| t03 | 694/800 | Ch.3 p.45, p.44 | 2 | The unique maximal/minimal elements are stated in page text; locator matches. |
| t04 | 678/800 | Ch.5 part 1 p.39, p.37 | 2 | The needed connectivity theorem is on p.39 and p.37 gives the definition; both locators were checked. |
| t05 | 787/800 | Ch.5 part 2 p.30; Ch.6 p.4, p.24 | 2 | The cited theorem and stated limitation were checked against p.30 and context metadata. |

Context grade distribution for t01-t05: **0:0, 1:0, 2:5**. Answer grade distribution for the five answerable cases: **0:2 (t02,t04), 1:0, 2:3 (t01,t03,t05)**; mean 1.2/2 and GAR 3/5. Sufficient context does not guarantee a valid released answer: t02/t04 have context grade 2 but answer grade 0 because validation rejected the output.

### A0 retrospective baseline comparison

A0 was subsequently run once on the same seven already-opened test questions, using the recovered A0 prompt/tool, the locked GLM model, R0 TF-IDF Top-3 and C0 800. It is a retrospective paired comparison, not an independent test. A0 completed 7/7, retrieved and packed gold evidence for 5/5 answerable cases, but all five final answers were abstentions (GAR 0/5; false refusal 5/5). Both missing-evidence cases abstained correctly (2/2). A0 tool use was 7/7; it used 14 API calls, 7,049 tokens and $0.0004882121 actual cost. The official A1 result remains 3/5 GAR, abstention 2/2 and tool use 7/7; it was not rerun or modified.

The A0 draft citations had correct chunk/source/page metadata and their nine primary cited claims were supported on the PDF pages, but none of the five answerable drafts passed inline citation validation. A0 produced no final citations, so final citation structure and semantic support are 0/0 (not applicable). Context grades were 2/2 on t01-t05. Full manual audit, per-case failure reasons, run hashes and the A0/A1 comparison are in [the A0 retrospective report](evaluation.md#a0-retrospective-test-audit). The code/prompt provenance caveat remains: prompt/tool hashes match historical commits, but the original A0 runner/API adapter snapshot was not recorded in its dev manifest and cannot be proven identical.

### Per-case telemetry

| Case | Retrieval calls | LLM calls | Repair | Latency (ms) | Tokens | Cost (USD) | Status/error |
|---|---:|---:|---:|---:|---:|---:|---|
| t01 | 1 | 2 | 0 | 3,484.2 | 1,063 | 0.0000604899 | Answer; structure valid |
| t02 | 1 | 3 | 1 | 5,992.3 | 2,048 | 0.0001378028 | `uncited_sentence`; repair `inline_citation_mismatch`; false refusal |
| t03 | 1 | 2 | 0 | 4,035.5 | 1,167 | 0.0000653781 | Answer; structure valid |
| t04 | 1 | 3 | 1 | 8,661.1 | 2,370 | 0.0001788145 | `uncited_sentence` persists; repair failure; false refusal |
| t05 | 1 | 2 | 0 | 3,267.7 | 1,131 | 0.0000677813 | Answer; structure valid |
| t06 | 1 | 2 | 0 | 4,501.8 | 1,253 | 0.0000907160 | Correct model abstention; no API error |
| t07 | 1 | 2 | 0 | 4,721.2 | 1,331 | 0.0000909109 | Correct model abstention; no API error |

There was one retrieval tool call for each test question (7/7) and 16 LLM/API calls overall, including two repairs. There were no provider/transport errors. t02/t04 are citation/output validation failures, not retrieval misses. The three final released answers have 3/3 structurally valid citation references and 3/3 manually supported references. Draft references in t02/t04 do not turn their final abstentions into grounded answers.

### Sanitized evidence and restricted submission

`artifacts/final_test_trace_sanitized.json` contains seven cases and 21 retrieval hits, with metadata, controller/tool events, citation validation, provider, latency, tokens, and cost. It excludes query text, answer text, chunk text, raw context, evidence notes, free-form tool arguments, and credentials. Run ID, hit locators and aggregates match the frozen raw run; public manifest hashes match the raw artifacts. This sanitized artifact supports structural/run review but cannot independently verify semantic grounding.

The course submission instructions request per-query query, context, answer, citations, errors, timing and cost. The A1 and A0 raw traces, metrics and audits remain in separate local runs under ignored `starter/results/`; the A0 retrospective report summarizes the newly completed pass. A separate local-only instructor bundle is prepared in `../../.private_submission/agent-a1-final-test-20261116T082303799998Z/`; it includes byte-identical trace/metrics/audit files and a manifest copy with account-specific spending-limit details removed. The bundle README and SHA256 list describe verification. If the instructor needs them, use a restricted course/LMS channel covered by the permission. Do not publish raw traces unless permission explicitly covers all their contents.

### Demo sequence (saved evidence; no API call)

1. Show t01 as a grounded answer with matching source/page citation.
2. Show t07 as a correct abstention because the available evidence does not supply the requested vertex order.
3. Show t04 as a real failure: C0 contains adequate evidence, but an uncited follow-up remains after repair and the agent abstains.

Use the restricted raw trace for query, answer and context details if required. Do not make a new API call or rerun evaluation for the demo.
