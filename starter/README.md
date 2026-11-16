# Starter và lệnh chạy Lab 07

Tài liệu này hướng dẫn chạy phần ingestion, retrieval, context và agent theo trạng thái hiện tại. Đọc [README gốc](../README.md), [GUIDE](../GUIDE.md), [BENCHMARK](../BENCHMARK.md), [RUBRIC](../RUBRIC.md), [RULES](../RULES.md) và [checklist nộp](../SUBMISSION_CHECKLIST.md) trước khi chia sẻ repository.

## 1. Môi trường

- Python 3.12 cho ingestion V2 và tests hiện tại.
- Dense/Hybrid và indexing cần môi trường Python của Lab 06 có `sentence-transformers`, `psycopg`/pgvector và kết nối PostgreSQL 16.
- Agent gọi OpenRouter qua thư viện chuẩn `urllib`; không cần SDK riêng.
- Các PDF nguồn, chunks đã sinh, database và traces có nội dung nguồn là tài nguyên local. Không tải lên Git nếu chưa xác minh quyền phân phối.

Tạo môi trường Lab 07 và cài parser:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r starter\requirements-ingestion-v2.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Đặt API key/config trong `.env` ở repo root; không commit file này. Biến cần có cho API run:

```dotenv
OPENROUTER_API_KEY=...
LAB07_LLM_MODEL=z-ai/glm-5.3-flash:floor
LAB07_LLM_BASE_URL=https://openrouter.ai/api/v1
LAB07_INPUT_USD_PER_1M=0.042
LAB07_OUTPUT_USD_PER_1M=0.184
LAB07_EXTERNAL_CORPUS_OK=1
```

Chỉ bật `LAB07_EXTERNAL_CORPUS_OK=1` sau khi có xác nhận quyền gửi nội dung tài liệu tới API ngoài. Theo xác nhận của người nộp, giáo viên cho phép sử dụng tài liệu cho Lab 07/nộp cho giảng viên; đây là phạm vi sử dụng học thuật, không phải quyền công khai toàn bộ PDF hoặc chunks. Việc gửi context trong run đã hoàn thành dựa trên xác nhận riêng của người dùng. Repo hiện public và có một số evidence excerpts đã track; cần xác nhận riêng phạm vi public của các excerpt đó.

## 2. Ingestion và indexing

Raw PDFs phải được cấp local theo danh sách nguồn. Ingestion V1 chỉ chuẩn bị chunk JSON; ingestion V2 đọc V1 + PDF và tạo file riêng, không embedding:

```powershell
.\.venv\Scripts\python.exe starter\index_discrete_math.py --prepare-only
.\.venv\Scripts\python.exe starter\improve_discrete_math.py
```

V1/V2 local JSON nằm dưới `starter/data/` và bị ignore. V2 hiện có 332 chunks, giữ `id`, `source_id`, `source`, `page` và metadata `subject`, `chapter`, `content_type`, `extraction_quality`. Nội dung có nguy cơ mất cấu trúc toán/hình được đánh dấu `needs_review`; không tái tạo nội dung từ hình.

Index V2 dùng Python environment của Lab 06 và `.env`/PostgreSQL của Lab 06:

```powershell
$Day6Python = "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe"
& $Day6Python starter\index_discrete_math_v2.py
```

Indexing ghi strategy riêng `D07_discrete_math_v2` bằng MiniLM đa ngôn ngữ 384 chiều. Chỉ chạy nếu cần tạo lại database; trạng thái nộp hiện tại đã có 332 vectors V2 và không cần re-embed. Index V2 không ghi đè A_fixed hoặc B_paragraph. Xem [ingestion audit](../report/individual/ingestion_v2_review.md) và [index smoke report](../report/individual/v2_index_smoke.md).

## 3. Retrieval và benchmark

`retrieval_v2.py` triển khai:

1. Dense pgvector, cosine similarity.
2. TF-IDF lexical trên cùng 332 chunks.
3. Hybrid RRF, hợp nhất candidate Dense + TF-IDF.

Các lệnh trực tiếp dưới đây dùng live suite, xác minh index PostgreSQL hiện có và chỉ truy vấn (không ghi DB):

```powershell
$Day6Python = "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe"
& $Day6Python starter\retrieval_v2.py --strategy dense --query "Định nghĩa cây khung nhỏ nhất là gì?"
& $Day6Python starter\retrieval_v2.py --strategy tfidf --query "Định nghĩa cây khung nhỏ nhất là gì?"
& $Day6Python starter\retrieval_v2.py --strategy hybrid_rrf --query "Định nghĩa cây khung nhỏ nhất là gì?"
```

So sánh Dense/TF-IDF/Hybrid trên dev tạo run mới và đọc PostgreSQL/model đã index; không re-embedding:

```powershell
& $Day6Python starter\evaluate_retrieval_v2.py
```

A2 R1 (query expansion) và R2 (candidate expansion + RRF) là phép đo offline trên V2, đọc trace R0 đã khóa, không gọi API/DB:

```powershell
.\.venv\Scripts\python.exe starter\retrieval_a2.py
```

Benchmark dev/test được khóa bằng [manifest](../data/benchmark_v2_manifest.json). Dev retrieval và A2 không dùng gold trong query/filter. Không chạy benchmark test bằng retrieval tuning scripts.

## 4. Context Engineering

`context_engineering_v2.py` dùng Top-3 TF-IDF đã lưu để so sánh C0/C1 dev; không chạy retrieval/API/DB. C0 giữ thứ hạng gốc và pack chunk đầy đủ trong 800 ký tự. C1 chọn tập con evidence-aware từ cùng Top-3, không dùng gold.

```powershell
.\.venv\Scripts\python.exe starter\context_engineering_v2.py
```

Metrics và audit nằm local ở `starter/results/`; đọc [báo cáo context](../report/individual/context_engineering_dev.md). Token MiniLM trong báo cáo context là proxy, không phải token LLM.

## 5. Agent A1 và evaluation

Agent A1 dùng OpenRouter Chat Completions function calling. Model quyết định gọi `search_discrete_math`; tool gọi TF-IDF Top-3 R0 rồi đóng context C0 800 ký tự. Mọi câu claim cần citation inline; citation được kiểm tra theo chunk/source/page trong context. Khi JSON/citation lỗi có tối đa một repair với cùng context. Validator cấu trúc không thay thế audit semantic.

Chạy A1 trên 17 câu dev tạo run mới; chỉ chạy khi có quyền, budget và cần một đánh giá mới:

```powershell
$Day6Python = "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe"
& $Day6Python starter\run_agent_a1_dev.py --max-api-calls 51 --max-total-tokens 30000 --max-cost-usd 0.10 --max-completion-tokens 300
```

Final Evaluation test đã chạy đúng một lần, đủ 7 câu. **Không chạy lại** lệnh dưới đây; chỉ giữ làm command provenance:

```powershell
.\.venv\Scripts\python.exe starter\run_agent_a1_test.py --max-api-calls 21 --max-total-tokens 20000 --max-cost-usd 0.10
```

Kết quả chính thức và failure audit: [final evaluation](../report/individual/agent_final_evaluation_test.md). Gói số liệu đã loại bỏ context/text nguồn: [artifacts summary](../artifacts/final_evaluation_public.json). Chạy lại test sẽ tạo lần đánh giá test thứ hai và không còn độc lập.

## 6. Tests và nguyên tắc nộp

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q starter tests
git diff --check
```

Test suite có một integration test pgvector chỉ chạy khi bật `RUN_LIVE_V2_TESTS=1`; không bật biến này trong unit-test pass thường.

`.gitignore` loại `.env`, `data/discrete_math/raw/`, `starter/data/` và `starter/results/`. Không force-add PDF, chunks V2, raw traces hoặc context. Benchmark JSON hiện đang được track và chứa evidence excerpts. Quyền sử dụng cho bài học/nộp giảng viên đã được người nộp xác nhận; việc public các excerpt và toàn bộ tài liệu chưa được xác nhận riêng. Xem [checklist nộp](../SUBMISSION_CHECKLIST.md) để biết allowlist và giới hạn quyền.
