# Checklist chuẩn bị nộp Lab 07

Trạng thái theo artifacts hiện có; chưa commit hoặc push.

## Đối chiếu yêu cầu/rubric

| Yêu cầu | Trạng thái | Bằng chứng / việc còn lại |
|---|---|---|
| Dữ liệu Day 6, embedding, vector store | Đạt | V2 332 chunks, MiniLM multilingual 384 chiều, PostgreSQL 16 + pgvector, strategy riêng; A/B Lab 06 giữ nguyên. Xem `report/individual/v2_index_smoke.md`. |
| Dataset và benchmark | Đạt có điều kiện | Dev 17 (15+2), test 7 (5+2), manifest/hash có sẵn; test đã chạy một lần. Git đang track ba benchmark JSON có evidence excerpts; phải xác minh quyền phân phối trước khi public. |
| Bao phủ nguồn | Thiếu | Thư mục có 9 PDF/389 trang, trong khi kiểm kê kỳ vọng 10 files. Bản PPT/PPTX Chương 3 chưa có để đối chiếu PDF/PPT trùng. |
| Ba phương pháp retrieval, gồm Dense | Đạt | Dense pgvector, TF-IDF, Hybrid RRF dùng cùng V2; có rank/score/source/page/filter và lỗi trong báo cáo dev. |
| Agent thật, tool traces và context | Đạt | A1 dùng OpenRouter tool calling thật, R0 TF-IDF Top-3, C0 800 ký tự, citation check và tối đa một repair. |
| Evaluation | Đạt | Retrieval/context và A1 được đánh giá dev; final Agent test 7 câu có metrics tự động, audit thủ công, hashes và traces local. Test được chạy đúng một lần. |
| Thử nghiệm cải thiện và phân tích lỗi | Đạt | C0/C1; A0→A1; A2 R0/R1/R2; phân tích lỗi d01, d03, d14, t02, t04. R1/R2 không được mô tả là cải thiện khi metric không tăng. |
| Grounding/citation/abstention | Đạt | Citation structure được phân biệt với support semantic; t02/t04 là false refusals sau repair; t06/t07 abstain đúng. |
| Tái lập và báo cáo | Đạt có điều kiện | README, code, tests, report cá nhân, sanitized metrics và public manifest có. Raw run manifests/traces dưới `starter/results/` bị ignore; chỉ đưa lên nơi được phép. |
| Thử thách nâng cao 100 trang | Chưa thực hiện | Không tuyên bố bonus 15 điểm. |
| Nguồn và quyền phân phối | **Chặn public release** | Quyền phân phối PDF/trích đoạn vẫn cần xác minh; không tuyên bố đã có license. Xem phần Git/data bên dưới. |

## Báo cáo cá nhân và thông tin sinh viên

 `STUDENT.md` đã được tạo với MSSV `2A202603812` và tên `NguyenDucNhat` theo đúng repository name/Git remote đã xác minh; không tự suy đoán dấu tiếng Việt hay thông tin cá nhân khác. Báo cáo đã lưu tại `report/individual/2A202603812_NguyenDucNhat.md`. `report/individual/MSSV_HoTen.md` vẫn là mẫu gốc.

## Git, dữ liệu và bí mật

- `.env` và `.env.*` được ignore; chỉ `.env.example` được track, không chứa giá trị key.
- Raw PDFs không được Git track; `data/discrete_math/raw/` bị ignore.
- V1/V2 JSON và run outputs trong `starter/data/`, `starter/results/` bị ignore.
- Detailed A1 audit JSON và d04 API smoke report được ignore rõ ràng vì có thể chứa source-derived content; dùng báo cáo/sanitized artifacts thay thế khi public.
- Git hiện **đang track** `data/benchmark_v2_dev.json`, `data/benchmark_v2_test.json`, `data/benchmark_v2_manifest.json`. Hai benchmark có câu hỏi/đáp án/evidence excerpt từ tài liệu; một số report/audit ingestion/context cũng có trích đoạn source. Không push public trước khi xác minh quyền.
- Không đưa raw `traces.json`, `audit_manual.json` đầy đủ, contexts, API responses hoặc PDFs lên GitHub nếu chưa có quyền; traces giữ nguyên ở local ignored directory.
- `artifacts/final_evaluation_public.json` và `artifacts/final_test_manifest_public.json` là gói đề xuất đưa lên Git: chỉ aggregate metrics, run ID, hash, case labels, cấu hình và chi phí; không có query, answer, PDF excerpt, raw context hay secret. Vẫn cần kiểm tra chính sách lớp/đơn vị trước khi phát hành.
- Nếu quyền không cho phép redistribution, giữ repo/private artifact store hoặc tạo một bản nộp sạch lịch sử Git đã loại benchmark/excerpts và cung cấp quy trình nhận dữ liệu được cấp quyền. Chỉ thêm `.gitignore` không loại file đã track hoặc xóa nội dung khỏi Git history.

## Allowlist đề xuất cho GitHub sau khi duyệt

### Có thể đưa lên sau khi duyệt nội dung

- `README.md`, `GUIDE.md`, `BENCHMARK.md`, `RUBRIC.md`, `RULES.md`, `SUBMISSION.md`, `SUBMISSION_CHECKLIST.md`.
- `starter/*.py` cần cho ingestion/retrieval/agent/evaluation và `tests/*.py`.
- `starter/requirements-*.txt`, `.env.example`, `.gitignore`.
- `report/individual/2A202603812_NguyenDucNhat.md`, `report/individual/agent_final_evaluation_test.md`, các báo cáo tổng hợp dev sau khi kiểm tra không chứa nội dung nguồn vượt quyền.
- `artifacts/README.md`, `artifacts/final_evaluation_public.json`, `artifacts/final_test_manifest_public.json`.

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

Lượt kiểm tra hiện tại: **54 tests passed, 1 live PostgreSQL test skipped** do opt-in. Không chạy lại benchmark test. Không dùng `git add -f` cho các thư mục bị ignore; không commit/push trước khi người dùng duyệt artifacts và quyết định quyền phân phối.

