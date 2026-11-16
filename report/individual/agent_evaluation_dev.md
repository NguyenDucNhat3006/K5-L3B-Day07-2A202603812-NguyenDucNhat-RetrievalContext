# Lab 07 — LLM Agent trên dev

## Trạng thái

Đã implement agent gọi API Chat Completions thật, dùng tool calling để quyết định gọi `search_discrete_math`. Tool dùng TF-IDF Top-3 trên 332 chunk V2 và C0 với 800 ký tự Unicode. Query giữ nguyên câu hỏi gốc; không dùng nhãn benchmark hoặc gold trong agent. Lần gọi model thứ hai chỉ nhận context đã chọn. Đây là tool calling thật khi có API, không phải pipeline RAG cố định. Model có thể không gọi tool; trace ghi quyết định đó và agent từ chối trả lời.

`.env` có khóa OpenRouter (không in ra), model `z-ai/glm-5.3-flash:floor` và URL `https://openrouter.ai/api/v1`; runner tự nạp file này. Sau khi người dùng cập nhật quyền chia sẻ, đã chạy toàn bộ **17 câu dev** qua API thật trong run mới; xem [manifest](../../starter/results/discrete_math_v2/agent-dev-20261116T054605035184Z/manifest.json), [traces](../../starter/results/discrete_math_v2/agent-dev-20261116T054605035184Z/traces.json), [metrics tự động](../../starter/results/discrete_math_v2/agent-dev-20261116T054605035184Z/metrics_auto.json), [metrics đã audit](../../starter/results/discrete_math_v2/agent-dev-20261116T054605035184Z/metrics_reviewed.json) và [audit 17 câu](agent_audit_dev_20261116.json). Run d04 trước đó được giữ nguyên. Không đọc/chạy test benchmark.

Run 17 câu dùng cùng model/configuration, cap $0.042/M input và $0.184/M output. Mỗi câu tạo tối đa hai LLM calls; tổng 34 calls. Tất cả 34 responses có token, provider và `usage.cost`; tổng API cost **$0.0011231227**, 17,005 tokens, trong giới hạn $0.10/30,000 tokens. Provider là Relace cho controller và Wafer cho JSON answer ở cả run. Lượt controller và answer được ghi riêng trong từng trace. Smoke d04 độc lập có chi phí xác nhận $0.0000621938; nó không thuộc tổng 17 câu.

## Kiểm tra và thước đo

Mỗi trace có query, quyết định controller, tool call và tham số, Top-3 hits, context C0, phản hồi LLM, citation, abstention, latency, usage token và cost estimate nếu có giá hợp lệ. Bộ kiểm tra citation yêu cầu ID nằm trong context, source/page đúng, và từng câu trả lời có citation inline. Đây là tính hợp lệ **cấu trúc**; người chấm vẫn phải xác nhận từng khẳng định có được text tương ứng hỗ trợ. Trace `needs_review` ghi rủi ro text so với hình/bảng/công thức chưa xác minh.

Run 17 câu cho grounded answer **9/15 (60%)**. Citation structure hợp lệ ở 9/9 câu được trả lời (coverage 9/15 câu answerable); 10/10 citation references trong các câu trả lời được audit semantic support và source/page. Hai câu thiếu evidence abstain đúng 2/2. False refusal là 6/15 (40%); toàn bộ 17 câu đã gọi tool đúng một lần.

## Hai rủi ro đã thấy trên dev trước khi chạy agent

- d03: context C0 không chứa hàng bảng chân trị cần thiết; một chunk liên quan có cờ công thức chưa ánh xạ. Agent phải từ chối thay vì tự tính hoặc tự dựng bảng. Đây là lỗi retrieval/context đã kiểm chứng, chưa phải lỗi LLM.
- d01: context C0 không có evidence định nghĩa mệnh đề cần thiết. Prompt chặt có thể gây từ chối đúng về mặt grounding nhưng tăng false refusal trên câu benchmark có đáp án. Đây là giới hạn retrieval đã kiểm chứng, chưa phải lỗi LLM.
- d11: phương án C1 từng bỏ sót điều kiện hai chiều; C0 giữ evidence tốt hơn nên được khóa cho agent. Không thay đổi policy theo test.

## Đối chiếu rubric

| Tiêu chí Day07 | Trạng thái |
|---|---|
| Corpus/benchmark dev 332 chunk, 15 có đáp án + 2 thiếu evidence | Đã kiểm chứng ở bước retrieval/context |
| Ba retrieval method | Đã có trong `retrieval_v2.py`; agent chọn TF-IDF |
| Agent model thật, tool trace, điều kiện dừng | Đã chạy API thật trên 17 câu; 34 calls, tool use 17/17 |
| Context C0, citation, thiếu evidence | C0 dùng trên 17 câu; citation structure và semantic support được audit thủ công |
| Grounded answer, citation support, abstention trên dev | Grounded 9/15; support 10/10 references; abstention 2/2; false refusal 6/15 |
| Cải thiện ít nhất hai cấu hình agent | Chưa làm; không chỉnh prompt trước baseline API |
| Test benchmark sau khi chốt dev | Chưa chạy, theo yêu cầu |
| Chi phí/latency API | 17 câu: $0.0011231227; mean 4059 ms, median 3744 ms |

## Giới hạn và bước cần người dùng

Chưa chạy test theo yêu cầu. Các lỗi chính cần xử lý ở một run mới: d01 TF-IDF bỏ lỡ p4; d03 không retrieve truth table p16; d04/d06/d13/d14 model trả lời có citation object nhưng thiếu inline `[chunk_id]`, nên citation validator gây false refusal. Không đổi prompt/policy giữa run này. Không đưa key vào repo.

## Kết quả đánh giá dev mới nhất

| Chỉ số | Kết quả |
|---|---:|
| Grounded Answer Rate (15 answerable) | 9/15 = 60.0% |
| Citation structure validity (câu answered) | 9/9 = 100%; coverage answerable 9/15 = 60.0% |
| Semantic citation support | 10/10 references = 100.0% |
| Abstention accuracy (d16, d17) | 2/2 = 100.0% |
| False refusal (answerable) | 6/15 = 40.0% |
| Tool-use correctness | 17/17 = 100.0% |
| Latency mean / median | 4059 / 3744 ms |
| Tokens input / output / total | 12,882 / 4,123 / 17,005 |
| Chi phí thực tế theo `usage.cost` | $0.0011231227 |

### Lỗi thực tế

- **d01:** TF-IDF trả p6/p13, gold định nghĩa nằm p4. Context không hỗ trợ định nghĩa; model nêu giới hạn nhưng có câu thiếu citation inline nên wrapper chuyển thành abstention. Về benchmark là false refusal; về grounding, abstain an toàn hơn bịa câu trả lời. Nguyên nhân chính: retrieval miss, sau đó validator xử lý uncited raw answer.
- **d03:** Top-3 p23/p21/p32 không có bảng chân trị p16. Model suy ra E=0 từ luật kéo theo ở p21 nhưng không gắn citation inline cho toàn bộ phép biến đổi; validator abstain. Đây là failure retrieval/context và citation formatting; policy không cho khôi phục bảng thiếu từ ngoài context.
- **d04, d06, d13, d14:** context chứa đáp án nguyên văn; raw model response có citation object với đúng chunk nhưng không chèn `[chunk_id]` trong câu. Citation validator từ chối toàn bộ response, dẫn tới bốn false refusals có thể khắc phục ở một run/config mới. Run d04 đơn lẻ trước đó trả lời đúng; run 17 câu hiện tại được giữ độc lập.

d16/d17 được model từ chối đúng; d17 có nhắc định lý Dijkstra với citation object nhưng không có inline ID, tuy nhiên không đưa số milliseconds nên abstention vẫn đúng. Metrics tự động là từ trace; grounded answer và citation semantic support là đánh giá thủ công theo audit file. Không chạy test hoặc thay benchmark/corpus.

## A1 — prompt citation rõ hơn và một lần sửa

A1 là run riêng, không thay baseline. Model/retriever/context/corpus giữ nguyên; chỉ hướng dẫn câu trả lời và chính sách repair thay đổi. Mỗi câu có một controller call, một final call và tối đa một repair call. Repair nhận nguyên context, không gọi retrieval lại; chỉ chấp nhận nếu JSON, citation inline, ID, source và page hợp lệ. Không tạo citation chỉ vì chunk xuất hiện trong context.

| Chỉ số | Baseline | A1 | Thay đổi |
|---|---:|---:|---:|
| Grounded Answer Rate (15) | 9/15 (60%) | 12/15 (80%) | +3 câu, +20 điểm % |
| False refusal (15) | 6/15 (40%) | 3/15 (20%) | giảm 3, −20 điểm % |
| Câu answered có citation structure hợp lệ | 9/9 | 12/12 | giữ 100%, coverage tăng 60% → 80% |
| Semantic citation support | 10/10 refs | 13/13 refs | mọi citation được audit đều được hỗ trợ |
| Abstention đúng d16/d17 | 2/2 | 2/2 | không đổi |
| Tool use | 17/17 | 17/17 | không đổi |
| Repair | — | 1 lần, thất bại | d14 vẫn abstain |
| Mean / median latency | 4059 / 3744 ms | 3627 / 3319 ms | A1 thấp hơn trong run này |
| Tokens | 17,005 | 20,772 | +3,767 |
| Chi phí API | $0.0011231227 | $0.0013042941 | +$0.0001811714 |

Grounded Answer Rate A1 = 12/15 dựa trên audit thủ công 17 câu, không suy từ citation validity. Citation structure 12/12 và semantic support 13/13 cũng là các phép đo riêng. Mọi retrieval giữ đúng TF-IDF Top-3 và C0; traces, manifest và metrics có trong `starter/results/discrete_math_v2/agent-a1-dev-20261116T055814596229Z/`.

### Lỗi A1 và phân loại root cause

- d01 và d03 vẫn abstain vì gold chunk không nằm trong Top-3/context. Đây là **retrieval_failure** theo audit hậu nghiệm; agent trace ghi `model_abstention`, vì retrieval returned unrelated but nonempty chunks.
- d14 vẫn false refusal. p11 có đủ ba traversal methods. Raw answer có hai câu, citation chỉ ở câu thứ hai; một repair lặp lại cùng lỗi, nên wrapper abstain với `repair_failure`. Cần A2/agent variant phân câu và gắn citation cho từng câu, hoặc rút gọn thành một câu có citation.
- d04, d06, d13 được trả lời đúng với citation inline và source/page hợp lệ mà không cần repair. Đây là giảm false refusal thực tế, không phải chỉ sửa nhãn.

### Đề xuất A2: retrieval cho d01/d03

Chưa triển khai A2. Thí nghiệm kế tiếp nên giữ nguyên 332 chunks, model và C0, tạo một retrieval run riêng so sánh TF-IDF Top-3 baseline với query expansion/symbol-aware lexical retrieval: chuẩn hóa cách hỏi định nghĩa mệnh đề cho d01 và giữ ký hiệu `E(p,q,r)`, toán tử, hàng giá trị cùng cụm “bảng chân trị” cho d03. Chỉ query gốc/biến thể được gửi retrieval, tuyệt đối không dùng gold chunk để filter. Đo recall/context hit và latency dev trước khi dùng API; nếu context vẫn thiếu bảng d03 thì agent phải abstain. Không chạy test.
