# Starter Day 7

| File | Công dụng |
|---|---|
| `agentic.py` | Khung agent ví dụ với số lượt search, top-k và context budget có thể cấu hình |
| `baseline.py` | TF-IDF lexical baseline, chạy offline |
| `convert_day6.py` | Chuyển một số trường JSON từ Day 6 |
| `agent_metrics.py` | Tổng hợp nhãn đánh giá do bạn tự chấm |

Starter **chưa phải solution hoàn chỉnh**. Bạn phải nối model và vector store thật, triển khai ít nhất 3 phương pháp retrieval do bạn chọn, gồm dense trên vector store Day 6. Mock chỉ dùng để test code.

## 1. Kết nối agent

Trong `agentic.py`, hiện thực:

- `Controller.decide`: gọi model thật và trả `{action: "search", query: "..."}` hoặc `{action: "answer", answer: "... [chunk-id]", citations: ["chunk-id"]}`.
- `Retriever.search`: tạo query embedding tương thích Day 6, truy vấn vector store thật và trả chunk theo [định dạng dữ liệu](../data/README.md).

Tự viết chương trình nối hai phần với `run_agent`, hoặc thay thế bằng kiến trúc nhiều tool. Tham số `max_searches`, `top_k` và `budget` chỉ là mặc định của ví dụ, không phải giới hạn của đề. Xem `tests/test_agentic.py` để hiểu cách gọi; kết nối trong test là mock. Khung code kiểm tra citation ID có trong context, nhưng bạn phải tự đọc xem nguồn có hỗ trợ câu trả lời. Báo lỗi kết nối, không thay bằng kết quả giả.

## 2. Chạy TF-IDF baseline

Chạy từ thư mục gốc với Python 3.11 trở lên:

```bash
python3 -m unittest discover -s tests -v
python3 starter/baseline.py --chunks data/example_chunks.json --questions data/example_questions.json --split dev --output starter/results/example-dev
```

Kết quả có `summary.json` và `traces.json`. Dữ liệu mẫu chỉ có một câu, không đủ để nộp bài. TF-IDF là lexical retrieval, không dùng filter và không thay dense retrieval.

## 3. Dùng dữ liệu Day 6

Xuất chunk và câu hỏi thành hai JSON array. Starter Day 6 không quy định tên bảng hay cách xuất; bạn cần tự thực hiện. Nếu chunk có `chunk_id`, `document_id`, `source`, `page`, `text`, `metadata` và câu hỏi có `gold_source_id`, `gold_page`, `evidence_quote`, chạy:

```bash
python3 starter/convert_day6.py --chunks <day6_chunks.json> --questions <day6_questions.json> --output starter/data/converted
python3 starter/baseline.py --chunks starter/data/converted/chunks.json --questions starter/data/converted/questions.json --split dev --output starter/results/dev-tfidf
```

Thay phần trong `< >` bằng đường dẫn thật. Script chỉ đổi tên trường, không tự truy cập database hay đoán evidence. Nếu cấu trúc khác, tự viết adapter. Đối chiếu lại nguồn, trang và evidence.

`--split dev` chỉ chấm dev. Sau khi chốt cấu hình, dùng `--split test` và chọn thư mục kết quả khác. Nếu test Day 6 từng dùng để chỉnh hệ thống, tạo test mới theo [GUIDE.md](../GUIDE.md). Baseline mẫu dùng evidence nằm trong một chunk và context từ top-3; cần mở rộng hoặc tự đánh giá nếu dùng multi-hop, context từ nhiều lượt hay schema khác. Khớp nguyên văn bằng code không thay thế đánh giá thủ công.

### Index PDF Toán rời rạc vào pgvector Day 6

Repo này có adapter để dùng lại **đúng model 384 chiều và PostgreSQL/pgvector Day 6**. Chín PDF mới được chunk lại theo paragraph (tối đa 500 ký tự, không nối qua trang), xuất thành `starter/data/indexed/discrete_math/chunks.json` với schema:

```json
{"id":"chuong-1-co-so-logic:p1:c1","text":"…","source_id":"chuong-1-co-so-logic","source":"data/discrete_math/raw/Chuong 1. Co so logic.pdf","page":1,"metadata":{"file_name":"Chuong 1. Co so logic.pdf","chapter":1}}
```

`chunks.json` không chứa vector số; vector mới được embed bằng model Day 6 và lưu trong cùng bảng PostgreSQL dưới strategy `D07_discrete_math`. Các vector A/B của Day 6 không bị thay thế. Không thể gán vector cũ của Giải tích vào chunk Toán rời rạc vì đó là văn bản khác; cách tái sử dụng đúng là dùng cùng model, chiều vector và vector store, rồi embed nội dung mới.

Từ thư mục gốc repo Day 7, PowerShell:

```powershell
# Cài parser VNI vào đúng môi trường Python đang chạy pipeline (Day 6).
& "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe" -m pip install -r starter\requirements-indexing.txt

# Chỉ trích xuất/chunk và ghi JSON để duyệt; chưa embed/ghi database.
& "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe" starter\index_discrete_math.py --prepare-only

# Sau khi duyệt chunks.json, embed bằng model Day 6 và upsert strategy riêng.
& "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe" starter\index_discrete_math.py
```

Có thể truyền `--day6-root <đường-dẫn>` nếu repo Day 6 không nằm cạnh Lab 07. Chạy lệnh thứ hai nhiều lần sẽ cập nhật index cùng strategy theo ID ổn định. File `index_info.json` ghi model, chiều, số trang/chunk và thời gian embedding. Input PDF và output local vẫn bị Git bỏ qua cho tới khi quyền chia sẻ được xác minh.

### Audit ingestion v2 cho Cấu trúc rời rạc

Từ thư mục gốc Lab 07, chạy pipeline v2 bằng Python 3.12 của Lab 07:

```powershell
& .\.venv\Scripts\python.exe -m pip install -r starter\requirements-ingestion-v2.txt
& .\.venv\Scripts\python.exe starter\improve_discrete_math.py
```

Script **chỉ đọc** `chunks.json` v1 và 9 PDF nguồn. Nó tạo `starter/data/indexed/discrete_math/chunks_v2.json` cùng [báo cáo đối chiếu 15 ví dụ](../report/individual/ingestion_v2_review.md). File v1 được kiểm tra SHA-256 trước/sau và không bị ghi đè. Metadata v2 gồm `subject`, `chapter`, `content_type`, `extraction_quality`, lý do cần review và ID chunk v1 cùng trang. Bảng chân trị chỉ được chuyển sang Markdown khi hàng/cột kiểm tra được; công thức, ma trận và hình không khôi phục chắc chắn được đánh dấu `needs_review`. Lệnh tạo V2 này không embedding, ghi database hoặc chạy benchmark. Lệnh index v1 ở mục trên không thuộc bước V2.

### Index V2 thử nghiệm

Sau khi duyệt V2, chạy từ thư mục gốc Lab 07 bằng Python của Day06 đã cài `starter/requirements-indexing.txt` và có PostgreSQL/pgvector đang hoạt động:

```powershell
& "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe" -B starter\index_discrete_math_v2.py
```

Script xác nhận SHA-256 của V1/V2 đã duyệt, 332 ID và citation, rồi embed bằng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 chiều) vào strategy riêng `D07_discrete_math_v2`. Mục tiêu chunk là 500 ký tự; 22 chunk vượt mục tiêu để giữ cấu trúc khi có thể, giới hạn cứng 620. Metadata của payload/DB ghi `chunk_target_chars`, `chunk_hard_limit_chars`, `semantic_over_target` và `semantic_unit_split`; 2 trong 22 chunk là phần của đơn vị dài hơn và được đánh dấu đã tách. `chunks.json` và `chunks_v2.json` không bị sửa. Nếu strategy V2 đã chứa đúng các hàng này, script kiểm tra và bỏ qua embedding; dữ liệu khác sẽ báo lỗi thay vì ghi đè.

Kiểm tra [báo cáo index và smoke retrieval](../report/individual/v2_index_smoke.md). Các file local `chunks_v2_index_ready.json`, `index_info_v2.json`, `smoke_traces_v2.json` nằm trong `starter/data/indexed/discrete_math/` và bị Git bỏ qua. Smoke retrieval dùng pgvector thật với filter SQL; chưa chấm benchmark test hay đánh giá grounding. Chunk `needs_review` cần đối chiếu PDF trước khi dùng làm evidence cho câu trả lời.

### Ba phương pháp retrieval trên V2 và benchmark dev

`retrieval_v2.py` đọc bản V2 đã duyệt và đối chiếu toàn bộ 332 hàng với PostgreSQL, sau đó cung cấp Dense pgvector, TF-IDF trên cùng 332 text và Hybrid RRF. Mỗi hit có `chunk_id`, `id`, `text`, `score`, `rank`, `source_id`, `source`, `page`, `metadata`; `needs_review` được giữ. Filter `document_id`, `source`, `page` dùng cột SQL ở Dense; các khóa metadata dùng JSONB containment. TF-IDF áp dụng cùng filter trên dữ liệu local. RRF mặc định lấy 20 ứng viên mỗi nhánh và dùng `1/(60 + rank)`.

Từ thư mục gốc Lab 07, dùng Python Day06 đang có model và database:

```powershell
& "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe" -B starter\retrieval_v2.py --strategy dense --query "Định nghĩa cây khung nhỏ nhất là gì?"
& "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe" -B starter\retrieval_v2.py --strategy tfidf --query "Định nghĩa cây khung nhỏ nhất là gì?"
& "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe" -B starter\retrieval_v2.py --strategy hybrid_rrf --query "Định nghĩa cây khung nhỏ nhất là gì?" --filters '{\"chapter\":6}'
```

Benchmark được tách thành [17 câu dev](../data/benchmark_v2_dev.json) và [7 câu test](../data/benchmark_v2_test.json); hash và số câu nằm trong [manifest](../data/benchmark_v2_manifest.json). Lệnh dưới đây **chỉ đọc dev** và lưu mỗi run vào thư mục mới với `metrics.json`, `traces.json`, `run_manifest.json`. Traces gồm Top-3 đầy đủ text/metadata, context và latency từng truy vấn. Không dùng gold làm query/filter; không embed lại corpus hay ghi DB.

```powershell
& "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe" -B starter\evaluate_retrieval_v2.py
$env:RUN_LIVE_V2_TESTS = "1"
& "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe" -B -m unittest discover -s tests -p test_retrieval_v2.py -v
Remove-Item Env:RUN_LIVE_V2_TESTS
```

Xem [báo cáo so sánh dev](../report/individual/retrieval_v2_dev_comparison.md). Script không có lựa chọn chạy test benchmark; sau khi chốt cấu hình và tiêu chí đánh giá, test cần được thực hiện trong một bước riêng có trace và báo cáo độc lập. Các file trong `starter/results/` bị Git bỏ qua; kiểm tra quyền trích đoạn tài liệu trước khi chia sẻ.

### Context Engineering trên dev

Script `context_engineering_v2.py` đọc **Top-3 TF-IDF đã lưu** trong run dev `dev-20261116T043019037173Z`, xác minh SHA-256 của trace, corpus và benchmark, rồi tạo run context mới. C0 giữ thứ hạng gốc và pack greedy; C1 chọn tập con các chunk nguyên vẹn theo rank, loại nội dung, cờ trích xuất và loại câu hỏi. Hai cấu hình dùng cùng ngân sách 800 ký tự, kể cả citation; hàm pack không nhận gold. Mỗi header context có `chunk_id`, `source`, `page`, `extraction_quality`. Số token được đo bằng tokenizer MiniLM như số tham khảo, chưa phải token của LLM Agent.

```powershell
& "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe" -B starter\context_engineering_v2.py
& .\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_context_engineering_v2.py -v
```

Run context đã audit là `starter/results/discrete_math_v2/context-dev-20261116T044835296260Z/`. [Audit thủ công 34 context](../report/individual/context_engineering_dev_audit.json) được kiểm tra bằng lệnh dưới đây; script chỉ tạo `metrics_reviewed.json` khi chưa có hoặc xác nhận file hiện có giống hệt:

```powershell
& .\.venv\Scripts\python.exe -B starter\summarize_context_review_v2.py
```

Xem [báo cáo context dev](../report/individual/context_engineering_dev.md). Các run mới phải có audit riêng và không thay file đã chấm. Không chạy test benchmark hoặc ghi database.

## 4. Tổng hợp đánh giá agent

### Agent V2 thực tế (dev-only)

`agent_v2.py` dùng Chat Completions tool calling: model quyết định gọi `search_discrete_math`, tool chạy đúng `V2RetrievalSuite.tfidf(question, top_k=3)` trên 332 chunk và `pack_c0(..., 800)`. Query của tool luôn là câu hỏi gốc để giữ cấu hình thí nghiệm. Lần gọi thứ hai chỉ nhận context đã chọn; câu trả lời phải là JSON với citation `{chunk_id, source, page}` khớp context. Bộ kiểm tra tự động xác nhận cấu trúc, không xác nhận semantic grounding. Trả lời thiếu hoặc sai citation bị chuyển thành abstention. Các chunk `needs_review` được giữ cờ và lý do trong trace; prompt cấm đoán hình/bảng/công thức thiếu. Đây là **tool calling thực tế**, có thể quan sát model không gọi tool; nó không phải pipeline RAG cố định.

Chuẩn bị biến môi trường theo `.env.example` ở root. `LAB07_EXTERNAL_CORPUS_OK=1` chỉ sau khi bạn xác minh quyền gửi đoạn tài liệu đến API ngoài. Điền `LAB07_INPUT_USD_PER_1M` và `LAB07_OUTPUT_USD_PER_1M` theo giá đúng của model đã chọn. Không tải `.env` vào Git. Ví dụ PowerShell sau khi đã nạp biến môi trường:

```powershell
& "..\..\lab06\K5--Day06-NguyenDucNhat-2A202603812-DataIngestionEngineering\starter\.venv\Scripts\python.exe" -B starter\run_agent_v2_dev.py --max-api-calls 34 --max-total-tokens 30000 --max-cost-usd 1 --max-completion-tokens 300
```

Runner chỉ đọc `data/benchmark_v2_dev.json`; không đọc test, không kết nối DB, không embedding. Mỗi lần chạy tạo run mới trong `starter/results/discrete_math_v2/agent-dev-*`; trace được lưu sau từng câu để giữ kết quả nếu gặp lỗi API. Giới hạn token và chi phí được kiểm tra sau từng câu theo usage thực tế; chúng **không phải hard cap của nhà cung cấp** vì prompt token của một lời gọi chưa biết trước. Đặt thêm project spending limit tại nhà cung cấp. `metrics_auto.json` ghi usage, latency, số lần gọi tool, abstention và tính hợp lệ cấu trúc citation. Dùng `reviews_template.json` để chấm thủ công grounded answer, support của từng citation và abstention; sau đó chạy `agent_metrics.py --split dev` với file review đã hoàn thành. Không chấm grounded answer từ Context Evidence Rate.

Sau khi chạy agent thật và tự chấm, chuẩn bị ba JSON array:

- `cases.json`: mỗi câu có `id`, `split`, `answerable` (`true` nếu có đủ evidence).
- `traces.json`: mỗi kết quả có `query_id`, `status` (`answered`, `abstain`, `error`), `events`, `citations`. Thêm `query_id` vào kết quả `run_agent`; lỗi kết nối ghi riêng với `status: "error"`. Script đếm tool use qua event `search`: nếu dùng nhiều tool, chuẩn hóa mỗi lượt retrieval về event này và ghi tên tool trong trường khác, hoặc tự viết metric tương đương.
- `reviews.json`: mỗi nhãn có `query_id`, `citation_support` là danh sách đúng/sai ứng với từng citation. Câu có đáp án cần `answer_grade` 0–2 theo [BENCHMARK.md](../BENCHMARK.md); nếu bị từ chối, chấm 0. Câu thiếu evidence cần `abstention_correct` (`true`/`false`) do người chấm xác nhận. Lần chạy lỗi không cần nhãn.

```bash
python3 starter/agent_metrics.py --cases <cases.json> --traces <traces.json> --reviews <reviews.json> --split test --output starter/results/agent-test/summary.json
```

Thay đường dẫn trong `< >`. Script tổng hợp nhãn bạn đã chấm, không tự đánh giá nội dung. Mẫu số bằng 0 nghĩa là không áp dụng. Lỗi kết nối được báo riêng, không tính vào chất lượng; giữ trace và nhãn để đối chiếu.

## Lưu ý

TF-IDF dùng cách tách từ đơn giản. `baseline.py` dùng mặc định context budget 800 ký tự, gồm cả nguồn; chunk không vừa bị bỏ. Bạn có thể chọn cách khác. File kết quả cùng tên sẽ bị ghi đè. `starter/data/` và `starter/results/` không được Git theo dõi mặc định; nếu được phép chia sẻ, dùng `git add -f <đường-dẫn>`, hoặc ghi cách tái tạo. Không nộp dữ liệu mật và secret.

Khung agent ưu tiên giữ chunk từ lần search trước. Khi chunk đầu chiếm gần hết budget, lần search sau có thể không thêm được evidence; hãy kiểm tra trace và thử cách chọn context phù hợp trên dev. Citation ID hợp lệ hoặc verifier trả “đúng” không đảm bảo câu trả lời được hỗ trợ; cần chấm thủ công.
