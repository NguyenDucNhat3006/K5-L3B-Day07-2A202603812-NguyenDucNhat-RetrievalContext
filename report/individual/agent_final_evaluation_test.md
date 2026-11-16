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

Định tuyến thực tế báo `z-ai/glm-5.3-flash` ở response metadata (OpenRouter bỏ hậu tố alias trong trường `model`); endpoint providers được chọn là **Relace (7 calls)** và **Wafer (9 calls)**. Key có giới hạn chi tiêu $50; trước run còn $49.997510406 và sau run còn $49.996818516. Run vẫn áp dụng hard cap cục bộ $0.10, 21 calls, 20,000 tokens.

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

## Trace sanitized cho submission

`artifacts/final_test_trace_sanitized.json` gi? 7 case c?ng retrieval hits, metadata, tool events, citation checks, latency, token usage v? chi ph?. Query, answer, chunk text, context v? evidence note ?? ???c b?. Raw trace/metrics g?c v?n n?m nguy?n t?i th? m?c run b? ignore; hash c?a traces, metrics, audit v? manifest g?c ti?p t?c kh?p manifest.
