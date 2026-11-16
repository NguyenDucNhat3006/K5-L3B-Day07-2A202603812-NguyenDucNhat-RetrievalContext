# Kiểm tra index corpus Cấu trúc rời rạc V2

V2 được dùng làm corpus thử nghiệm theo quyết định của người dùng. Báo cáo này chỉ ghi indexing và smoke retrieval, không ghi điểm benchmark.

## Nguồn và chính sách chunk

- V1: `7561e3a39e06b919b5872e2e3f9083c6ef2d67c739c5329464d6d7090aba515d`; V2 đã duyệt: `979a0baaf2f34735592bde1aeaf2bdb29b5a8f336f3f0bcb3fee699056f57990` (SHA-256). Hai JSON nguồn được giữ nguyên byte.
- V2 có **332** chunk; **22** chunk dài hơn 500 ký tự, dài nhất 614. Giới hạn mục tiêu là 500, giới hạn cứng là 620; mọi chunk đều trong giới hạn cứng.
- **20** chunk >500 giữ trọn đơn vị semantic; **2** chunk >500 là phần của đơn vị dài hơn, có cờ `long_semantic_unit_split`. Không diễn giải hai chunk này là đơn vị nguyên vẹn.
- Metadata của payload/DB có `chunk_target_chars`, `chunk_hard_limit_chars`, `semantic_over_target`, `semantic_unit_split`, `approved_v2_sha256`. Text, ID, source_id, source và page trùng V2 đã duyệt.
- `needs_review`: **256/332** chunk; các cờ phản ánh rủi ro thiếu evidence và có thể chồng lấp.

| Nhóm cần kiểm tra | Số chunk | Tất cả có needs_review? |
|---|---:|---|
| Bảng | 86 | có |
| Ma trận | 13 | có |
| Hình/đồ thị | 33 | có |
| Công thức/font | 200 | có |

Bảng chân trị có cấu trúc được giữ từ PDF khi trích xuất đáng tin cậy; bảng lệch cột, ma trận và hình chưa đọc đủ vẫn cần đối chiếu trang nguồn. Không bổ sung dữ liệu suy đoán từ hình.

### 22 chunk vượt mục tiêu 500 ký tự

| ID | Ký tự | Chính sách | extraction_quality |
|---|---:|---|---|
| `bai-tap-chuong-5:p1:c1:v2` | 579 | giữ đơn vị semantic | needs_review |
| `bai-tap-chuong-5:p2:c1:v2` | 578 | giữ đơn vị semantic | needs_review |
| `bai-tap-chuong-5:p4:c1:v2` | 614 | giữ đơn vị semantic | needs_review |
| `bai-tap-chuong-5:p6:c1:v2` | 612 | giữ đơn vị semantic | needs_review |
| `bai-tap-chuong-6:p1:c1:v2` | 595 | giữ đơn vị semantic | needs_review |
| `bai-tap-chuong-6:p1:c2:v2` | 535 | giữ đơn vị semantic | needs_review |
| `bai-tap-chuong-6:p2:c1:v2` | 594 | giữ đơn vị semantic | needs_review |
| `chuong-2-phep-dem:p14:c1:v2` | 608 | giữ đơn vị semantic | needs_review |
| `chuong-3-quan-he:p6:c1:v2` | 545 | giữ đơn vị semantic | needs_review |
| `chuong-3-quan-he:p19:c1:v2` | 542 | giữ đơn vị semantic | needs_review |
| `chuong-3-quan-he:p21:c1:v2` | 501 | giữ đơn vị semantic | ok |
| `chuong-3-quan-he:p41:c1:v2` | 593 | giữ đơn vị semantic | needs_review |
| `chuong-4-dai-so-boole:p9:c1:v2` | 563 | đã tách từ đơn vị dài | needs_review |
| `chuong-4-dai-so-boole:p28:c1:v2` | 610 | đã tách từ đơn vị dài | needs_review |
| `chuong-4-dai-so-boole:p49:c1:v2` | 538 | giữ đơn vị semantic | ok |
| `chuong-4-dai-so-boole:p52:c1:v2` | 501 | giữ đơn vị semantic | needs_review |
| `chuong-4-dai-so-boole:p53:c1:v2` | 593 | giữ đơn vị semantic | needs_review |
| `chuong-4-dai-so-boole:p57:c1:v2` | 530 | giữ đơn vị semantic | needs_review |
| `chuong-5-do-thi-phan-2:p4:c1:v2` | 603 | giữ đơn vị semantic | ok |
| `chuong-5-do-thi-phan-2:p9:c1:v2` | 501 | giữ đơn vị semantic | needs_review |
| `chuong-5-do-thi-phan-2:p25:c1:v2` | 507 | giữ đơn vị semantic | needs_review |
| `chuong-6-cay:p38:c1:v2` | 565 | giữ đơn vị semantic | ok |

## PostgreSQL + pgvector

- Strategy riêng: `D07_discrete_math_v2`. Model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; chiều vector: **384**.
- Trước indexing: V2 **0** hàng. Sau indexing: V2 **332** hàng. Thời gian embedding: 10.075 giây.
- A_fixed **287 → 287**; B_paragraph **296 → 296**.
- Đã đối chiếu toàn bộ ID, document_id, source, page, text, metadata và `vector_dims(embedding)` giữa JSON index-ready và các hàng DB của strategy V2.
- Store Day06 dùng khóa `(strategy, chunk_id)`; câu `DELETE`/`UPSERT` đều giới hạn theo strategy. Vì vậy thao tác V2 không chạm các hàng A/B.

## Smoke retrieval (câu minh họa, ngoài benchmark test)

Các truy vấn dùng model Day06 thật và SQL pgvector; filter `chapter`, `subject`, `extraction_quality` chạy qua JSONB containment, còn `document_id/page` là điều kiện cột SQL. Không chấm đúng/sai hoặc grounding từ kết quả này.

### 1. Bảng chân trị của E(p,q,r) ở phần biểu thức logic

Filter: `{}`

| Rank | Chunk ID | Score | source_id | page | quality |
|---:|---|---:|---|---:|---|
| 1 | `chuong-1-co-so-logic:p13:c1:v2` | 0.8109 | `chuong-1-co-so-logic` | 13 | needs_review |
| 2 | `chuong-4-dai-so-boole:p74:c1:v2` | 0.7691 | `chuong-4-dai-so-boole` | 74 | needs_review |
| 3 | `chuong-1-co-so-logic:p17:c1:v2` | 0.7586 | `chuong-1-co-so-logic` | 17 | needs_review |

### 2. Quan hệ từ A đến B biểu diễn bằng ma trận như thế nào?

Filter: `{"chapter": 3}`

| Rank | Chunk ID | Score | source_id | page | quality |
|---:|---|---:|---|---:|---|
| 1 | `chuong-3-quan-he:p16:c1:v2` | 0.6836 | `chuong-3-quan-he` | 16 | needs_review |
| 2 | `chuong-3-quan-he:p20:c1:v2` | 0.6121 | `chuong-3-quan-he` | 20 | needs_review |
| 3 | `chuong-3-quan-he:p10:c1:v2` | 0.5907 | `chuong-3-quan-he` | 10 | needs_review |

### 3. Phép duyệt tiền tự trên cây có gốc

Filter: `{"subject": "discrete_math"}`

| Rank | Chunk ID | Score | source_id | page | quality |
|---:|---|---:|---|---:|---|
| 1 | `chuong-6-cay:p6:c1:v2` | 0.6303 | `chuong-6-cay` | 6 | ok |
| 2 | `chuong-6-cay:p5:c1:v2` | 0.6127 | `chuong-6-cay` | 5 | needs_review |
| 3 | `chuong-6-cay:p12:c1:v2` | 0.5943 | `chuong-6-cay` | 12 | needs_review |

### 4. Bảng chân trị của E(p,q,r)

Filter: `{"document_id": "chuong-1-co-so-logic", "page": 16}`

| Rank | Chunk ID | Score | source_id | page | quality |
|---:|---|---:|---|---:|---|
| 1 | `chuong-1-co-so-logic:p16:c1:v2` | 0.6133 | `chuong-1-co-so-logic` | 16 | ok |

### 5. Ví dụ về đồ thị và cây khung

Filter: `{"extraction_quality": "needs_review"}`

| Rank | Chunk ID | Score | source_id | page | quality |
|---:|---|---:|---|---:|---|
| 1 | `chuong-5-do-thi-phan-1:p1:c1:v2` | 0.6767 | `chuong-5-do-thi-phan-1` | 1 | needs_review |
| 2 | `chuong-5-do-thi-phan-1:p11:c1:v2` | 0.5572 | `chuong-5-do-thi-phan-1` | 11 | needs_review |
| 3 | `chuong-6-cay:p34:c1:v2` | 0.5502 | `chuong-6-cay` | 34 | needs_review |

## Giới hạn và bước tiếp theo

- Smoke test xác nhận truy vấn, thứ hạng, citation và filter, chưa chứng minh câu trả lời đúng hoặc evidence đủ. Chunk `needs_review` cần người đối chiếu PDF trước khi dùng để đánh giá grounding.
- Đã chạy Dense smoke; chưa chạy benchmark test hoặc xây/chấm bộ so sánh Dense, TF-IDF, Hybrid trên câu hỏi Lab07.
- Quyền chia sẻ PDF và các trích đoạn trong báo cáo chưa được xác minh; cần kiểm tra trước khi công bố.
