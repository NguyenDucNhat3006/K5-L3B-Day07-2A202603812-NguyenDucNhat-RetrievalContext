# Experiments and retrieval evidence

## Contents

- [Ingestion V1 to V2 audit](#ingestion-v1-to-v2-audit)
- [V2 index validation and smoke retrieval](#v2-index-validation-and-smoke-retrieval)
- [Dense, TF-IDF, and Hybrid RRF dev comparison](#dense-tf-idf-and-hybrid-rrf-dev-comparison)
- [Context engineering C0 and C1](#context-engineering-c0-and-c1)
- [A2 retrieval variants R0, R1, and R2](#a2-retrieval-variants-r0-r1-and-r2)
- [A1 agent dev evaluation and improvement analysis](#a1-agent-dev-evaluation-and-improvement-analysis)

Consolidated record of the V2 ingestion audit, index smoke checks, retrieval/context experiments, and dev-only agent variants. Original tables and per-case failure notes are retained; locked benchmark and run artifacts were not edited.

## Ingestion V1 to V2 audit

## Audit ingestion Cấu trúc rời rạc: v1 → v2

Đây là audit tại thời điểm tạo v2, trước khi index. Sau khi người dùng duyệt, v2 đã được index riêng; xem [báo cáo index và smoke retrieval](experiments.md#v2-index-validation-and-smoke-retrieval). Lệnh tạo v2 không embedding, ghi database, chạy benchmark hay thay dữ liệu chính thức.
SHA-256 của `chunks.json` v1: `7561e3a39e06b919b5872e2e3f9083c6ef2d67c739c5329464d6d7090aba515d`.

### Phạm vi nguồn

- Đã đọc 9 PDF, 389 trang vật lý.
- Trong `data/discrete_math/raw/` chỉ có 9 PDF; không có PPT/PPTX Chương 3. Vì vậy chưa thể xác nhận bộ 10 file gốc hay so sánh bản PDF/PPT Chương 3.
- Quyền chia sẻ PDF và các trích đoạn trong báo cáo chưa được xác minh; cần kiểm tra trước khi công bố hoặc đưa báo cáo lên remote.
- `source_id`, `source` và `page` là ID nguồn, đường dẫn và số trang vật lý của PDF hiện có. Trang chỉ chứa header/số trang có thể không có chunk v2.

### So sánh định lượng

| Chỉ số | v1 | v2 |
|---|---:|---:|
| Số chunks | 420 | 332 |
| Độ dài nhỏ nhất | 2 | 37 |
| Trung vị ký tự | 250.5 | 240.0 |
| Trung bình ký tự | 254.0 | 260.9 |
| Độ dài lớn nhất | 500 | 614 |
| Chunks <100 ký tự | 61 | 26 |
| Chunks chỉ số trang | 15 | 0 |
| Chunks vô nghĩa theo quy tắc | 42 | 0 |
| Chunks chứa ký tự font toán chưa giải mã | 252 | 173 |
| Chunks >620 ký tự | 0 | 0 |

Tỷ lệ chunk vô nghĩa theo quy tắc: **10.0%** ở v1 và **0.0%** ở v2.
Tỷ lệ chunk cần người kiểm tra ở v2: **256/332 = 77.1%**; đây là cờ rủi ro trích xuất, không phải tỷ lệ sai được chấm thủ công.
Số trang không tạo chunk sau lọc: **65**. Bảng chân trị có hàng/cột hợp lệ: **1** trang.

#### Theo tài liệu

| source_id | v1 | v2 | needs_review (v2) |
|---|---:|---:|---:|
| `bai-tap-chuong-5` | 15 | 12 | 12 |
| `bai-tap-chuong-6` | 7 | 5 | 5 |
| `chuong-1-co-so-logic` | 62 | 46 | 34 |
| `chuong-2-phep-dem` | 64 | 59 | 59 |
| `chuong-3-quan-he` | 51 | 37 | 25 |
| `chuong-4-dai-so-boole` | 84 | 68 | 55 |
| `chuong-5-do-thi-phan-1` | 45 | 42 | 29 |
| `chuong-5-do-thi-phan-2` | 50 | 28 | 16 |
| `chuong-6-cay` | 42 | 35 | 21 |

### Quy tắc v2 và giới hạn

- Loại số trang, header/footer lặp, bảng rỗng do PDF parser tạo và đoạn chỉ có nhãn hình. Giữ số trang vật lý ở trường `page`.
- Ưu tiên giữ trọn bài tập, định nghĩa, định lý, ví dụ và bảng trong một chunk. Mức 620 ký tự cho text dành chỗ cho citation header trong context budget 800 ký tự của Lab07; đơn vị dài hơn chỉ chia tại ranh giới dòng/câu, có cờ `long_semantic_unit_split`.
- Bảng chân trị chỉ chuyển Markdown khi hàng/cột đầy đủ, không có ô trống, các hàng nhị phân và số hàng là lũy thừa của 2. Bảng lệch cột được giữ dưới dạng text gốc và gắn `needs_review`.
- Ma trận, công thức font tùy biến và hình đồ thị không được suy đoán từ chuỗi nhãn/trọng số. Các chunk liên quan gắn `needs_review` và `quality_reasons`.
- Các trang hình có thể chứa evidence không hiện diện trong text; cần đối chiếu PDF trước khi dùng làm câu trả lời có dẫn nguồn. Lỗi dấu tiếng Việt còn có thể tồn tại sau giải mã VNI.

### Tương thích retrieval

- `chunks_v2.json` giữ đúng 6 trường của schema Day07: `id`, `text`, `source_id`, `source`, `page`, `metadata`. ID có hậu tố `:v2` và duy nhất.
- TF-IDF: tạo chỉ mục trong bộ nhớ cho **332** hàng; truy vấn khói trả **3** hit, pack context được **2** chunk / 559 ký tự. Không dùng benchmark để tính điểm.
- Context budget: **332/332** chunk riêng lẻ vừa 800 ký tự kể cả citation header. Bộ packer vẫn có thể bỏ hit nếu tổng nhiều chunk vượt ngân sách.
- Dense: **332** hàng ánh xạ được sang `src.models.Chunk` Day06. Audit này chỉ kiểm tra schema; truy vấn Dense thật sau khi index được ghi ở [báo cáo index và smoke retrieval](experiments.md#v2-index-validation-and-smoke-retrieval).
- Hybrid: chưa có triển khai hybrid trong Python của repo để chạy end-to-end. Các hàng có ID/text/metadata chung cho fusion sau này.

### 15 ví dụ trước/sau

#### 1. Trang bìa/header: `chuong-1-co-so-logic` trang 1

v1: 1 chunk (`chuong-1-co-so-logic:p1:c1`). v2: 0 chunk (`đã loại`).
Chất lượng v2: `không áp dụng`; lý do: `không có`.

Trước:

```text
CẤU TRÚC RỜI RẠC

1
```

Sau:

```text
(đã loại khỏi v2)
```

#### 2. Số trang đơn lẻ: `chuong-1-co-so-logic` trang 39

v1: 1 chunk (`chuong-1-co-so-logic:p39:c1`). v2: 0 chunk (`đã loại`).
Chất lượng v2: `không áp dụng`; lý do: `không có`.

Trước:

```text
39
```

Sau:

```text
(đã loại khỏi v2)
```

#### 3. Số trang đơn lẻ: `chuong-1-co-so-logic` trang 45

v1: 1 chunk (`chuong-1-co-so-logic:p45:c1`). v2: 0 chunk (`đã loại`).
Chất lượng v2: `không áp dụng`; lý do: `không có`.

Trước:

```text
45
```

Sau:

```text
(đã loại khỏi v2)
```

#### 4. Header lặp: `chuong-3-quan-he` trang 25

v1: 1 chunk (`chuong-3-quan-he:p25:c1`). v2: 0 chunk (`đã loại`).
Chất lượng v2: `không áp dụng`; lý do: `không có`.

Trước:

```text
Quan hệ thứ tự

25
```

Sau:

```text
(đã loại khỏi v2)
```

#### 5. Footer ngày và số trang: `chuong-4-dai-so-boole` trang 4

v1: 1 chunk (`chuong-4-dai-so-boole:p4:c1`). v2: 0 chunk (`đã loại`).
Chất lượng v2: `không áp dụng`; lý do: `không có`.

Trước:

```text
11/16/2026 Đại Số Boole Trang 4
```

Sau:

```text
(đã loại khỏi v2)
```

#### 6. Header lặp: `chuong-5-do-thi-phan-2` trang 33

v1: 1 chunk (`chuong-5-do-thi-phan-2:p33:c1`). v2: 0 chunk (`đã loại`).
Chất lượng v2: `không áp dụng`; lý do: `không có`.

Trước:

```text
Chương 2. Các bài toán về đường đi

33
```

Sau:

```text
(đã loại khỏi v2)
```

#### 7. Bảng chân trị có cấu trúc: `chuong-1-co-so-logic` trang 16

v1: 1 chunk (`chuong-1-co-so-logic:p16:c1`). v2: 1 chunk (`chuong-1-co-so-logic:p16:c1:v2`).
Chất lượng v2: `ok`; lý do: `không có`.

Trước:

```text
Biểu thức logic

Ví dụ: Cho E(p,q,r) =(p  q)  r .
Ta có bảng chân trị sau:
p q r p  q (p  q)  r
0 0 0 0 1
0 0 1 0 1
0 1 0 1 0
0 1 1 1 1
1 0 0 1 0
1 0 1 1 1
1 1 0 1 0
1 1 1 1 1
16
```

Sau:

```text
Ví dụ: Cho E(p,q,r) =(p ∨ q) → r .
Ta có bảng chân trị sau:

| p | q | r | p ∨ q | (p ∨ q) → r |
| --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | 1 |
| 0 | 0 | 1 | 0 | 1 |
| 0 | 1 | 0 | 1 | 0 |
| 0 | 1 | 1 | 1 | 1 |
| 1 | 0 | 0 | 1 | 0 |
| 1 | 0 | 1 | 1 | 1 |
| 1 | 1 | 0 | 1 | 0 |
| 1 | 1 | 1 | 1 | 1 |
```

#### 8. Bảng chân trị lệch cột: `chuong-4-dai-so-boole` trang 19

v1: 1 chunk (`chuong-4-dai-so-boole:p19:c1`). v2: 1 chunk (`chuong-4-dai-so-boole:p19:c1:v2`).
Chất lượng v2: `needs_review`; lý do: `table_not_verified`.

Trước:

```text
Khi đó f là hàm Bool theo 3 biến x,y,x có bảng chân trị như sau: x y z f 0 0 0 0 0 0 1 0 0 1 0 0 0 1 1 1 1 0 0 0 1 0 1 1 1 1 0 1 1 1 1 1 11/16/2026 Đại Số Boole Trang 19

x y z f

0 0 0 0

0 0 1 0

0 1 0 0

0 1 1 1

1 0 0 0

1 0 1 1

1 1 0 1

1 1 1 1

11/16/2026 Đại Số Boole Trang 19
```

Sau:

```text
Khi đó f là hàm Bool theo 3 biến x,y,x có bảng chân trị như sau: x y z f 0 0 0 0 0 0 1 0 0 1 0 0 0 1 1 1 1 0 0 0 1 0 1 1 1 1 0 1 1 1 1 1
```

#### 9. Bảng ở dạng hình: `chuong-4-dai-so-boole` trang 73

v1: 1 chunk (`chuong-4-dai-so-boole:p73:c1`). v2: 1 chunk (`chuong-4-dai-so-boole:p73:c1:v2`).
Chất lượng v2: `needs_review`; lý do: `incomplete_prompt, table_not_verified`.

Trước:

```text
 Bước 2: Từ yêu cầu bài toán ta có bảng chân trị: 11/16/2026 Đại Số Boole Trang 73
```

Sau:

```text
- Bước 2: Từ yêu cầu bài toán ta có bảng chân trị:
```

#### 10. Ma trận dạng hình: `chuong-3-quan-he` trang 8

v1: 1 chunk (`chuong-3-quan-he:p8:c1`). v2: 1 chunk (`chuong-3-quan-he:p8:c1:v2`).
Chất lượng v2: `needs_review`; lý do: `matrix_requires_visual_check`.

Trước:

```text
Quan hệ hai ngôi

3. Biểu diễn quan hệ

Định nghĩa.

Cho R là quan hệ từ A = {1,2,3,4} đến B = {u,v,w},

R = {(1,u),(1,v),(2,w),(3,w),(4,u)}.

Khi đó R có thể biễu diễn như sau

Đây là ma trận cấp 4×3 biễu diễn

cho quan hệ R

8
```

Sau:

```text
Định nghĩa.
Cho R là quan hệ từ A = {1,2,3,4} đến B = {u,v,w},
R = {(1,u),(1,v),(2,w),(3,w),(4,u)}.
Khi đó R có thể biễu diễn như sau
Đây là ma trận cấp 4×3 biễu diễn
cho quan hệ R
```

#### 11. Hình đồ thị: `bai-tap-chuong-5` trang 1

v1: 2 chunk (`bai-tap-chuong-5:p1:c1, bai-tap-chuong-5:p1:c2`). v2: 1 chunk (`bai-tap-chuong-5:p1:c1:v2`).
Chất lượng v2: `needs_review`; lý do: `diagram_requires_visual_check, graph_exercise_requires_visual_check`.

Trước:

```text
ĐẠI CƯƠNG VỀ ĐỒ THỊ

Bài 01. Tìm số đỉnh, số cạnh, bậc của mỗi đỉnh trong các đồ thì vô hướng sau:

(chỉ rõ đỉnh cô lập và đỉnh treo, nếu có)

a.

a b c a b

b.

R

f e d e d c

Q

c. P

T

S

Bài 02. Xác định số định, số cạnh, số bậc vào và số ra của mỗi đỉnh đối với các

đồ thị có hướng:

a. b.

a b a b

d c a d c

b

e d

c.

c

Bài 03. Hãy vẽ các đồ thị :

a. K b. K c. K d. C e. W

7 1,8 4,4 7 7

Bài 04. Xét xem các đồ thị sau có là đồ thị lư…
```

Sau:

```text
ĐẠI CƯƠNG VỀ ĐỒ THỊ
Bài 01. Tìm số đỉnh, số cạnh, bậc của mỗi đỉnh trong các đồ thì vô hướng sau:
(chỉ rõ đỉnh cô lập và đỉnh treo, nếu có)
a.
a b c a b
b.
R
f e d e d c
Q
c. P
T
S

Bài 02. Xác định số định, số cạnh, số bậc vào và số ra của mỗi đỉnh đối với các
đồ thị có hướng:
a. b.
a b a b
d c a d c
b
e d
c.
c

Bài 03. Hãy vẽ các đồ thị :
a. K b. K c. K d. C e. W
7 1,8 4,4 7 7

Bài 04. Xét xem các đồ thị sau có là đồ thị lưỡng phân không:
a. b.
b c
a b
c
d e
a d
c. b c e
b
d. c
a
a d
e
f d
e
f

Bài 05. Các đồ thị sau có bao nhiêu đỉnh, cạnh?
a. K b. C c. W d. K
n n n m,n
```

#### 12. Bài tập ma trận: `bai-tap-chuong-5` trang 2

v1: 3 chunk (`bai-tap-chuong-5:p2:c1, bai-tap-chuong-5:p2:c2, bai-tap-chuong-5:p2:c3`). v2: 2 chunk (`bai-tap-chuong-5:p2:c1:v2, bai-tap-chuong-5:p2:c2:v2`).
Chất lượng v2: `needs_review`; lý do: `diagram_requires_visual_check, graph_exercise_requires_visual_check, matrix_requires_visual_check, unmapped_formula_symbol`.

Trước:

```text
Bài 06. Một đồ thị vô hướng có các đỉnh có các bậc lần lượt là: 4, 3, 3, 2, 2. Tính

số cạnh và vẽ đồ thị này.

Bài 07. Tính số đỉnh của một đồ thị đều bậc 4 và có 10 cạnh.

Bài 08. Một đồ thị có 100 đỉnh, mỗi đỉnh đều có bậc 50. Tính số cạnh của nó.

Bài 09. Tìm hợp các cặp đồ thị (giả sử các cạnh có các đầu mút trùng nhau là như

nhau) :

a. b. a b a f b

a

f b

b

f e

e

e

c d

d c d c g e

Bài 10. Nếu đơn đồ thị G có 15 cạnh và G có 13 cạn…
```

Sau:

```text
Bài 06. Một đồ thị vô hướng có các đỉnh có các bậc lần lượt là: 4, 3, 3, 2, 2. Tính
số cạnh và vẽ đồ thị này.

Bài 07. Tính số đỉnh của một đồ thị đều bậc 4 và có 10 cạnh.

Bài 08. Một đồ thị có 100 đỉnh, mỗi đỉnh đều có bậc 50. Tính số cạnh của nó.

Bài 09. Tìm hợp các cặp đồ thị (giả sử các cạnh có các đầu mút trùng nhau là như
nhau) :
a. b. a b a f b
a
f b
b
f e
e
e
c d
d c d c g e

Bài 10. Nếu đơn đồ thị G có 15 cạnh và G có 13 cạnh khi đó G và G có bao
nhiêu đỉnh ?

Bài 11. Biểu diễn các đồ thị sau bằng ma trận liền kề:
a. a b b. a b c
d c
e d
c. a b d. a b c
c d d e

Bài 12. Biểu diễn cá…
```

#### 13. Bài tập cây/ma trận: `bai-tap-chuong-6` trang 2

v1: 3 chunk (`bai-tap-chuong-6:p2:c1, bai-tap-chuong-6:p2:c2, bai-tap-chuong-6:p2:c3`). v2: 2 chunk (`bai-tap-chuong-6:p2:c1:v2, bai-tap-chuong-6:p2:c2:v2`).
Chất lượng v2: `needs_review`; lý do: `diagram_requires_visual_check, matrix_requires_visual_check, table_columns_unreliable, unmapped_formula_symbol`.

Trước:

```text
Bài 10: Đồ thị K với n=3, 4, 5 có bao nhiêu cây khung không đẳng cấu?

n

Bài 11: Tìm cây khung nhỏ nhất của các đồ thị sau theo thuật toán Kruskal và Prim.

42

a b

4 10 14 3

3 1 11

c d e f

5 20 9

15

7

g h

a 5 b 4 c

1

3 5 e 7 6 1

3 8 4

c 1 d g 4 h 2 i

Bài 12:Cây khung lớn nhất của một đồ thị liên thông có trọng số là cây khung có tổng trọng số lớn

nhất. Hãy đề xuất hai thuật toán để tìm cây khung lớn nhất của một đồ thị liên thông …
```

Sau:

```text
Bài 10: Đồ thị K với n=3, 4, 5 có bao nhiêu cây khung không đẳng cấu?
n

Bài 11: Tìm cây khung nhỏ nhất của các đồ thị sau theo thuật toán Kruskal và Prim.
42
a b
4 10 14 3
3 1 11
c d e f
5 20 9
15
7
g h
a 5 b 4 c
1

3 5 e 7
6 1
3 8
4

c 1 d g 4 h 2 i

Bài 12:Cây khung lớn nhất của một đồ thị liên thông có trọng số là cây khung có tổng trọng số lớn
nhất. Hãy đề xuất hai thuật toán để tìm cây khung lớn nhất của một đồ thị liên thông có trọng số.
(HD: Nên tận dụng hai thuật toán đã học Prim/Kruskal)

Bài 13: Áp dụng các thuật toán trên để tìm cây khung lớn nhất của các đồ thị trong bài 11.

Bài …
```

#### 14. Bài tập nhiều ý: `bai-tap-chuong-5` trang 5

v1: 1 chunk (`bai-tap-chuong-5:p5:c1`). v2: 1 chunk (`bai-tap-chuong-5:p5:c1:v2`).
Chất lượng v2: `needs_review`; lý do: `diagram_requires_visual_check, graph_exercise_requires_visual_check, table_columns_unreliable`.

Trước:

```text
CÁC BÀI TOÁN VỀ ĐƯỜNG ĐI
Bài 01. Các đồ thị sau có chu trình Euler, đường đi Euler hay không? Nếu có hãy
xây dựng chu trình, đường đi đó.
a
e
d

g
a b
c. d.
e b
f
c
d
b c
a
e. f.
e f

h i j k
a b e f a
g. h.
d e
c d g h
b c
f
Bài 02. Một người nào đó có thể đi qua những chiếc cầu như trên hình vẽ sau,
mỗi chiếc cầu đi qua đúng 1 lần và lại trở về nơi xuất phát được không?
```

Sau:

```text
CÁC BÀI TOÁN VỀ ĐƯỜNG ĐI
Bài 01. Các đồ thị sau có chu trình Euler, đường đi Euler hay không? Nếu có hãy
xây dựng chu trình, đường đi đó.

f

e f

h i j k
a b e f a
g. h.
d e
c d g h
b c
f

Bài 02. Một người nào đó có thể đi qua những chiếc cầu như trên hình vẽ sau,
mỗi chiếc cầu đi qua đúng 1 lần và lại trở về nơi xuất phát được không?
```

#### 15. Công thức: `chuong-2-phep-dem` trang 54

v1: 1 chunk (`chuong-2-phep-dem:p54:c1`). v2: 1 chunk (`chuong-2-phep-dem:p54:c1:v2`).
Chất lượng v2: `needs_review`; lý do: `table_columns_unreliable, unmapped_formula_symbol`.

Trước:

```text
K h a i t r i ể n m ở r ộ n g n h ị t h ứ c N e w t o n

n ( a  a  . . .  a )  1 2 k n    n n n a a . . . a 1 2 k 1 2 k n , . . . , n n  n  . . .  n  n 1 k 1 2 k với các số nguyên không âm n ,n ,…,n 1 2 k thoả n +n +…+n = n, ký hiệu 1 2 k  n  n!      n , n ,..., n n !n !...n !   1 2 k 1 2 k 54
```

Sau:

```text
n ( a  a  . . .  a )  1 2 k n    n n n a a . . . a 1 2 k 1 2 k n , . . . , n n  n  . . .  n  n 1 k 1 2 k với các số nguyên không âm n ,n ,…,n 1 2 k thoả n +n +…+n = n, ký hiệu 1 2 k  n  n!      n , n ,..., n n !n !...n !   1 2 k 1 2 k 54
```

## V2 index validation and smoke retrieval

## Kiểm tra index corpus Cấu trúc rời rạc V2

V2 được dùng làm corpus thử nghiệm theo quyết định của người dùng. Báo cáo này chỉ ghi indexing và smoke retrieval, không ghi điểm benchmark.

### Nguồn và chính sách chunk

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

#### 22 chunk vượt mục tiêu 500 ký tự

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

### PostgreSQL + pgvector

- Strategy riêng: `D07_discrete_math_v2`. Model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; chiều vector: **384**.
- Trước indexing: V2 **0** hàng. Sau indexing: V2 **332** hàng. Thời gian embedding: 10.075 giây.
- A_fixed **287 → 287**; B_paragraph **296 → 296**.
- Đã đối chiếu toàn bộ ID, document_id, source, page, text, metadata và `vector_dims(embedding)` giữa JSON index-ready và các hàng DB của strategy V2.
- Store Day06 dùng khóa `(strategy, chunk_id)`; câu `DELETE`/`UPSERT` đều giới hạn theo strategy. Vì vậy thao tác V2 không chạm các hàng A/B.

### Smoke retrieval (câu minh họa, ngoài benchmark test)

Các truy vấn dùng model Day06 thật và SQL pgvector; filter `chapter`, `subject`, `extraction_quality` chạy qua JSONB containment, còn `document_id/page` là điều kiện cột SQL. Không chấm đúng/sai hoặc grounding từ kết quả này.

#### 1. Bảng chân trị của E(p,q,r) ở phần biểu thức logic

Filter: `{}`

| Rank | Chunk ID | Score | source_id | page | quality |
|---:|---|---:|---|---:|---|
| 1 | `chuong-1-co-so-logic:p13:c1:v2` | 0.8109 | `chuong-1-co-so-logic` | 13 | needs_review |
| 2 | `chuong-4-dai-so-boole:p74:c1:v2` | 0.7691 | `chuong-4-dai-so-boole` | 74 | needs_review |
| 3 | `chuong-1-co-so-logic:p17:c1:v2` | 0.7586 | `chuong-1-co-so-logic` | 17 | needs_review |

#### 2. Quan hệ từ A đến B biểu diễn bằng ma trận như thế nào?

Filter: `{"chapter": 3}`

| Rank | Chunk ID | Score | source_id | page | quality |
|---:|---|---:|---|---:|---|
| 1 | `chuong-3-quan-he:p16:c1:v2` | 0.6836 | `chuong-3-quan-he` | 16 | needs_review |
| 2 | `chuong-3-quan-he:p20:c1:v2` | 0.6121 | `chuong-3-quan-he` | 20 | needs_review |
| 3 | `chuong-3-quan-he:p10:c1:v2` | 0.5907 | `chuong-3-quan-he` | 10 | needs_review |

#### 3. Phép duyệt tiền tự trên cây có gốc

Filter: `{"subject": "discrete_math"}`

| Rank | Chunk ID | Score | source_id | page | quality |
|---:|---|---:|---|---:|---|
| 1 | `chuong-6-cay:p6:c1:v2` | 0.6303 | `chuong-6-cay` | 6 | ok |
| 2 | `chuong-6-cay:p5:c1:v2` | 0.6127 | `chuong-6-cay` | 5 | needs_review |
| 3 | `chuong-6-cay:p12:c1:v2` | 0.5943 | `chuong-6-cay` | 12 | needs_review |

#### 4. Bảng chân trị của E(p,q,r)

Filter: `{"document_id": "chuong-1-co-so-logic", "page": 16}`

| Rank | Chunk ID | Score | source_id | page | quality |
|---:|---|---:|---|---:|---|
| 1 | `chuong-1-co-so-logic:p16:c1:v2` | 0.6133 | `chuong-1-co-so-logic` | 16 | ok |

#### 5. Ví dụ về đồ thị và cây khung

Filter: `{"extraction_quality": "needs_review"}`

| Rank | Chunk ID | Score | source_id | page | quality |
|---:|---|---:|---|---:|---|
| 1 | `chuong-5-do-thi-phan-1:p1:c1:v2` | 0.6767 | `chuong-5-do-thi-phan-1` | 1 | needs_review |
| 2 | `chuong-5-do-thi-phan-1:p11:c1:v2` | 0.5572 | `chuong-5-do-thi-phan-1` | 11 | needs_review |
| 3 | `chuong-6-cay:p34:c1:v2` | 0.5502 | `chuong-6-cay` | 34 | needs_review |

### Giới hạn và bước tiếp theo

- Smoke test xác nhận truy vấn, thứ hạng, citation và filter, chưa chứng minh câu trả lời đúng hoặc evidence đủ. Chunk `needs_review` cần người đối chiếu PDF trước khi dùng để đánh giá grounding.
- Đã chạy Dense smoke; chưa chạy benchmark test hoặc xây/chấm bộ so sánh Dense, TF-IDF, Hybrid trên câu hỏi Lab07.
- Quyền chia sẻ PDF và các trích đoạn trong báo cáo chưa được xác minh; cần kiểm tra trước khi công bố.

## Dense, TF-IDF, and Hybrid RRF dev comparison

## So sánh Dense, TF-IDF và Hybrid RRF trên corpus V2 — dev

### Phạm vi và dữ liệu

- Corpus: đúng **332** chunk trong `chunks_v2.json` đã duyệt, SHA-256 `979a0baaf2f34735592bde1aeaf2bdb29b5a8f336f3f0bcb3fee699056f57990`. Cả ba phương pháp dùng cùng ID, text, source, page và metadata; cờ `needs_review` không bị bỏ hoặc sửa.
- Dense truy vấn thực tế PostgreSQL/pgvector strategy `D07_discrete_math_v2`, model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, vector **384** chiều. Trước và sau chạy: A_fixed **287**, B_paragraph **296**, V2 **332** hàng, cùng chiều 384.
- TF-IDF xây chỉ mục trong bộ nhớ từ text của đúng 332 chunk V2. Tokenizer hiện tại là Unicode `\w+`, chữ thường, chưa tách từ tiếng Việt. Không ghi database hay embed lại corpus.
- Hybrid lấy tối đa **20** ứng viên từ mỗi nhánh, cộng `1/(60 + rank)` cho mỗi lần một chunk xuất hiện, rồi trả Top-3. `score` của Dense là cosine similarity, TF-IDF là cosine TF-IDF, Hybrid là điểm RRF; không so sánh trị tuyệt đối giữa các thang này.

### Benchmark và cách chấm

- [Dev](../../data/benchmark_v2_dev.json): **15** câu có đáp án + **2** câu thiếu bằng chứng. [Test](../../data/benchmark_v2_test.json): **5** câu có đáp án + **2** câu thiếu bằng chứng. Hash của từng split nằm trong [manifest](../../data/benchmark_v2_manifest.json). Test **chưa được đưa vào retrieval hoặc dùng để chọn cấu hình**.
- Mọi truy vấn dev dùng nguyên câu hỏi tiếng Việt, `filters={}`. Gold, đáp án và vị trí evidence chỉ được dùng **sau** khi retrieval để chấm; không truyền vào embedding query, TF-IDF hoặc SQL filter.
- Hit@1/Evidence Hit@3 yêu cầu đúng chunk ID, source ID, trang vật lý và chuỗi evidence trong text (chỉ gộp khoảng trắng do PDF xuống dòng). Context Evidence Rate yêu cầu evidence đó nằm trong context cuối, được pack từ Top-3 với ngân sách **800 ký tự Unicode gồm citation header**. Mẫu số chỉ gồm 15 câu có đáp án. Đây là metric định vị evidence bằng chuỗi, **không phải kiểm tra thủ công câu trả lời có đủ căn cứ**.
- Hai câu Chương 2 có `needs_review` vì cờ trích xuất bảng. Evidence dùng để đặt câu d04/t02 đã đối chiếu trực quan PDF trang 29 và 36; cờ chất lượng trong V2 và trace vẫn giữ nguyên. Các gold còn lại được đối chiếu với text V2, chưa có vòng chấm thủ công toàn bộ trang PDF.

### Kết quả dev thực đo

| Phương pháp | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Median retrieval | P95 retrieval |
|---|---:|---:|---:|---:|---:|
| Dense pgvector | **9/15 (60,0%)** | **11/15 (73,3%)** | **11/15 (73,3%)** | **65,6 ms** | 105,0 ms |
| TF-IDF | **12/15 (80,0%)** | **13/15 (86,7%)** | **13/15 (86,7%)** | **2,3 ms** | 5,2 ms |
| Hybrid RRF | **11/15 (73,3%)** | **13/15 (86,7%)** | **12/15 (80,0%)** | **71,8 ms** | 80,1 ms |

Mỗi phương pháp trả 51 hit trên 17 truy vấn dev, không có truy vấn rỗng. Hai câu thiếu evidence **không** được tính vào ba tỷ lệ trên. Cả ba vẫn trả các chunk liên quan chủ đề cho d16/d17; sự có mặt của hit không chứng minh có thể trả lời, và chưa có agent để chấm abstention.

Thời gian khởi động gồm tải model, xác minh 332 hàng DB và tạo TF-IDF là **15,548 giây**; riêng tạo TF-IDF **0,015 giây**. Latency trong bảng đo một lần chạy cục bộ trên máy hiện tại, gồm query embedding và truy vấn SQL cho Dense/Hybrid, không gồm khởi động. Phí API trực tiếp bằng **0 USD** vì dùng model local; chi phí máy/điện **chưa đo**. Xem [metrics tương thích PowerShell](../../starter/results/discrete_math_v2/dev-20261116T043019037173Z/metrics_portable.json), [Top-3 traces](../../starter/results/discrete_math_v2/dev-20261116T043019037173Z/traces.json) và [run manifest](../../starter/results/discrete_math_v2/dev-20261116T043019037173Z/run_manifest.json). `metrics.json` ban đầu được giữ nguyên; bản portable chỉ đổi khóa `n/N` thành `count/total` để PowerShell đọc được. Các file trong `starter/results/` là dữ liệu local bị Git bỏ qua; chạy lại tạo thư mục mới.

### Lỗi và đánh đổi cụ thể

1. **d01 — định nghĩa mệnh đề:** TF-IDF không đưa chunk đúng `chuong-1-co-so-logic:p4:c1:v2` vào Top-3; Top-1 là chunk cây khung. Dense xếp evidence ở hạng 2, còn Hybrid ở hạng 1 nhờ chunk này có hạng 2 Dense và hạng 4 TF-IDF. Tokenizer hiện tại dễ bị từ chung trong câu hỏi chi phối; cần thử bỏ stopword/tách từ trên dev trong thí nghiệm riêng.
2. **d03 — bảng chân trị E(p,q,r):** Dense và TF-IDF đều bỏ lỡ bảng đúng trong Top-3. Hybrid tìm được `chuong-1-co-so-logic:p16:c1:v2` ở hạng 3, nhưng context 800 ký tự đã chứa hai hit trước nên không còn chỗ cho bảng. Vì vậy Evidence Hit@3 đúng, Context Evidence Rate sai. Đây là lỗi chọn context, không phải lỗi bảng gold.
3. **d05 — quan hệ thứ tự:** TF-IDF xếp định nghĩa đúng `chuong-3-quan-he:p23:c1:v2` hạng 1; Dense bỏ lỡ. RRF đưa các đoạn cùng chủ đề nhưng không chứa ba tính chất lên Top-3, nên Hybrid mất hit đúng của TF-IDF. RRF mặc định ưu tiên đồng thuận hai nhánh, kể cả khi cả hai cùng xếp cao đoạn tổng quan.
4. **d09 — đồ thị lưỡng phân:** TF-IDF xếp định nghĩa đúng `chuong-5-do-thi-phan-1:p24:c1:v2` hạng 1. Dense ưu tiên các bài tập/hình có `needs_review`; Hybrid theo các đoạn này và bỏ lỡ định nghĩa trong Top-3. Cờ chất lượng được hiển thị để người đọc nhận ra rủi ro nhưng chưa được dùng làm filter/rerank.

### Quyết định trên dev và phần còn thiếu

Theo ba metric evidence và latency đo trên dev, **TF-IDF Top-3 với context budget 800 ký tự** là ứng viên hiện tại cho cấu hình được chọn; Dense và Hybrid giữ làm đối chứng. Quyết định này được ghi trước khi chạy test, nhưng tiêu chí ưu tiên không được ghi thành artifact trước lần chạy dev đầu tiên. Không chỉnh RRF theo test. Nếu thử thêm cấu hình tokenizer/context trên dev, phải lưu run mới và chốt lại trước test.

- Chưa chạy **7 câu test**, chưa chấm context thủ công mức 0/1/2, câu trả lời agent, citation hợp lệ hoặc abstention. Retrieval hit không thay thế các phần này của [BENCHMARK.md](../../BENCHMARK.md).
- Cần kiểm tra thủ công các trường hợp `needs_review`, nhất là bảng/ma trận/hình và các gold chưa đối chiếu trực quan PDF. Corpus có **256/332** chunk mang cờ này; hai câu không đủ bằng chứng đã được kiểm tra trên toàn bộ V2, không chỉ Top-3.
- Cần thêm vòng dev có giả thuyết và đo lại cho tokenizer tiếng Việt, context packing và RRF trước khi khẳng định cấu hình tối ưu. Tài liệu Chương 3 dạng PPT/PPTX thứ 10 chưa có; quyền chia sẻ PDF và trích đoạn vẫn cần xác minh.

## Context engineering C0 and C1

## Context Engineering trên TF-IDF Top-3 — dev

### Phạm vi và cách làm

Thí nghiệm này dùng nguyên [Top-3 TF-IDF đã lưu](../../starter/results/discrete_math_v2/dev-20261116T043019037173Z/traces.json) cho **17 câu dev**; SHA-256 của trace nguồn là `33d0d4c73598230273cf9b27533b9bfea7d888f2747dceb8c377f41ec0f16022`. Không chạy lại retrieval, không mở benchmark test, không embed corpus, không truy cập database và không sửa kết quả cũ. Cả hai cấu hình có cùng ba candidate theo thứ hạng gốc và cùng ngân sách **800 ký tự Unicode**.

- **C0:** Duyệt Top-3 theo thứ hạng TF-IDF; thêm cả chunk nếu vừa ngân sách, bỏ qua chunk không vừa. Đây là baseline packing với header citation bổ sung `extraction_quality`; nó không ghi đè trace baseline cũ.
- **C1:** Xét các tập con của cùng Top-3, chỉ chọn **chunk đầy đủ** vừa ngân sách. Điểm chọn dựa trên rank, `content_type`, tín hiệu loại câu hỏi (định nghĩa/định lý/bảng/ví dụ), cờ chất lượng và `semantic_unit_split`. C1 không dùng gold, đáp án chuẩn hoặc trang gold. Chunk có cờ hình/ma trận/công thức được giảm ưu tiên, nhưng `needs_review` do bố cục bảng không bị coi mặc định là vô dụng.
- Mỗi block context chứa `chunk_id`, đường dẫn `source`, `page`, `extraction_quality` và **toàn bộ text**. Metadata và các `quality_reasons` đầy đủ nằm trong trace retrieval gốc. Bộ kiểm tra đối chiếu từng block với JSON V2 và xác nhận số trang nằm trong PDF nguồn; việc xem trực quan PDF mới thực hiện cho d04.

Gold chỉ được dùng **sau khi pack** để tính Context Evidence Rate. Chỉ số tự động đòi đúng ID, nguồn/trang và chuỗi evidence trong một chunk đã chọn; nó không xác nhận đáp án được hỗ trợ đầy đủ. Tôi đã đọc context của cả 15 câu có đáp án và 2 câu thiếu evidence cho **mỗi** cấu hình, rồi ghi nhãn/lý do tại [audit 34 context](context_engineering_dev_audit.json). Rubric thủ công: **0** không có evidence; **1** có evidence liên quan nhưng thiếu điều kiện/nguồn; **2** đủ evidence và citation. Hai câu thiếu evidence được chấm riêng về việc context có buộc phải từ chối hay không, chưa phải điểm abstention của agent.

### Kết quả thực đo

| Cấu hình | Context Evidence Rate | Thủ công: mức 0 / 1 / 2 | Trung bình /2 | Context hỗ trợ từ chối | Ký tự TB / tối đa | MiniLM tokens TB / tối đa | Median packing |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 | **13/15 (86,7%)** | **2 / 0 / 13** | **1,733/2** | **2/2** | **701 / 797** | **254,5 / 367** | **0,0186 ms** |
| C1 | **12/15 (80,0%)** | **2 / 1 / 12** | **1,667/2** | **2/2** | **700,2 / 792** | **256,3 / 367** | **0,0632 ms** |

Ngân sách của cả hai là **800 ký tự**, tính cả citation header; trung bình mỗi context chứa **2 chunk**. Cột token đếm bằng tokenizer MiniLM như một số đo tham khảo; **chưa đặt ngân sách token LLM** vì model agent chưa được chọn. Latency trong bảng chỉ đo đóng gói context từ Top-3 đã lưu. Retrieval TF-IDF có median **2,3 ms** trong run gốc và giống nhau cho hai cấu hình; không cộng các median với nhau thành một phép đo end-to-end. Thời gian packing rất nhỏ và chỉ đo một lượt trên máy hiện tại, nên chênh lệch không đủ để suy luận về hiệu năng khi tải lớn. Phí API trực tiếp **0 USD**; chi phí máy/điện chưa đo.

Xem [metrics tự động](../../starter/results/discrete_math_v2/context-dev-20261116T044835296260Z/metrics_auto.json), [metrics có audit thủ công](../../starter/results/discrete_math_v2/context-dev-20261116T044835296260Z/metrics_reviewed.json), [context traces](../../starter/results/discrete_math_v2/context-dev-20261116T044835296260Z/traces.json) và [run manifest](../../starter/results/discrete_math_v2/context-dev-20261116T044835296260Z/run_manifest.json). Run mới nằm trong `starter/results/`, được Git bỏ qua; file cũ không bị ghi đè.

### Audit từng câu dev

| ID | C0 | C1 | Evidence và lý do chính |
|---|---:|---:|---|
| d01 | 0 | 0 | Top-3 TF-IDF thiếu định nghĩa mệnh đề ở Chương 1 p4; các đoạn về loại mệnh đề/biểu thức logic không nêu giá trị chân lý. |
| d02 | 2 | 2 | Chương 1 p11 ghi rõ “P là điều kiện đủ của Q”; p12 có ký hiệu cần review nhưng không cần dùng. |
| d03 | 0 | 0 | Không có bảng chân trị p16 trong Top-3; các đoạn p23/p21 có ký hiệu công thức lỗi, không có hàng p=0, q=1, r=0. |
| d04 | 2 | 2 | Chương 2 p29 nêu 5+6=11; text `needs_review` vẫn đọc rõ và đã đối chiếu PDF trang 29. Công thức lỗi ở p57 không dùng. |
| d05 | 2 | 2 | Chương 3 p23 liệt kê phản xạ, phản xứng, bắc cầu với citation đầy đủ. |
| d06 | 2 | 2 | Chương 3 p44 nêu trực tiếp các phần tử tối đại 12, 20, 25. |
| d07 | 2 | 2 | Chương 4 p18 nêu 1 là tán thành và 0 là bác bỏ; đoạn `needs_review` khác không liên quan. |
| d08 | 2 | 2 | Chương 5 phần 1 p14 có đủ điều kiện và kết luận của Định lý 1.2. |
| d09 | 2 | 2 | Chương 5 phần 1 p24 đủ định nghĩa đồ thị lưỡng phân. C1 bỏ p3 có cờ hình, thêm p43 nhưng không tăng điểm. |
| d10 | 2 | 2 | Chương 5 phần 1 p37 nêu đường đi nối hai đỉnh. |
| d11 | 2 | 1 | C0 giữ p42 với đường đi **hai chiều**; C1 chọn p37/p43, chỉ có khái niệm liên thông nói chung, thiếu điều kiện của liên thông mạnh. |
| d12 | 2 | 2 | Chương 5 phần 2 p8 nêu mọi đỉnh có bậc chẵn; p14 nói trường hợp đường đi Euler khác. |
| d13 | 2 | 2 | Chương 5 phần 2 p14 nêu đúng hai đỉnh bậc lẻ; p6 có ký hiệu lỗi nhưng không cần để trả lời. |
| d14 | 2 | 2 | Chương 6 p11 liệt kê tiền tự, trung tự, hậu tự ở cả hai context. |
| d15 | 2 | 2 | Chương 6 p25 định nghĩa tổng trọng số các cạnh nhỏ nhất. |
| d16 | Từ chối | Từ chối | p29 cho số áo và số cách chọn nhưng **không có giá áo**; `needs_review` ở đây không làm mất phép cộng, nhưng không thể so sánh giá. |
| d17 | Từ chối | Từ chối | Đoạn Dijkstra p43 nêu điều kiện thuật toán nhưng **không có số mili giây**; không suy ra thời gian chạy. |

“Từ chối” trong hai hàng cuối nghĩa là **context chỉ hỗ trợ quyết định từ chối**; chưa có agent để xác nhận nó thật sự từ chối. Toàn bộ 34 nhãn, excerpt và lý do cụ thể có trong JSON audit.

### Phân tích lỗi và quyết định

- **d03 là lỗi retrieval đầu vào:** TF-IDF Top-3 không chứa bảng p16; cả C0/C1 chỉ nhận ba chunk đã trả về nên không thể tạo evidence còn thiếu. Không tái tạo hàng bảng bằng suy luận từ hình/công thức.
- **d05 là ca thành công của baseline TF-IDF:** chunk định nghĩa p23 đứng hạng 1 và được cả hai packer giữ; lỗi Hybrid RRF trước đó không xuất hiện khi dùng TF-IDF Top-3 cố định.
- **d09 cho thấy cờ review cần đọc theo ngữ cảnh:** chunk p3 có cờ hình cần kiểm tra nhưng p24 đã đủ định nghĩa. C1 loại p3, song chất lượng câu trả lời vẫn mức 2 ở cả hai.
- **d11 là hồi quy do C1:** bộ chọn cộng điểm cho `content_type=definition` và tối ưu tập con ngắn, nên chọn p37 thay p42 dù cặp p42+p43 vẫn vừa 800 ký tự. Đây là lỗi tiêu chí chọn, không phải thiếu ngân sách hay thiếu nguồn.

Đã cân nhắc mở rộng ngân sách nhưng **chưa chạy C2**: d01/d03 thiếu chunk gold ngay từ Top-3, còn d11 do utility của C1. Một run 1.200 ký tự chỉ nên thực hiện sau này như **biến ngân sách riêng**, giữ nguyên retrieval và thuật toán chọn, để đo tác động độc lập.

**Đề xuất giữ C0** cho bước xây LLM Agent: C0 có CER và điểm thủ công cao hơn C1 trong run dev này. Cần đối chiếu thêm các gold chưa xem trực quan PDF, thiết kế một C1 mới có điều kiện truy vấn cụ thể hơn và lưu thành run khác nếu tiếp tục cải thiện trên dev. Không dùng tập test để chỉnh; test vẫn chưa chạy. Quyền chia sẻ PDF/trích đoạn chưa được xác minh.

## A2 retrieval variants R0, R1, and R2

## A2 — Cải thiện retrieval (dev only)

### Phạm vi và tính toàn vẹn

Thí nghiệm chạy offline trên 332 chunks V2 với 17 câu dev (15 câu có đáp án, 2 câu thiếu bằng chứng). R0 lấy Top-3 từ trace TF-IDF gốc đã khóa; R1 và R2 chạy TF-IDF trên cùng corpus V2. Cả ba được đóng gói bằng C0, tối đa 800 ký tự Unicode, để đo bằng chứng trong cùng một context budget.

Không mở benchmark test; không gọi OpenRouter/LLM; không truy vấn hoặc ghi PostgreSQL; không tạo embedding; không sửa corpus hay benchmark. Truy hồi chỉ nhận câu hỏi, không nhận gold, đáp án, ID/trang gold hoặc filter. Gold chỉ được dùng sau truy hồi để chấm. Mỗi hit giữ nguyên ID, source, page và metadata, bao gồm `extraction_quality: needs_review`.

### Cấu hình

- **R0:** TF-IDF baseline Top-3 đã lưu. Dùng retrieval latency trong trace baseline; C0 được đóng gói lại thống nhất.
- **R1:** TF-IDF Top-3 trên câu hỏi được mở rộng bằng từ vựng tiếng Việt/Anh tổng quát cho các khái niệm Discrete Math. Mở rộng chỉ được kích hoạt khi cụm thuật ngữ hiện diện trong câu hỏi; không có luật theo câu benchmark hoặc vị trí gold.
- **R2:** hợp nhất candidate Top-30 từ TF-IDF truy vấn gốc và truy vấn mở rộng, sau đó rerank bằng Reciprocal Rank Fusion với `k=60`, lấy Top-3. Đây là candidate expansion lexical, không kết hợp Dense trong lần chạy này.

### So sánh dev

| Variant | Hit@1 / 15 | Evidence Hit@3 / 15 | Context Evidence Rate / 15 | Median retrieval (ms) | Mean retrieval (ms) | Mean context chars | Ghi chú |
|---|---:|---:|---:|---:|---:|---:|---|
| R0 | 12 (80.0%) | 13 (86.7%) | 13 (86.7%) | 2.307 | 2.497 | 701 | Baseline |
| R1 | 11 (73.3%) | 13 (86.7%) | 12 (80.0%) | 1.329 | 1.408 | 723.7 | Không thêm evidence trong Top-3; mất một evidence ở context C0 |
| R2 | 12 (80.0%) | 13 (86.7%) | 13 (86.7%) | 2.542 | 2.765 | 706.2 | Bằng R0 ở ba metric evidence; đưa d14 về Top-1 |

> **Diễn giải latency:** R0 được lấy từ phép đo trong trace gốc; R1/R2 đo cục bộ trong lần chạy này, không gồm khởi tạo TF-IDF index. Đây là latency retrieval, không gồm khởi động ứng dụng. Chênh lệch vài phần ms trong benchmark nhỏ này không đủ để kết luận R1/R2 nhanh hơn R0. Packing C0 trung bình khoảng 0.02 ms mỗi câu; chi phí API là $0.

Không có câu nào trả về rỗng. Mỗi cấu hình có 2/2 câu thiếu bằng chứng với kết quả truy hồi không rỗng; điều đó không đồng nghĩa có chứng cứ trả lời. Top-3 có lần lượt 23/22/23 hit mang cờ `needs_review` (R0/R1/R2); context answerable chọn 9/9/8 chunks `needs_review` trong 30 chunk được đóng gói. Các cờ được giữ nguyên để downstream agent thận trọng.

### Audit context và lỗi

Context Evidence Rate là kiểm tra xem chunk chứa nguyên văn evidence gold có được đưa vào context C0 hay không. Đây là metric định vị evidence, không phải đánh giá câu trả lời sinh bởi LLM và không thay thế đánh giá grounding của Agent. Audit chất lượng context theo ba nhóm: **evidence rõ trong text và chunk `ok`** (R0/R1/R2: 12/11/12 câu), **evidence có trong text nhưng chunk mang `needs_review`** (1/1/1), **không có evidence trong context** (2/3/2). Cờ review không bị bỏ qua; nội dung `needs_review` cần kiểm tra phần text có đọc được hay phụ thuộc hình/công thức.

- **d01 — định nghĩa mệnh đề:** R0/R1/R2 đều không lấy chunk trang 4 chứa câu định nghĩa vào Top-3. Chúng lấy nội dung logic khác (R0: trang 6/13; R1: trang 17/5; R2: trang 13/6). Đây là retrieval failure, không phải lỗi đóng gói.
- **d03 — hàng bảng chân trị:** cả ba đều không lấy evidence trang 16 vào Top-3. Top-3 bị hút vào ví dụ biến đổi biểu thức và luật logic ở trang 23/21/32; các chunk có `needs_review`, bảng cần thiết không có trong context. Không thể suy ra giá trị hàng bị thiếu.
- **d12 — định lý Euler:** cả ba có evidence trong Top-3. R1 xếp chunk đúng evidence thấp hơn và C0 không đưa nó vào context, nên Context Evidence Rate giảm một câu. R0/R2 giữ evidence trong context.
- **d14 — duyệt cây nhị phân:** R0 xếp chunk liệt kê ba kiểu duyệt ở Top-1; R1 đưa tiêu đề chương lên trước và đẩy evidence xuống Top-2; R2 khôi phục chunk evidence lên Top-1. Đây là cải thiện thứ hạng của R2 cho câu này, nhưng không tăng Hit@1 tổng thể so với R0.
- **d16 — thiếu dữ kiện giá áo:** cả ba trả về ví dụ đếm áo ở trang 29 cùng chunk không liên quan. Nội dung nói số lượng áo và phép cộng, không có đơn giá được hỏi. Không có evidence giá; agent phải abstain.
- **d17 — thiếu thời gian chạy Dijkstra:** cả ba có chunk nói Dijkstra tìm đường đi ngắn nhất ở trang 43, không cung cấp thời gian thực thi. Không được biến phát biểu về tính đúng đắn thuật toán thành thời gian chạy; agent phải abstain.

Trong 13/15 context có chứa gold của R0/R2 (12/15 R1), citation provenance trong trace truy được trực tiếp bằng chunk ID, source và page canonical của V2. Trường hợp evidence thiếu trong context được ghi là thiếu, không gán citation.

### Kết luận và đề xuất

R1 không phù hợp để thay R0: không tăng Evidence Hit@3, giảm Hit@1 một câu và giảm Context Evidence Rate một câu. R2 đạt ngang R0 ở Hit@1, Evidence Hit@3 và Context Evidence Rate; nó sửa thứ hạng d14 nhưng chưa cải thiện tổng thể. Vì vậy **giữ R0/TF-IDF làm cấu hình đề xuất cho Agent**, chưa chuyển A2 sang API thật. R2 có thể được giữ làm ứng viên so sánh, nhưng chưa có lợi ích dev tổng thể đủ để chấp nhận độ phức tạp thêm. Cả d01 và d03 cần một thí nghiệm retrieval khác; không có căn cứ để coi vấn đề đã được giải quyết.

### Tệp kết quả

Run chính: `starter/results/discrete_math_v2/retrieval-a2-dev-20261116T072332985851Z/`

- `metrics.json`: số liệu tổng hợp.
- `traces.json`: 51 trace (17 câu × R0/R1/R2), gồm Top-3, điểm/rank, context C0, thời gian và cờ evidence sau retrieval.
- `run_manifest.json`: hash corpus/benchmark, cấu hình và xác nhận test/API/database/embedding không được dùng.

Các run `retrieval-a2-dev-20261116T071940771208Z` và `retrieval-a2-dev-20261116T072055123775Z` là lần chạy sơ bộ. Run đầu đo nhầm R0 latency bằng lookup trace; run thứ hai có metrics tương tự nhưng được thay bằng run chính sau khi bổ sung kiểm tra hash manifest và đúng kích thước split. Không dùng hai run sơ bộ để báo cáo; dữ liệu được giữ nguyên.

## A1 agent dev evaluation and improvement analysis

## Lab 07 — LLM Agent trên dev

### Trạng thái

Đã implement agent gọi API Chat Completions thật, dùng tool calling để quyết định gọi `search_discrete_math`. Tool dùng TF-IDF Top-3 trên 332 chunk V2 và C0 với 800 ký tự Unicode. Query giữ nguyên câu hỏi gốc; không dùng nhãn benchmark hoặc gold trong agent. Lần gọi model thứ hai chỉ nhận context đã chọn. Đây là tool calling thật khi có API, không phải pipeline RAG cố định. Model có thể không gọi tool; trace ghi quyết định đó và agent từ chối trả lời.

`.env` có khóa OpenRouter (không in ra), model `z-ai/glm-5.3-flash:floor` và URL `https://openrouter.ai/api/v1`; runner tự nạp file này. Sau khi người dùng cập nhật quyền chia sẻ, đã chạy toàn bộ **17 câu dev** qua API thật trong run mới; xem [manifest](../../starter/results/discrete_math_v2/agent-dev-20261116T054605035184Z/manifest.json), [traces](../../starter/results/discrete_math_v2/agent-dev-20261116T054605035184Z/traces.json), [metrics tự động](../../starter/results/discrete_math_v2/agent-dev-20261116T054605035184Z/metrics_auto.json), [metrics đã audit](../../starter/results/discrete_math_v2/agent-dev-20261116T054605035184Z/metrics_reviewed.json) và [audit 17 câu](agent_audit_dev_20261116.json). Run d04 trước đó được giữ nguyên. Không đọc/chạy test benchmark.

Run 17 câu dùng cùng model/configuration, cap $0.042/M input và $0.184/M output. Mỗi câu tạo tối đa hai LLM calls; tổng 34 calls. Tất cả 34 responses có token, provider và `usage.cost`; tổng API cost **$0.0011231227**, 17,005 tokens, trong giới hạn $0.10/30,000 tokens. Provider là Relace cho controller và Wafer cho JSON answer ở cả run. Lượt controller và answer được ghi riêng trong từng trace. Smoke d04 độc lập có chi phí xác nhận $0.0000621938; nó không thuộc tổng 17 câu.

### Kiểm tra và thước đo

Mỗi trace có query, quyết định controller, tool call và tham số, Top-3 hits, context C0, phản hồi LLM, citation, abstention, latency, usage token và cost estimate nếu có giá hợp lệ. Bộ kiểm tra citation yêu cầu ID nằm trong context, source/page đúng, và từng câu trả lời có citation inline. Đây là tính hợp lệ **cấu trúc**; người chấm vẫn phải xác nhận từng khẳng định có được text tương ứng hỗ trợ. Trace `needs_review` ghi rủi ro text so với hình/bảng/công thức chưa xác minh.

Run 17 câu cho grounded answer **9/15 (60%)**. Citation structure hợp lệ ở 9/9 câu được trả lời (coverage 9/15 câu answerable); 10/10 citation references trong các câu trả lời được audit semantic support và source/page. Hai câu thiếu evidence abstain đúng 2/2. False refusal là 6/15 (40%); toàn bộ 17 câu đã gọi tool đúng một lần.

### Hai rủi ro đã thấy trên dev trước khi chạy agent

- d03: context C0 không chứa hàng bảng chân trị cần thiết; một chunk liên quan có cờ công thức chưa ánh xạ. Agent phải từ chối thay vì tự tính hoặc tự dựng bảng. Đây là lỗi retrieval/context đã kiểm chứng, chưa phải lỗi LLM.
- d01: context C0 không có evidence định nghĩa mệnh đề cần thiết. Prompt chặt có thể gây từ chối đúng về mặt grounding nhưng tăng false refusal trên câu benchmark có đáp án. Đây là giới hạn retrieval đã kiểm chứng, chưa phải lỗi LLM.
- d11: phương án C1 từng bỏ sót điều kiện hai chiều; C0 giữ evidence tốt hơn nên được khóa cho agent. Không thay đổi policy theo test.

### Đối chiếu rubric

| Tiêu chí Day07 | Trạng thái |
|---|---|
| Corpus/benchmark dev 332 chunk, 15 có đáp án + 2 thiếu evidence | Đã kiểm chứng ở bước retrieval/context |
| Ba retrieval method | Đã có trong `retrieval_v2.py`; agent chọn TF-IDF |
| Agent model thật, tool trace, điều kiện dừng | Đã chạy API thật trên 17 câu; 34 calls, tool use 17/17 |
| Context C0, citation, thiếu evidence | C0 dùng trên 17 câu; citation structure và semantic support được audit thủ công |
| Grounded answer, citation support, abstention trên dev | Grounded 9/15; support 10/10 references; abstention 2/2; false refusal 6/15 |
| Cải thiện ít nhất hai cấu hình agent | Chưa làm; không chỉnh prompt trước baseline API |
| Test benchmark sau khi chốt dev | Chưa chạy, theo yêu cầu |
| Chi phí/latency API | 17 câu: $0.0011231227; mean 4059 ms, median 3744 ms |

### Giới hạn và bước cần người dùng

Chưa chạy test theo yêu cầu. Các lỗi chính cần xử lý ở một run mới: d01 TF-IDF bỏ lỡ p4; d03 không retrieve truth table p16; d04/d06/d13/d14 model trả lời có citation object nhưng thiếu inline `[chunk_id]`, nên citation validator gây false refusal. Không đổi prompt/policy giữa run này. Không đưa key vào repo.

### Kết quả đánh giá dev mới nhất

| Chỉ số | Kết quả |
|---|---:|
| Grounded Answer Rate (15 answerable) | 9/15 = 60.0% |
| Citation structure validity (câu answered) | 9/9 = 100%; coverage answerable 9/15 = 60.0% |
| Semantic citation support | 10/10 references = 100.0% |
| Abstention accuracy (d16, d17) | 2/2 = 100.0% |
| False refusal (answerable) | 6/15 = 40.0% |
| Tool-use correctness | 17/17 = 100.0% |
| Latency mean / median | 4059 / 3744 ms |
| Tokens input / output / total | 12,882 / 4,123 / 17,005 |
| Chi phí thực tế theo `usage.cost` | $0.0011231227 |

#### Lỗi thực tế

- **d01:** TF-IDF trả p6/p13, gold định nghĩa nằm p4. Context không hỗ trợ định nghĩa; model nêu giới hạn nhưng có câu thiếu citation inline nên wrapper chuyển thành abstention. Về benchmark là false refusal; về grounding, abstain an toàn hơn bịa câu trả lời. Nguyên nhân chính: retrieval miss, sau đó validator xử lý uncited raw answer.
- **d03:** Top-3 p23/p21/p32 không có bảng chân trị p16. Model suy ra E=0 từ luật kéo theo ở p21 nhưng không gắn citation inline cho toàn bộ phép biến đổi; validator abstain. Đây là failure retrieval/context và citation formatting; policy không cho khôi phục bảng thiếu từ ngoài context.
- **d04, d06, d13, d14:** context chứa đáp án nguyên văn; raw model response có citation object với đúng chunk nhưng không chèn `[chunk_id]` trong câu. Citation validator từ chối toàn bộ response, dẫn tới bốn false refusals có thể khắc phục ở một run/config mới. Run d04 đơn lẻ trước đó trả lời đúng; run 17 câu hiện tại được giữ độc lập.

d16/d17 được model từ chối đúng; d17 có nhắc định lý Dijkstra với citation object nhưng không có inline ID, tuy nhiên không đưa số milliseconds nên abstention vẫn đúng. Metrics tự động là từ trace; grounded answer và citation semantic support là đánh giá thủ công theo audit file. Không chạy test hoặc thay benchmark/corpus.

### A1 — prompt citation rõ hơn và một lần sửa

A1 là run riêng, không thay baseline. Model/retriever/context/corpus giữ nguyên; chỉ hướng dẫn câu trả lời và chính sách repair thay đổi. Mỗi câu có một controller call, một final call và tối đa một repair call. Repair nhận nguyên context, không gọi retrieval lại; chỉ chấp nhận nếu JSON, citation inline, ID, source và page hợp lệ. Không tạo citation chỉ vì chunk xuất hiện trong context.

| Chỉ số | Baseline | A1 | Thay đổi |
|---|---:|---:|---:|
| Grounded Answer Rate (15) | 9/15 (60%) | 12/15 (80%) | +3 câu, +20 điểm % |
| False refusal (15) | 6/15 (40%) | 3/15 (20%) | giảm 3, −20 điểm % |
| Câu answered có citation structure hợp lệ | 9/9 | 12/12 | giữ 100%, coverage tăng 60% → 80% |
| Semantic citation support | 10/10 refs | 13/13 refs | mọi citation được audit đều được hỗ trợ |
| Abstention đúng d16/d17 | 2/2 | 2/2 | không đổi |
| Tool use | 17/17 | 17/17 | không đổi |
| Repair | — | 1 lần, thất bại | d14 vẫn abstain |
| Mean / median latency | 4059 / 3744 ms | 3627 / 3319 ms | A1 thấp hơn trong run này |
| Tokens | 17,005 | 20,772 | +3,767 |
| Chi phí API | $0.0011231227 | $0.0013042941 | +$0.0001811714 |

Grounded Answer Rate A1 = 12/15 dựa trên audit thủ công 17 câu, không suy từ citation validity. Citation structure 12/12 và semantic support 13/13 cũng là các phép đo riêng. Mọi retrieval giữ đúng TF-IDF Top-3 và C0; traces, manifest và metrics có trong `starter/results/discrete_math_v2/agent-a1-dev-20261116T055814596229Z/`.

#### Lỗi A1 và phân loại root cause

- d01 và d03 vẫn abstain vì gold chunk không nằm trong Top-3/context. Đây là **retrieval_failure** theo audit hậu nghiệm; agent trace ghi `model_abstention`, vì retrieval returned unrelated but nonempty chunks.
- d14 vẫn false refusal. p11 có đủ ba traversal methods. Raw answer có hai câu, citation chỉ ở câu thứ hai; một repair lặp lại cùng lỗi, nên wrapper abstain với `repair_failure`. Cần A2/agent variant phân câu và gắn citation cho từng câu, hoặc rút gọn thành một câu có citation.
- d04, d06, d13 được trả lời đúng với citation inline và source/page hợp lệ mà không cần repair. Đây là giảm false refusal thực tế, không phải chỉ sửa nhãn.

#### Đề xuất A2: retrieval cho d01/d03

Chưa triển khai A2. Thí nghiệm kế tiếp nên giữ nguyên 332 chunks, model và C0, tạo một retrieval run riêng so sánh TF-IDF Top-3 baseline với query expansion/symbol-aware lexical retrieval: chuẩn hóa cách hỏi định nghĩa mệnh đề cho d01 và giữ ký hiệu `E(p,q,r)`, toán tử, hàng giá trị cùng cụm “bảng chân trị” cho d03. Chỉ query gốc/biến thể được gửi retrieval, tuyệt đối không dùng gold chunk để filter. Đo recall/context hit và latency dev trước khi dùng API; nếu context vẫn thiếu bảng d03 thì agent phải abstain. Không chạy test.
