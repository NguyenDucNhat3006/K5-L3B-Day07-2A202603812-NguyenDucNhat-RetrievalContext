# Báo cáo cá nhân Lab 07 — Agentic RAG

**MSSV:** 2A202603812  
**Sinh viên:** NguyenDucNhat  
**Repository:** `K5-L3B-Day07-NguyenDucNhat-2A202603812-Retrieval-Context-Engineering` (current `origin` repository)

> Danh tính ghi theo repository name và Git remote; `STUDENT.md` chỉ lưu MSSV và tên đúng cách viết đã xác minh trong slug, không tự thêm dấu tiếng Việt hay chi tiết cá nhân khác.

## 1. Dataset, ingestion và benchmark

Corpus là tài liệu Cấu trúc rời rạc trích xuất từ 9 PDF có trong thư mục nguồn, tổng cộng 389 trang vật lý. Danh sách nguồn dự kiến có 10 tệp; tệp PPT/PPTX Chương 3 chưa hiện diện nên chưa thể đối chiếu bản PDF/PPT trùng nhau. Chunk V1 có 420 đoạn; V2 được duyệt giữ 332 đoạn, loại chunk chỉ là số trang/header/footer và cải thiện ranh giới semantic. V2 bảo toàn ID, source ID, đường dẫn source và page, thêm subject/chapter/content type/extraction quality.

Trong V2 có 256/332 chunk mang `needs_review`. PDF parser có thể làm mất ký hiệu toán học, cột bảng, cấu trúc ma trận hoặc thông tin nằm trong hình. Một bảng chân trị được trích thành Markdown khi cấu trúc đọc được; phần không đáng tin cậy được gắn cờ thay vì tái tạo. Đây là cờ cần người kiểm tra, không phải kết luận rằng mọi đoạn đó sai.

Vector V2 dùng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 chiều) trong PostgreSQL 16 + pgvector, cosine similarity, strategy riêng `D07_discrete_math_v2`. Index V2 không ghi đè A_fixed hoặc B_paragraph của Lab 06. Benchmark giữ nguyên hash: dev 15 câu answerable + 2 câu thiếu evidence; test 5 + 2. Gold chỉ được dùng sau retrieval để đánh giá.

**Phạm vi quyền dữ liệu:** theo xác nhận của người nộp, giáo viên đã cho phép sử dụng tài liệu trong phạm vi học phần/Lab 07 và nộp bài cho giảng viên. Không suy rộng xác nhận này thành quyền công khai PDF đầy đủ, toàn bộ chunks hoặc evidence excerpts. Manifest benchmark vẫn ghi `source_redistribution_permission: requires verification`, đúng với trạng thái quyền tái phân phối công khai chưa được xác nhận. Repo hiện public và có excerpt đã track; cần đối chiếu từng artifact với phạm vi giáo viên cho phép trước khi coi việc public repository là phù hợp. Quyền gửi context tới OpenRouter trong lần đánh giá là xác nhận riêng đã ghi trong run manifest, không phải căn cứ cấp quyền public.

## 2. Ba phương pháp retrieval

Dense dùng embedding query MiniLM và pgvector thực tế. TF-IDF tạo index lexical trong bộ nhớ trên cùng 332 chunks; tokenizer Unicode hiện chưa xử lý chuyên biệt tách từ tiếng Việt. Hybrid lấy đến 20 candidate mỗi nhánh và dùng Reciprocal Rank Fusion `1/(60 + rank)`. Ba phương pháp dùng chung chunk IDs/metadata và được so sánh trên cùng dev split.

| Dev retriever | Hit@1 / 15 | Evidence Hit@3 / 15 | Context Evidence Rate / 15 | Median retrieval |
|---|---:|---:|---:|---:|
| Dense pgvector | 9 (60.0%) | 11 (73.3%) | 11 (73.3%) | 65.6 ms |
| TF-IDF | 12 (80.0%) | 13 (86.7%) | 13 (86.7%) | 2.3 ms |
| Hybrid RRF | 11 (73.3%) | 13 (86.7%) | 12 (80.0%) | 71.8 ms |

Hit@1 và Evidence Hit@3 kiểm tra vị trí evidence gold trong ranking. Context Evidence Rate kiểm tra evidence có vào context sau giới hạn 800 ký tự. Các chỉ số định vị này không thay thế đánh giá câu trả lời hoặc grounding semantic.

## 3. Context Engineering C0/C1

C0 pack Top-3 theo thứ hạng gốc, giữ chunk và citation đầy đủ trong tối đa 800 ký tự Unicode. C1 chọn tập con evidence-aware từ cùng Top-3 theo rank, content type, query cue và extraction risk; không dùng gold.

| Packing | Context Evidence Rate | Audit context mức 0 / 1 / 2 | Điểm trung bình /2 | Ký tự trung bình |
|---|---:|---:|---:|---:|
| C0 | 13/15 (86.7%) | 2 / 0 / 13 | 1.733 | 701 |
| C1 | 12/15 (80.0%) | 2 / 1 / 12 | 1.667 | 700.2 |

C0 được chọn vì có evidence coverage và audit context dev tốt hơn trong run hiện có. `needs_review` được giữ để agent chỉ dùng phần text đọc được và không suy luận cấu trúc thiếu.

## 4. Agent architecture và tool calling

Agent A1 dùng OpenRouter Chat Completions function calling. Controller quyết định gọi `search_discrete_math`; tool truy vấn TF-IDF Top-3 R0 trên V2 rồi pack context C0. Model sinh câu trả lời JSON với citation inline `[chunk_id]`; verifier đối chiếu chunk ID/source/page và citation coverage trong context. Khi output sai cấu trúc, A1 cho tối đa một lượt repair dùng đúng context cũ. Đây là tool calling thật, không phải RAG pipeline cố định. Verifier không xác nhận entailment, vì vậy citation semantic được audit thủ công.

Model request: `z-ai/glm-5.3-flash:floor` qua OpenRouter; provider endpoint có thể được chọn theo route. `.env` chứa key/config, bị ignore và không được đưa lên Git. Traces local ghi quyết định controller, tool call, hits, context, output, citations, latency, token usage và cost.

## 5. Cải thiện A1 và A2

A0 đạt 9/15 grounded answer trên dev. Một lượt retrospective duy nhất trên cùng test đã mở đạt 0/5 GAR và false refusal 5/5; không phải đánh giá độc lập. A1 official final test vẫn là 3/5 GAR, false refusal 2/5, và không bị chạy lại hoặc sửa. Trên dev, A1 đạt 12/15 (80%) và false refusal 3/15; giữ nguyên retrieval/context/model. A1 không chữa được lỗi d01/d03 do thiếu evidence trong Top-3, còn d14 là citation repair failure.
A0 baseline recovery and test: the saved dev run used `run_v2_agent()`/`agent_v2.SYSTEM`, model `z-ai/glm-5.3-flash:floor`, TF-IDF Top-3 and C0 800. A user-approved A0 retrospective pass on the already-opened test completed once, scoring 0/5 GAR, with correct abstention 2/2 and tool use 7/7. It is not an independent test and does not change official A1 test GAR 3/5. Prompt/tool hashes match the recovered historical revisions; exact A0 dev runner/API adapter snapshot is not provable. The retrospective pass used 14 API calls and 7,049 tokens, with mean/median latency 3.720/3.577 seconds and actual cost $0.0004882121. See the [A0 case audit and comparison](evaluation.md#a0-retrospective-test-audit) and [plan/execution record](evaluation.md#a0-retrospective-protocol-and-provenance).

A2 so sánh trên dev với R0 gốc, R1 query expansion bằng từ vựng Discrete Math chung, R2 mở rộng candidate Top-30 từ truy vấn gốc/mở rộng rồi rerank bằng RRF. Không hardcode câu hỏi hoặc vị trí gold. Kết quả:

| Variant | Hit@1 / 15 | Evidence Hit@3 / 15 | Context Evidence Rate / 15 |
|---|---:|---:|---:|
| R0 | 12 (80.0%) | 13 (86.7%) | 13 (86.7%) |
| R1 | 11 (73.3%) | 13 (86.7%) | 12 (80.0%) |
| R2 | 12 (80.0%) | 13 (86.7%) | 13 (86.7%) |

R1 không cải thiện baseline. R2 đưa d14 lên Top-1 nhưng không tăng metric tổng thể; giữ R0 vì đơn giản hơn. Test không dùng để chọn hoặc chỉnh variant.

## 6. Kết quả Agent dev/test

| Metric | Dev A1 | Test A1 |
|---|---:|---:|
| Grounded Answer Rate | 12/15 (80%) | 3/5 (60%) |
| Citation structure hợp lệ trong câu trả lời cuối | 12/12 | 3/3 |
| Citation semantic support | 13/13 citation references theo audit dev | 3/3 citation references trong câu trả lời cuối trên test có hỗ trợ semantic theo audit; draft t02/t04 có evidence nhưng bị verifier từ chối |
| Abstention đúng | 2/2 | 2/2 |
| False refusal | 3/15 (20%) | 2/5 (40%) |
| Tool use | 17/17 | 7/7 |
| Mean / median latency | 3.627 / 3.319 s | 4.952 / 4.502 s |
| Tokens | 20,772 | 10,363 |
| LLM calls | 35 | 16 |
| Actual API cost | $0.0013042941 | $0.0006918935 |

Final test chạy đúng một lần, 7/7 câu hoàn tất. 16 API calls gồm 2 lượt repair; 10,363 tokens và $0.0006918935 theo OpenRouter response usage, dưới cap $0.10/21 calls/20,000 tokens. Cấu hình request dùng alias `:floor`; response ghi model base `z-ai/glm-5.3-flash`, providers được chọn Relace và Wafer. Không gọi API lại sau đó.

## 7. Phân tích lỗi

- **d01:** TF-IDF và R0 bỏ lỡ chunk định nghĩa mệnh đề ở trang 4; Top-3 chứa đoạn chủ đề logic khác. A1 abstain an toàn nhưng vẫn là false refusal. Cần xử lý query lexical/từ chung trên dev.
- **d03:** evidence là một hàng cụ thể của bảng chân trị ở trang 16 nhưng TF-IDF Top-3 không lấy được. Các đoạn công thức/truth-table liên quan có lỗi extraction; context không đủ và agent nên abstain.
- **d14:** A1 answer dựa trên evidence về ba kiểu duyệt cây nhưng citation repair thất bại; retrieval có evidence. A2 R2 đưa chunk lên Top-1 nhưng tổng dev retrieval không tăng.
- **t02:** trang evidence đã có trong Top-1 và C0; draft model trả lời đúng mức “ít nhất 3” nhưng câu giải thích tiếp theo thiếu citation inline. Repair viết lại biểu thức thành `[20/7]`, khiến citation parser nhầm ngoặc vuông toán học là citation; lượt repair vẫn không qua validator, agent abstain.
- **t04:** định lý cần thiết nằm trong Top-1/C0 và draft trả lời đúng, nhưng có câu paraphrase không gắn inline citation. Repair lặp lại lỗi uncited sentence; agent abstain.

Hai lỗi test là false refusal từ output/validator, không phải retrieval miss. Chúng được ghi nhận sau test; không thay mã, prompt hoặc kết quả final run.

## 8. Hạn chế, tái lập và artifacts

- Các bảng, hình, ma trận và ký hiệu font tùy biến có thể mất cấu trúc; 256 chunks `needs_review` đòi hỏi kiểm tra PDF thủ công.
- Chưa có PPT/PPTX Chương 3 thứ 10 để xác minh trùng lặp nguồn.
- Bộ tokenizer TF-IDF đơn giản; retrieval kết quả còn phụ thuộc tách từ tiếng Việt.
- Citation structure không tự chứng minh claim được nguồn hỗ trợ; audit test đã đọc trang PDF nguồn và đối chiếu ID/source/page.
- Không thực hiện thử thách nâng cao 100 trang; không tuyên bố đạt bonus.
- Traces đầy đủ chứa raw query/context/source text và nằm trong `starter/results/` bị ignore. Chỉ dùng metrics/audit sanitized trong `artifacts/` khi chuẩn bị public; các benchmark JSON hiện được track vẫn chứa evidence excerpts và cần xác minh quyền.

Các báo cáo chi tiết: [retrieval dev](experiments.md#dense-tf-idf-and-hybrid-rrf-dev-comparison), [context dev](experiments.md#context-engineering-c0-and-c1), [A1 dev](experiments.md#a1-agent-dev-evaluation-and-improvement-analysis), [A2 dev](experiments.md#a2-retrieval-variants-r0-r1-and-r2), [final test audit](evaluation.md#a1-official-final-test-evaluation). Hướng dẫn lệnh ở [starter README](../../starter/README.md); kết quả public-safe ở [artifacts summary](../../artifacts/final_evaluation_public.json). Run manifest test local: `starter/results/discrete_math_v2/agent-a1-final-test-20261116T082303799998Z/manifest.json`.
