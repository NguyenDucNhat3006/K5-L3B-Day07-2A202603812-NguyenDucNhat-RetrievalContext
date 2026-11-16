# Lab 07 — Final Evaluation (A1, test)

## Kết luận

Đã chạy đúng một lượt trên 7 câu test, với A1, R0 TF-IDF Top-3, C0 tối đa 800 ký tự Unicode và request model `z-ai/glm-5.3-flash:floor` qua OpenRouter. Không chạy lại, không điều chỉnh sau khi xem test, không truy cập hoặc ghi database, không re-embedding. Cả 7 câu đều hoàn tất; không có lỗi API.

**Grounded Answer Rate: 3/5 (60%)** trên câu có đáp án. Hai câu false refusal (t02, t04) đã retrieve đúng evidence và model draft trả lời đúng, nhưng cả answer và lượt repair đều bị verifier từ chối vì có câu khẳng định không gắn citation inline. A1 trả lời an toàn bằng abstention cuối cùng; điểm answer vẫn bằng 0 theo rubric vì evidence đủ và câu trả lời không được phát hành.

Hai câu thiếu bằng chứng (t06, t07) abstain đúng. Tất cả 7 câu đều gọi retrieval tool. Không có citation sai source/page hoặc citation trỏ ra ngoài context trong câu trả lời/draft đã audit.

## Cấu hình đã khóa và tái lập

- Agent A1; tối đa một repair trên mỗi câu; không thay prompt/policy trong lượt test.
- Retriever R0: TF-IDF Top-3 trên corpus Discrete Math V2 (332 chunks).
- Context C0: tối đa 800 ký tự Unicode, giữ chunk nguyên vẹn và citation metadata.
- Request model `z-ai/glm-5.3-flash:floor`, qua `https://openrouter.ai/api/v1`, có `require_parameters` và `provider.max_price` theo cấu hình.
- Hash benchmark test: `3f267ab60758d16351c4e26167e3adb730df8afab5dd983e9db5eb1fa50fc384`.
- Hash corpus V2: `979a0baaf2f34735592bde1aeaf2bdb29b5a8f336f3f0bcb3fee699056f57990`.
- Manifest lưu SHA-256 của benchmark, corpus, manifest benchmark, A1, agent adapter, context packer, retrieval, baseline, runner và hai system prompt.

Người dùng đã xác nhận riêng quyền gửi context corpus tới OpenRouter cho lượt đánh giá; `.env` bật `LAB07_EXTERNAL_CORPUS_OK=1`. Người nộp cũng xác nhận giáo viên cho phép dùng tài liệu trong phạm vi Lab 07/nộp giảng viên. Hai xác nhận này không tự cấp quyền public PDF hoặc toàn bộ trích đoạn. Manifest benchmark vẫn ghi `source_redistribution_permission: requires verification` cho tái phân phối công khai.

## Metrics tự động

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

### Retrieval coverage scored from the frozen test trace

This is a post-hoc scoring pass over the immutable A1 retrieval hits and selected context; it did not rerun retrieval or call an API. Using the same exact chunk ID, source ID, page, and whitespace-normalized evidence quote checks as the dev evaluator, the unchanged gold locations score Hit@1 **5/5**, Evidence Hit@3 **5/5**, and C0 Context Evidence Rate **5/5** on the five answerable cases. The two intentionally unanswerable cases are excluded. This retrieval coverage does not imply that the generated answer was grounded: t02 and t04 had sufficient context but failed citation validation and received answer grade 0.

The run stayed within the local hard caps: $0.10, 21 calls, and 20,000 tokens. Account limit and balance details have been omitted from the public report.

## So sánh Agent A1 dev/test

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

## Audit thủ công theo PDF

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

## Hạn chế và đối chiếu rubric Day 07

- **Dữ liệu/benchmark:** V2 332 chunks, citation có source và trang; benchmark 17 dev + 7 test đã khóa hash. Tập test chỉ chạy một lượt.
- **Retrieval:** Dense pgvector, TF-IDF, Hybrid RRF đã được xây và đánh giá dev trước đó; Final Evaluation dùng R0 theo quyết định khóa cấu hình. Test diagnostics cho thấy Hit@1 và Evidence Hit@3 đều 5/5 answerable; cả 5 evidence nằm trong C0. False refusals không bắt nguồn từ retriever.
- **Agent/context:** API tool calling thật, C0, JSON/citation validation, tối đa một repair. 7/7 truy vấn gọi tool; repair xảy ra ở t02/t04 và không tạo evidence mới.
- **Evaluation:** Retrieval/context metrics dev và manual agent audits được tách khỏi tự động checks. Final test có audit từng câu, citation metadata và support trên PDF.
- **Experiments/improvements:** A/B/C ingestion/retrieval, C0/C1, A0/A1 và R0/R1/R2 được giữ thành runs riêng; cấu hình được chọn trên dev. Test không dẫn đến thay đổi prompt hoặc retriever. Audit này phát hiện hai lỗi cần sửa trong một run dev mới: bộ parse citation nhầm `[20/7]` là citation; prompt/verifier không giúp model gắn inline citation cho từng câu khẳng định (t04).
- **Trade-offs, cost, latency:** Test tốn $0.0006918935, thấp hơn cap $0.10; trung bình 4.95 giây/câu. Tăng thêm model call/repair chưa khắc phục lỗi trích dẫn lặp câu.
- **Reproducibility/reporting:** `manifest.json` khóa hash/config; traces đầy đủ gồm controller, calls, hits, context, output, citation, usage, provider, latency và cost. Trace/results không ghi vào Git theo `.gitignore`; chỉ report/code được theo dõi.
- **Giới hạn ingestion:** PDF extraction làm hỏng hoặc mất layout công thức, bảng, ma trận và hình; các chunk `needs_review` không được dùng để suy đoán dữ liệu thị giác. Giáo viên đã cho phép dùng tài liệu cho bài học/nộp bài theo xác nhận của người nộp; chưa có căn cứ trong repo cho quyền public PDF, corpus hoặc mọi excerpt.
- **Nâng cao:** Không đánh giá challenge riêng 100 trang/90%; không tuyên bố đạt bonus.

### Công việc còn lại

1. Sửa lỗi A1 validation/prompt ở một run mới trên dev trước khi cân nhắc benchmark test khác; không thay kết quả run khóa hiện tại. Ưu tiên phân biệt bracket công thức với `[chunk_id]`, rồi kiểm tra repair có bao phủ citation cho từng câu.
2. Lưu lại phạm vi giáo viên cho phép dùng tài liệu cho Lab 07/nộp bài. Nếu muốn duy trì public repository, xác nhận riêng rằng benchmark/audit excerpts cụ thể được phép public; quyền gửi context tới OpenRouter trong lượt này là xác nhận riêng, không phải quyền public PDF.
3. Nếu cần semantic citation support tự động, bổ sung evaluator riêng; cấu trúc citation hợp lệ hiện không tự chứng minh entailment.

## Artifacts và lệnh tái lập

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

## Final test context and answer grade audit

Per BENCHMARK, context grade 0 means no evidence, 1 means partial evidence or missing conditions/source, and 2 means sufficient evidence with a traceable citation. Each of the five answerable test contexts receives context grade 2 after matching selected-context IDs to the raw trace and checking cited physical PDF pages. Lengths below count Unicode characters in `selected_context`, not tokens. Only IDs in the final context appear; other Top-3 hits were not packed.

| Case | Context chars / budget | Locators in C0 | Context grade | Audit reason |
|---|---:|---|---:|---|
| t01 | 604/800 | Ch.1 p.27, p.26 | 2 | p.27 states the Modus Tollens conclusion directly; source and page match. |
| t02 | 747/800 | Ch.2 p.36, p.33 | 2 | p.36 contains the pigeonhole condition and lower bound 3; the physical page was checked. Chunk p.36 remains `needs_review`, but its relevant readable text is sufficient for this claim. No missing visual content was reconstructed. |
| t03 | 694/800 | Ch.3 p.45, p.44 | 2 | The unique maximal/minimal elements are stated in page text; locator matches. |
| t04 | 678/800 | Ch.5 part 1 p.39, p.37 | 2 | The needed connectivity theorem is on p.39 and p.37 gives the definition; both locators were checked. |
| t05 | 787/800 | Ch.5 part 2 p.30; Ch.6 p.4, p.24 | 2 | The cited theorem and stated limitation were checked against p.30 and context metadata. |

Context grade distribution for t01-t05: **0:0, 1:0, 2:5**. Answer grade distribution for the five answerable cases: **0:2 (t02,t04), 1:0, 2:3 (t01,t03,t05)**; mean 1.2/2 and GAR 3/5. Sufficient context does not guarantee a valid released answer: t02/t04 have context grade 2 but answer grade 0 because validation rejected the output.

## A0 retrospective baseline comparison

A0 was subsequently run once on the same seven already-opened test questions, using the recovered A0 prompt/tool, the locked GLM model, R0 TF-IDF Top-3 and C0 800. It is a retrospective paired comparison, not an independent test. A0 completed 7/7, retrieved and packed gold evidence for 5/5 answerable cases, but all five final answers were abstentions (GAR 0/5; false refusal 5/5). Both missing-evidence cases abstained correctly (2/2). A0 tool use was 7/7; it used 14 API calls, 7,049 tokens and $0.0004882121 actual cost. The official A1 result remains 3/5 GAR, abstention 2/2 and tool use 7/7; it was not rerun or modified.

The A0 draft citations had correct chunk/source/page metadata and their nine primary cited claims were supported on the PDF pages, but none of the five answerable drafts passed inline citation validation. A0 produced no final citations, so final citation structure and semantic support are 0/0 (not applicable). Context grades were 2/2 on t01-t05. Full manual audit, per-case failure reasons, run hashes and the A0/A1 comparison are in [the A0 retrospective report](agent_a0_retrospective_test.md). The code/prompt provenance caveat remains: prompt/tool hashes match historical commits, but the original A0 runner/API adapter snapshot was not recorded in its dev manifest and cannot be proven identical.

## Per-case telemetry

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

## Sanitized evidence and restricted submission

`artifacts/final_test_trace_sanitized.json` contains seven cases and 21 retrieval hits, with metadata, controller/tool events, citation validation, provider, latency, tokens, and cost. It excludes query text, answer text, chunk text, raw context, evidence notes, free-form tool arguments, and credentials. Run ID, hit locators and aggregates match the frozen raw run; public manifest hashes match the raw artifacts. This sanitized artifact supports structural/run review but cannot independently verify semantic grounding.

The course submission instructions request per-query query, context, answer, citations, errors, timing and cost. The A1 and A0 raw traces, metrics and audits remain in separate local runs under ignored `starter/results/`; the A0 retrospective report summarizes the newly completed pass. A separate local-only instructor bundle is prepared in `../../.private_submission/agent-a1-final-test-20261116T082303799998Z/`; it includes byte-identical trace/metrics/audit files and a manifest copy with account-specific spending-limit details removed. The bundle README and SHA256 list describe verification. If the instructor needs them, use a restricted course/LMS channel covered by the permission. Do not publish raw traces unless permission explicitly covers all their contents.

## Demo sequence (saved evidence; no API call)

1. Show t01 as a grounded answer with matching source/page citation.
2. Show t07 as a correct abstention because the available evidence does not supply the requested vertex order.
3. Show t04 as a real failure: C0 contains adequate evidence, but an uncited follow-up remains after repair and the agent abstains.

Use the restricted raw trace for query, answer and context details if required. Do not make a new API call or rerun evaluation for the demo.
