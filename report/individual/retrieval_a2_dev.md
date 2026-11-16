# A2 — Cải thiện retrieval (dev only)

## Phạm vi và tính toàn vẹn

Thí nghiệm chạy offline trên 332 chunks V2 với 17 câu dev (15 câu có đáp án, 2 câu thiếu bằng chứng). R0 lấy Top-3 từ trace TF-IDF gốc đã khóa; R1 và R2 chạy TF-IDF trên cùng corpus V2. Cả ba được đóng gói bằng C0, tối đa 800 ký tự Unicode, để đo bằng chứng trong cùng một context budget.

Không mở benchmark test; không gọi OpenRouter/LLM; không truy vấn hoặc ghi PostgreSQL; không tạo embedding; không sửa corpus hay benchmark. Truy hồi chỉ nhận câu hỏi, không nhận gold, đáp án, ID/trang gold hoặc filter. Gold chỉ được dùng sau truy hồi để chấm. Mỗi hit giữ nguyên ID, source, page và metadata, bao gồm `extraction_quality: needs_review`.

## Cấu hình

- **R0:** TF-IDF baseline Top-3 đã lưu. Dùng retrieval latency trong trace baseline; C0 được đóng gói lại thống nhất.
- **R1:** TF-IDF Top-3 trên câu hỏi được mở rộng bằng từ vựng tiếng Việt/Anh tổng quát cho các khái niệm Discrete Math. Mở rộng chỉ được kích hoạt khi cụm thuật ngữ hiện diện trong câu hỏi; không có luật theo câu benchmark hoặc vị trí gold.
- **R2:** hợp nhất candidate Top-30 từ TF-IDF truy vấn gốc và truy vấn mở rộng, sau đó rerank bằng Reciprocal Rank Fusion với `k=60`, lấy Top-3. Đây là candidate expansion lexical, không kết hợp Dense trong lần chạy này.

## So sánh dev

| Variant | Hit@1 / 15 | Evidence Hit@3 / 15 | Context Evidence Rate / 15 | Median retrieval (ms) | Mean retrieval (ms) | Mean context chars | Ghi chú |
|---|---:|---:|---:|---:|---:|---:|---|
| R0 | 12 (80.0%) | 13 (86.7%) | 13 (86.7%) | 2.307 | 2.497 | 701 | Baseline |
| R1 | 11 (73.3%) | 13 (86.7%) | 12 (80.0%) | 1.329 | 1.408 | 723.7 | Không thêm evidence trong Top-3; mất một evidence ở context C0 |
| R2 | 12 (80.0%) | 13 (86.7%) | 13 (86.7%) | 2.542 | 2.765 | 706.2 | Bằng R0 ở ba metric evidence; đưa d14 về Top-1 |

> **Diễn giải latency:** R0 được lấy từ phép đo trong trace gốc; R1/R2 đo cục bộ trong lần chạy này, không gồm khởi tạo TF-IDF index. Đây là latency retrieval, không gồm khởi động ứng dụng. Chênh lệch vài phần ms trong benchmark nhỏ này không đủ để kết luận R1/R2 nhanh hơn R0. Packing C0 trung bình khoảng 0.02 ms mỗi câu; chi phí API là $0.

Không có câu nào trả về rỗng. Mỗi cấu hình có 2/2 câu thiếu bằng chứng với kết quả truy hồi không rỗng; điều đó không đồng nghĩa có chứng cứ trả lời. Top-3 có lần lượt 23/22/23 hit mang cờ `needs_review` (R0/R1/R2); context answerable chọn 9/9/8 chunks `needs_review` trong 30 chunk được đóng gói. Các cờ được giữ nguyên để downstream agent thận trọng.

## Audit context và lỗi

Context Evidence Rate là kiểm tra xem chunk chứa nguyên văn evidence gold có được đưa vào context C0 hay không. Đây là metric định vị evidence, không phải đánh giá câu trả lời sinh bởi LLM và không thay thế đánh giá grounding của Agent. Audit chất lượng context theo ba nhóm: **evidence rõ trong text và chunk `ok`** (R0/R1/R2: 12/11/12 câu), **evidence có trong text nhưng chunk mang `needs_review`** (1/1/1), **không có evidence trong context** (2/3/2). Cờ review không bị bỏ qua; nội dung `needs_review` cần kiểm tra phần text có đọc được hay phụ thuộc hình/công thức.

- **d01 — định nghĩa mệnh đề:** R0/R1/R2 đều không lấy chunk trang 4 chứa câu định nghĩa vào Top-3. Chúng lấy nội dung logic khác (R0: trang 6/13; R1: trang 17/5; R2: trang 13/6). Đây là retrieval failure, không phải lỗi đóng gói.
- **d03 — hàng bảng chân trị:** cả ba đều không lấy evidence trang 16 vào Top-3. Top-3 bị hút vào ví dụ biến đổi biểu thức và luật logic ở trang 23/21/32; các chunk có `needs_review`, bảng cần thiết không có trong context. Không thể suy ra giá trị hàng bị thiếu.
- **d12 — định lý Euler:** cả ba có evidence trong Top-3. R1 xếp chunk đúng evidence thấp hơn và C0 không đưa nó vào context, nên Context Evidence Rate giảm một câu. R0/R2 giữ evidence trong context.
- **d14 — duyệt cây nhị phân:** R0 xếp chunk liệt kê ba kiểu duyệt ở Top-1; R1 đưa tiêu đề chương lên trước và đẩy evidence xuống Top-2; R2 khôi phục chunk evidence lên Top-1. Đây là cải thiện thứ hạng của R2 cho câu này, nhưng không tăng Hit@1 tổng thể so với R0.
- **d16 — thiếu dữ kiện giá áo:** cả ba trả về ví dụ đếm áo ở trang 29 cùng chunk không liên quan. Nội dung nói số lượng áo và phép cộng, không có đơn giá được hỏi. Không có evidence giá; agent phải abstain.
- **d17 — thiếu thời gian chạy Dijkstra:** cả ba có chunk nói Dijkstra tìm đường đi ngắn nhất ở trang 43, không cung cấp thời gian thực thi. Không được biến phát biểu về tính đúng đắn thuật toán thành thời gian chạy; agent phải abstain.

Trong 13/15 context có chứa gold của R0/R2 (12/15 R1), citation provenance trong trace truy được trực tiếp bằng chunk ID, source và page canonical của V2. Trường hợp evidence thiếu trong context được ghi là thiếu, không gán citation.

## Kết luận và đề xuất

R1 không phù hợp để thay R0: không tăng Evidence Hit@3, giảm Hit@1 một câu và giảm Context Evidence Rate một câu. R2 đạt ngang R0 ở Hit@1, Evidence Hit@3 và Context Evidence Rate; nó sửa thứ hạng d14 nhưng chưa cải thiện tổng thể. Vì vậy **giữ R0/TF-IDF làm cấu hình đề xuất cho Agent**, chưa chuyển A2 sang API thật. R2 có thể được giữ làm ứng viên so sánh, nhưng chưa có lợi ích dev tổng thể đủ để chấp nhận độ phức tạp thêm. Cả d01 và d03 cần một thí nghiệm retrieval khác; không có căn cứ để coi vấn đề đã được giải quyết.

## Tệp kết quả

Run chính: `starter/results/discrete_math_v2/retrieval-a2-dev-20261116T072332985851Z/`

- `metrics.json`: số liệu tổng hợp.
- `traces.json`: 51 trace (17 câu × R0/R1/R2), gồm Top-3, điểm/rank, context C0, thời gian và cờ evidence sau retrieval.
- `run_manifest.json`: hash corpus/benchmark, cấu hình và xác nhận test/API/database/embedding không được dùng.

Các run `retrieval-a2-dev-20261116T071940771208Z` và `retrieval-a2-dev-20261116T072055123775Z` là lần chạy sơ bộ. Run đầu đo nhầm R0 latency bằng lookup trace; run thứ hai có metrics tương tự nhưng được thay bằng run chính sau khi bổ sung kiểm tra hash manifest và đúng kích thước split. Không dùng hai run sơ bộ để báo cáo; dữ liệu được giữ nguyên.
