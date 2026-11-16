# Day 7 — Agentic RAG

## LLM Agent V2 trên dev

Agent dùng TF-IDF Top-3 trên corpus V2 (332 chunk), C0 800 ký tự và Chat Completions tool calling. Xem [hướng dẫn cấu hình/chạy](starter/README.md) và [báo cáo dev](report/individual/agent_evaluation_dev.md). Chỉ chạy API sau khi kiểm tra quyền gửi tài liệu ra ngoài và đặt key, model, giá, ngân sách trong biến môi trường theo `.env.example`. Chưa có kết quả API thật; benchmark test chưa chạy.

**Bài cá nhân · Python 3.11+ · tiếp nối Day 6**

Dùng embedding và vector store từ Day 6 để xây một agent biết tìm bằng chứng, trả lời có nguồn và nhận biết khi không đủ thông tin. Bạn tự chọn kiến trúc, số tool và cách tổ chức retrieval.

> **Tùy chọn:** [Gợi ý dùng AI để lập trình](AGENT_SETUP.md) giúp bạn làm lab; phần này không bắt buộc và không tính điểm.

## Bài cần làm

![Agent tìm tài liệu trong kho Day 6 và trả lời có nguồn](assets/retrieval-pipeline.svg)

1. Kết nối dữ liệu, embedding và vector store Day 6.
2. Xây agent dùng model thật và ít nhất một khả năng truy xuất dữ liệu. Agent có thể dùng nhiều tool và nhiều lượt gọi.
3. Thử **ít nhất 3 phương pháp retrieval khác nhau**, trong đó có dense retrieval dùng vector store Day 6. Tự chọn các phương pháp còn lại; xem [gợi ý](GUIDE.md#2-thử-các-phương-pháp-retrieval).
4. Thử nhiều cấu hình, benchmark, phân tích lỗi và chọn cấu hình tốt trên **dev**; sau đó đánh giá trên **test**.

Benchmark tối thiểu có **24 câu**: dev gồm 15 câu có đáp án và 2 câu thiếu bằng chứng; test gồm 5 câu có đáp án và 2 câu thiếu bằng chứng. Xem [benchmark](BENCHMARK.md) và [rubric](RUBRIC.md).

## Thử thách nâng cao · +15 điểm

Index một tài liệu thực tế từ **100 trang** có bảng, ảnh và biểu đồ; xây agent truy xuất và trả lời các câu hỏi về nội dung đó. Hoàn thành [thử thách nâng cao](ADVANCED.md) và đạt **ít nhất 90% benchmark test** để nhận 15 điểm bonus. Phần cơ bản tối đa 85 điểm; toàn bài tối đa 100 điểm.

## Bắt đầu

1. Đọc [hướng dẫn](GUIDE.md), [rubric](RUBRIC.md) và [quy tắc](RULES.md).
2. Tạo repo cá nhân theo [cách nộp bài](SUBMISSION.md), chuẩn bị đầu ra Day 6 và model hỗ trợ tool calling.
3. Dùng hoặc thay thế [starter](starter/README.md); bạn cần kết nối model và vector store thật.
4. Chạy `python -m unittest discover -s tests -v`. Test mock chỉ kiểm tra code, không phải benchmark agent thật.

![Các bước thử nghiệm trên dev và đánh giá trên test](assets/experiment-loop.svg)

Nộp code, cách chạy, cấu hình, benchmark, trace và [báo cáo](report/individual/MSSV_HoTen.md). Thời gian ở [checkpoints](CHECKPOINTS.md) là gợi ý, có thể điều chỉnh theo lớp và phạm vi thử nghiệm.

## Corpus Cấu trúc rời rạc V2

Pipeline [ingestion v2](starter/README.md#audit-ingestion-v2-cho-cấu-trúc-rời-rạc) tạo `starter/data/indexed/discrete_math/chunks_v2.json` và [báo cáo v1/v2](report/individual/ingestion_v2_review.md) từ các PDF trong `data/discrete_math/raw/`. Bản v2 giữ `source_id`, đường dẫn nguồn và trang vật lý, đồng thời đánh dấu nội dung công thức, ma trận, hình hoặc bảng chưa trích xuất chắc chắn bằng `extraction_quality: "needs_review"`.

Sau khi người dùng duyệt, V2 đã được index thành strategy riêng `D07_discrete_math_v2` trong PostgreSQL/pgvector Day06. Xem [lệnh chạy](starter/README.md#index-v2-thử-nghiệm) và [báo cáo index, smoke retrieval](report/individual/v2_index_smoke.md). V1/V2 JSON và vector A/B được giữ nguyên; chưa chạy benchmark test.

Ba phương pháp [Dense, TF-IDF, Hybrid RRF](starter/README.md#ba-phương-pháp-retrieval-trên-v2-và-benchmark-dev) đã được so sánh trên 17 câu dev của V2. Xem [benchmark đã tách dev/test](data/benchmark_v2_manifest.json) và [báo cáo kết quả dev](report/individual/retrieval_v2_dev_comparison.md). Tập test 7 câu chưa được truy vấn.

[Thí nghiệm Context Engineering trên dev](starter/README.md#context-engineering-trên-dev) so sánh C0/C1 từ cùng Top-3 TF-IDF đã lưu; có [báo cáo](report/individual/context_engineering_dev.md), metrics, trace và audit thủ công 17 câu. Chưa chạy test hoặc xây LLM Agent.
