# So sánh Dense, TF-IDF và Hybrid RRF trên corpus V2 — dev

## Phạm vi và dữ liệu

- Corpus: đúng **332** chunk trong `chunks_v2.json` đã duyệt, SHA-256 `979a0baaf2f34735592bde1aeaf2bdb29b5a8f336f3f0bcb3fee699056f57990`. Cả ba phương pháp dùng cùng ID, text, source, page và metadata; cờ `needs_review` không bị bỏ hoặc sửa.
- Dense truy vấn thực tế PostgreSQL/pgvector strategy `D07_discrete_math_v2`, model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, vector **384** chiều. Trước và sau chạy: A_fixed **287**, B_paragraph **296**, V2 **332** hàng, cùng chiều 384.
- TF-IDF xây chỉ mục trong bộ nhớ từ text của đúng 332 chunk V2. Tokenizer hiện tại là Unicode `\w+`, chữ thường, chưa tách từ tiếng Việt. Không ghi database hay embed lại corpus.
- Hybrid lấy tối đa **20** ứng viên từ mỗi nhánh, cộng `1/(60 + rank)` cho mỗi lần một chunk xuất hiện, rồi trả Top-3. `score` của Dense là cosine similarity, TF-IDF là cosine TF-IDF, Hybrid là điểm RRF; không so sánh trị tuyệt đối giữa các thang này.

## Benchmark và cách chấm

- [Dev](../../data/benchmark_v2_dev.json): **15** câu có đáp án + **2** câu thiếu bằng chứng. [Test](../../data/benchmark_v2_test.json): **5** câu có đáp án + **2** câu thiếu bằng chứng. Hash của từng split nằm trong [manifest](../../data/benchmark_v2_manifest.json). Test **chưa được đưa vào retrieval hoặc dùng để chọn cấu hình**.
- Mọi truy vấn dev dùng nguyên câu hỏi tiếng Việt, `filters={}`. Gold, đáp án và vị trí evidence chỉ được dùng **sau** khi retrieval để chấm; không truyền vào embedding query, TF-IDF hoặc SQL filter.
- Hit@1/Evidence Hit@3 yêu cầu đúng chunk ID, source ID, trang vật lý và chuỗi evidence trong text (chỉ gộp khoảng trắng do PDF xuống dòng). Context Evidence Rate yêu cầu evidence đó nằm trong context cuối, được pack từ Top-3 với ngân sách **800 ký tự Unicode gồm citation header**. Mẫu số chỉ gồm 15 câu có đáp án. Đây là metric định vị evidence bằng chuỗi, **không phải kiểm tra thủ công câu trả lời có đủ căn cứ**.
- Hai câu Chương 2 có `needs_review` vì cờ trích xuất bảng. Evidence dùng để đặt câu d04/t02 đã đối chiếu trực quan PDF trang 29 và 36; cờ chất lượng trong V2 và trace vẫn giữ nguyên. Các gold còn lại được đối chiếu với text V2, chưa có vòng chấm thủ công toàn bộ trang PDF.

## Kết quả dev thực đo

| Phương pháp | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Median retrieval | P95 retrieval |
|---|---:|---:|---:|---:|---:|
| Dense pgvector | **9/15 (60,0%)** | **11/15 (73,3%)** | **11/15 (73,3%)** | **65,6 ms** | 105,0 ms |
| TF-IDF | **12/15 (80,0%)** | **13/15 (86,7%)** | **13/15 (86,7%)** | **2,3 ms** | 5,2 ms |
| Hybrid RRF | **11/15 (73,3%)** | **13/15 (86,7%)** | **12/15 (80,0%)** | **71,8 ms** | 80,1 ms |

Mỗi phương pháp trả 51 hit trên 17 truy vấn dev, không có truy vấn rỗng. Hai câu thiếu evidence **không** được tính vào ba tỷ lệ trên. Cả ba vẫn trả các chunk liên quan chủ đề cho d16/d17; sự có mặt của hit không chứng minh có thể trả lời, và chưa có agent để chấm abstention.

Thời gian khởi động gồm tải model, xác minh 332 hàng DB và tạo TF-IDF là **15,548 giây**; riêng tạo TF-IDF **0,015 giây**. Latency trong bảng đo một lần chạy cục bộ trên máy hiện tại, gồm query embedding và truy vấn SQL cho Dense/Hybrid, không gồm khởi động. Phí API trực tiếp bằng **0 USD** vì dùng model local; chi phí máy/điện **chưa đo**. Xem [metrics tương thích PowerShell](../../starter/results/discrete_math_v2/dev-20261116T043019037173Z/metrics_portable.json), [Top-3 traces](../../starter/results/discrete_math_v2/dev-20261116T043019037173Z/traces.json) và [run manifest](../../starter/results/discrete_math_v2/dev-20261116T043019037173Z/run_manifest.json). `metrics.json` ban đầu được giữ nguyên; bản portable chỉ đổi khóa `n/N` thành `count/total` để PowerShell đọc được. Các file trong `starter/results/` là dữ liệu local bị Git bỏ qua; chạy lại tạo thư mục mới.

## Lỗi và đánh đổi cụ thể

1. **d01 — định nghĩa mệnh đề:** TF-IDF không đưa chunk đúng `chuong-1-co-so-logic:p4:c1:v2` vào Top-3; Top-1 là chunk cây khung. Dense xếp evidence ở hạng 2, còn Hybrid ở hạng 1 nhờ chunk này có hạng 2 Dense và hạng 4 TF-IDF. Tokenizer hiện tại dễ bị từ chung trong câu hỏi chi phối; cần thử bỏ stopword/tách từ trên dev trong thí nghiệm riêng.
2. **d03 — bảng chân trị E(p,q,r):** Dense và TF-IDF đều bỏ lỡ bảng đúng trong Top-3. Hybrid tìm được `chuong-1-co-so-logic:p16:c1:v2` ở hạng 3, nhưng context 800 ký tự đã chứa hai hit trước nên không còn chỗ cho bảng. Vì vậy Evidence Hit@3 đúng, Context Evidence Rate sai. Đây là lỗi chọn context, không phải lỗi bảng gold.
3. **d05 — quan hệ thứ tự:** TF-IDF xếp định nghĩa đúng `chuong-3-quan-he:p23:c1:v2` hạng 1; Dense bỏ lỡ. RRF đưa các đoạn cùng chủ đề nhưng không chứa ba tính chất lên Top-3, nên Hybrid mất hit đúng của TF-IDF. RRF mặc định ưu tiên đồng thuận hai nhánh, kể cả khi cả hai cùng xếp cao đoạn tổng quan.
4. **d09 — đồ thị lưỡng phân:** TF-IDF xếp định nghĩa đúng `chuong-5-do-thi-phan-1:p24:c1:v2` hạng 1. Dense ưu tiên các bài tập/hình có `needs_review`; Hybrid theo các đoạn này và bỏ lỡ định nghĩa trong Top-3. Cờ chất lượng được hiển thị để người đọc nhận ra rủi ro nhưng chưa được dùng làm filter/rerank.

## Quyết định trên dev và phần còn thiếu

Theo ba metric evidence và latency đo trên dev, **TF-IDF Top-3 với context budget 800 ký tự** là ứng viên hiện tại cho cấu hình được chọn; Dense và Hybrid giữ làm đối chứng. Quyết định này được ghi trước khi chạy test, nhưng tiêu chí ưu tiên không được ghi thành artifact trước lần chạy dev đầu tiên. Không chỉnh RRF theo test. Nếu thử thêm cấu hình tokenizer/context trên dev, phải lưu run mới và chốt lại trước test.

- Chưa chạy **7 câu test**, chưa chấm context thủ công mức 0/1/2, câu trả lời agent, citation hợp lệ hoặc abstention. Retrieval hit không thay thế các phần này của [BENCHMARK.md](../../BENCHMARK.md).
- Cần kiểm tra thủ công các trường hợp `needs_review`, nhất là bảng/ma trận/hình và các gold chưa đối chiếu trực quan PDF. Corpus có **256/332** chunk mang cờ này; hai câu không đủ bằng chứng đã được kiểm tra trên toàn bộ V2, không chỉ Top-3.
- Cần thêm vòng dev có giả thuyết và đo lại cho tokenizer tiếng Việt, context packing và RRF trước khi khẳng định cấu hình tối ưu. Tài liệu Chương 3 dạng PPT/PPTX thứ 10 chưa có; quyền chia sẻ PDF và trích đoạn vẫn cần xác minh.
