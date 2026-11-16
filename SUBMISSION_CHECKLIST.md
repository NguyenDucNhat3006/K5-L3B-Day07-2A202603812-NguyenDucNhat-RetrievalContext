# Checklist chuẩn bị nộp Lab 07

Checkpoint Git gần nhất sau khi fetch: local `main` và `origin/main` cùng trỏ tới `98c620049214357f40fd6c32d4e2cae06b6ef01c` (0 ahead/behind). Remote canonical hiện là `NguyenDucNhat3006/K5-L3B-Day07-NguyenDucNhat-2A202603812-Retrieval-Context-Engineering`, GitHub visibility là public. Hiện có thay đổi chuẩn bị submission trong worktree chưa commit/push theo yêu cầu. Commit `98c6200` đã tồn tại trên remote; agent không tạo commit hoặc push trong lượt này.

## Đối chiếu yêu cầu/rubric

| Yêu cầu | Trạng thái | Bằng chứng / việc còn lại |
|---|---|---|
| Dữ liệu Day 6, embedding, vector store | Đạt | V2 332 chunks, MiniLM multilingual 384 chiều, PostgreSQL 16 + pgvector, strategy riêng; A/B Lab 06 giữ nguyên. Xem `report/individual/v2_index_smoke.md`. |
| Dataset và benchmark | Đạt có điều kiện | Dev 17 (15+2), test 7 (5+2), manifest/hash có sẵn; test đã chạy một lần. Người nộp xác nhận giáo viên cho phép sử dụng tài liệu cho Lab 07/nộp bài; phạm vi này không tự cho phép public benchmark excerpts. |
| Bao phủ nguồn | Thiếu | Corpus hiện có 9 PDF/389 trang vật lý, trong khi kiểm kê kỳ vọng 10 files. Bản PPT/PPTX Chương 3 chưa có để đối chiếu PDF/PPT trùng. |
| Ba phương pháp retrieval, gồm Dense | Đạt | Dense pgvector, TF-IDF, Hybrid RRF dùng cùng V2; có rank/score/source/page/filter và lỗi trong báo cáo dev. |
| Agent thật, tool traces và context | Đạt | A1 dùng OpenRouter tool calling thật, R0 TF-IDF Top-3, C0 800 ký tự, citation check và tối đa một repair. |
| Evaluation | Đạt | Retrieval/context và A1 được đánh giá dev; final Agent test 7 câu có metrics tự động, audit thủ công, hashes và traces local. Test được chạy đúng một lần. |
| Thử nghiệm cải thiện và phân tích lỗi | Đạt | C0/C1; A0→A1; A2 R0/R1/R2; phân tích lỗi d01, d03, d14, t02, t04. R1/R2 không được mô tả là cải thiện khi metric không tăng. |
| Grounding/citation/abstention | Đạt | Citation structure được phân biệt với support semantic; t02/t04 là false refusals sau repair; t06/t07 abstain đúng. |
| Tái lập và báo cáo | Đạt có điều kiện | README, code, tests, report cá nhân, sanitized metrics và public manifest có. Raw run manifests/traces dưới `starter/results/` bị ignore; chỉ đưa lên nơi được phép. |
| Thử thách nâng cao 100 trang | Chưa thực hiện | Không tuyên bố bonus 15 điểm. |
| Nguồn và quyền phân phối | **Đạt có điều kiện cho course submission; public scope cần xác minh** | Theo xác nhận người nộp, giáo viên cho phép dùng tài liệu cho Lab 07/nộp giảng viên. Không suy rộng thành license hoặc quyền công khai PDF đầy đủ/corpus/excerpts; repo hiện public nên cần xác nhận thêm quyền đối với từng artifact trích nguồn. |

## Báo cáo cá nhân và thông tin sinh viên

 `STUDENT.md` đã được tạo với MSSV `2A202603812` và tên `NguyenDucNhat` theo đúng repository name/Git remote đã xác minh; không tự suy đoán dấu tiếng Việt hay thông tin cá nhân khác. Báo cáo đã lưu tại `report/individual/2A202603812_NguyenDucNhat.md`. `report/individual/MSSV_HoTen.md` vẫn là mẫu gốc.

## Git, dữ liệu và bí mật

- `.env` và `.env.*` được ignore; chỉ `.env.example` được track, không chứa giá trị key.
- Raw PDFs không được Git track; `data/discrete_math/raw/` bị ignore.
- V1/V2 JSON và run outputs trong `starter/data/`, `starter/results/` bị ignore.
- Detailed A1 audit JSON và d04 API smoke report được ignore rõ ràng vì có thể chứa source-derived content; dùng báo cáo/sanitized artifacts thay thế khi public.
- GitHub repo hiện là **public**. Người nộp xác nhận giáo viên cho phép dùng tài liệu trong phạm vi Lab 07/nộp bài; chưa có xác nhận rằng quyền đó bao gồm public distribution. Git history track `data/benchmark_v2_dev.json`, `data/benchmark_v2_test.json`, `data/benchmark_v2_manifest.json`; hai benchmark chứa evidence excerpts (dev 15 excerpt/581 ký tự, test 5 excerpt/181 ký tự). Cũng đang track `data/example_questions.json` (một evidence field ngắn, nguồn gốc cần rà soát), `report/individual/context_engineering_dev_audit.json` (16 excerpt không rỗng/461 ký tự) và `report/individual/ingestion_v2_review.md` (15 ví dụ trước/sau gắn với PDF/trang). Cần xác nhận các artifact cụ thể này thuộc phạm vi cho phép trước khi public tiếp tục. Không kết luận repo an toàn public; `.gitignore` không gỡ file khỏi history.
- `report/individual/agent_final_evaluation_test.md` chứa audit theo trang PDF; automated overlap scan có một candidate khớp chuỗi ngắn với chunk nguồn, cần rà soát thủ công. Các report khác không có match chính xác từ 20 ký tự trở lên trong kiểm tra hiện tại; đây không thay thế xác nhận phạm vi quyền.
- Không đưa raw `traces.json`, `audit_manual.json` đầy đủ, contexts, API responses hoặc PDFs lên GitHub nếu chưa có quyền; traces giữ nguyên ở local ignored directory.
- `artifacts/final_evaluation_public.json`, `artifacts/final_test_manifest_public.json` và `artifacts/final_test_trace_sanitized.json` không chứa PDF excerpt/raw context/API key theo kiểm tra hiện tại. Trace sanitized giữ 7 case, 21 hit, chunk IDs, rank/score, source/page, metadata có cấu trúc, tool event, citation checks, latency, token và chi phí; query, answer, chunk text, context, evidence note, free-text tool args và `quality_reasons` đã bỏ. Có thể nộp các artifact này cho giảng viên theo phạm vi đã xác nhận; việc public GitHub vẫn phụ thuộc quyền đối với các file nguồn khác.
- Nếu quyền không cho phép redistribution, giữ repo/private artifact store hoặc tạo một bản nộp sạch lịch sử Git đã loại benchmark/excerpts và cung cấp quy trình nhận dữ liệu được cấp quyền. Chỉ thêm `.gitignore` không loại file đã track hoặc xóa nội dung khỏi Git history.

## Allowlist đề xuất cho GitHub sau khi duyệt

### Có thể đưa lên sau khi duyệt nội dung

- `README.md`, `GUIDE.md`, `BENCHMARK.md`, `RUBRIC.md`, `RULES.md`, `SUBMISSION.md`, `SUBMISSION_CHECKLIST.md`.
- `starter/*.py` cần cho ingestion/retrieval/agent/evaluation và `tests/*.py`.
- `starter/requirements-*.txt`, `.env.example`, `.gitignore`.
- `report/individual/2A202603812_NguyenDucNhat.md`, `report/individual/agent_final_evaluation_test.md`, các báo cáo tổng hợp dev sau khi kiểm tra không chứa nội dung nguồn vượt quyền.
- `artifacts/README.md`, `artifacts/final_evaluation_public.json`, `artifacts/final_test_manifest_public.json`.
- `artifacts/final_test_trace_sanitized.json` (trace tổng hợp đã khử source text; không phải raw trace).

### Chỉ đưa lên khi có quyền/phê duyệt rõ

- `data/benchmark_v2_dev.json`, `data/benchmark_v2_test.json` (chứa evidence excerpts) và manifest đi cùng.
- `report/individual/ingestion_v2_review.md`, `context_engineering_dev_audit.json`, các report/audit chứa excerpt.
- `starter/data/` chunks/index metadata; không force-add mặc định.
- `starter/results/` full traces, contexts, outputs, source text và account usage metadata; không force-add mặc định.
- `data/discrete_math/raw/` PDF sources: hiện không track, tiếp tục loại khỏi Git.

## Lệnh kiểm tra trước khi nộp

Từ repo root, sau khi dữ liệu local đã sẵn sàng:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q starter tests
git diff --check
git status --short
```

Lượt kiểm tra hiện tại: **54 tests passed, 1 live PostgreSQL test skipped** do opt-in. Không chạy benchmark test hoặc gọi API trong lượt chuẩn bị cuối. Không dùng `git add -f` cho các thư mục bị ignore; không commit/push trước khi người dùng duyệt artifacts và quyết định quyền phân phối.

