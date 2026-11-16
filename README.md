# Lab 07 — Agentic RAG

## Kết quả nộp bài

Pipeline dùng 332 chunks Cấu trúc rời rạc V2. Cấu hình được chọn trên dev: **Agent A1 + TF-IDF Top-3 (R0) + C0 800 ký tự + GLM-5.3-Flash qua OpenRouter**.

| Split | Grounded Answer Rate | Abstention đúng | Tool use | Chi phí API |
|---|---:|---:|---:|---:|
| Dev, 17 câu | 12/15 (80%) | 2/2 | 17/17 | $0.0013042941 |
| Test, 7 câu, chạy một lần | 3/5 (60%) | 2/2 | 7/7 | $0.0006918935 |

Hai false refusal trên test (t02, t04) có evidence trong context; câu trả lời draft bị citation validator từ chối do thiếu citation inline ở một câu. Không điều chỉnh cấu hình sau test. Xem [báo cáo cá nhân](report/individual/2A202603812_NguyenDucNhat.md), [audit final test](report/individual/agent_final_evaluation_test.md) và [checklist nộp bài](SUBMISSION_CHECKLIST.md).

## Thành phần và báo cáo

- [Hướng dẫn cài đặt/chạy](starter/README.md)
- [Benchmark và cách chấm](BENCHMARK.md), [rubric](RUBRIC.md), [quy tắc](RULES.md), [hướng dẫn bài](GUIDE.md)
- [So sánh Dense, TF-IDF và Hybrid RRF](report/individual/retrieval_v2_dev_comparison.md)
- [Context C0/C1](report/individual/context_engineering_dev.md)
- [A1 dev](report/individual/agent_evaluation_dev.md)
- [A2 retrieval dev](report/individual/retrieval_a2_dev.md)
- [Final test audit](report/individual/agent_final_evaluation_test.md)
- [Metrics tổng hợp đã loại bỏ nội dung nguồn](artifacts/final_evaluation_public.json)

## Dataset và quyền sử dụng

Corpus V2 được trích từ 9 PDF (389 trang vật lý có trong thư mục nguồn), tạo 332 chunks. Bộ benchmark gồm 17 câu dev (15 answerable, 2 thiếu evidence) và 7 câu test (5 answerable, 2 thiếu evidence). Model embedding: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 chiều; vector V2 nằm trong PostgreSQL 16 + pgvector, strategy riêng `D07_discrete_math_v2`. Các strategy A/B của Lab 06 được giữ nguyên.

Chỉ có 9 PDF trong thư mục nguồn; file PPT/PPTX thứ 10 dự kiến cho Chương 3 chưa có để đối chiếu. Công thức, ma trận, bảng và hình có giới hạn trích xuất; 256/332 chunk mang `needs_review`. **Quyền phân phối PDF và trích đoạn vẫn cần xác minh.** Không đưa PDF, chunks, raw traces/context hoặc secrets lên GitHub trước khi xác minh quyền. Các file benchmark hiện được Git theo dõi và chứa evidence text trích từ nguồn; xem checklist trước khi public.

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
python -m compileall -q starter tests
git diff --check
```

Artifacts đầy đủ có nội dung retrieved/context/API nằm trong `starter/results/` và bị ignore có chủ đích; metrics tổng hợp sạch được lưu trong `artifacts/`. Không force-add raw results. Final test đã chạy một lần; không chạy lại `starter/run_agent_a1_test.py`.
