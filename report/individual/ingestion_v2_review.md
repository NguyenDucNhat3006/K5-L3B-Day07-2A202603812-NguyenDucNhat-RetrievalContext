# Audit ingestion Cấu trúc rời rạc: v1 → v2

Đây là audit tại thời điểm tạo v2, trước khi index. Sau khi người dùng duyệt, v2 đã được index riêng; xem [báo cáo index và smoke retrieval](v2_index_smoke.md). Lệnh tạo v2 không embedding, ghi database, chạy benchmark hay thay dữ liệu chính thức.
SHA-256 của `chunks.json` v1: `7561e3a39e06b919b5872e2e3f9083c6ef2d67c739c5329464d6d7090aba515d`.

## Phạm vi nguồn

- Đã đọc 9 PDF, 389 trang vật lý.
- Trong `data/discrete_math/raw/` chỉ có 9 PDF; không có PPT/PPTX Chương 3. Vì vậy chưa thể xác nhận bộ 10 file gốc hay so sánh bản PDF/PPT Chương 3.
- Quyền chia sẻ PDF và các trích đoạn trong báo cáo chưa được xác minh; cần kiểm tra trước khi công bố hoặc đưa báo cáo lên remote.
- `source_id`, `source` và `page` là ID nguồn, đường dẫn và số trang vật lý của PDF hiện có. Trang chỉ chứa header/số trang có thể không có chunk v2.

## So sánh định lượng

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

### Theo tài liệu

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

## Quy tắc v2 và giới hạn

- Loại số trang, header/footer lặp, bảng rỗng do PDF parser tạo và đoạn chỉ có nhãn hình. Giữ số trang vật lý ở trường `page`.
- Ưu tiên giữ trọn bài tập, định nghĩa, định lý, ví dụ và bảng trong một chunk. Mức 620 ký tự cho text dành chỗ cho citation header trong context budget 800 ký tự của Lab07; đơn vị dài hơn chỉ chia tại ranh giới dòng/câu, có cờ `long_semantic_unit_split`.
- Bảng chân trị chỉ chuyển Markdown khi hàng/cột đầy đủ, không có ô trống, các hàng nhị phân và số hàng là lũy thừa của 2. Bảng lệch cột được giữ dưới dạng text gốc và gắn `needs_review`.
- Ma trận, công thức font tùy biến và hình đồ thị không được suy đoán từ chuỗi nhãn/trọng số. Các chunk liên quan gắn `needs_review` và `quality_reasons`.
- Các trang hình có thể chứa evidence không hiện diện trong text; cần đối chiếu PDF trước khi dùng làm câu trả lời có dẫn nguồn. Lỗi dấu tiếng Việt còn có thể tồn tại sau giải mã VNI.

## Tương thích retrieval

- `chunks_v2.json` giữ đúng 6 trường của schema Day07: `id`, `text`, `source_id`, `source`, `page`, `metadata`. ID có hậu tố `:v2` và duy nhất.
- TF-IDF: tạo chỉ mục trong bộ nhớ cho **332** hàng; truy vấn khói trả **3** hit, pack context được **2** chunk / 559 ký tự. Không dùng benchmark để tính điểm.
- Context budget: **332/332** chunk riêng lẻ vừa 800 ký tự kể cả citation header. Bộ packer vẫn có thể bỏ hit nếu tổng nhiều chunk vượt ngân sách.
- Dense: **332** hàng ánh xạ được sang `src.models.Chunk` Day06. Audit này chỉ kiểm tra schema; truy vấn Dense thật sau khi index được ghi ở [báo cáo index và smoke retrieval](v2_index_smoke.md).
- Hybrid: chưa có triển khai hybrid trong Python của repo để chạy end-to-end. Các hàng có ID/text/metadata chung cho fusion sau này.

## 15 ví dụ trước/sau

### 1. Trang bìa/header: `chuong-1-co-so-logic` trang 1

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

### 2. Số trang đơn lẻ: `chuong-1-co-so-logic` trang 39

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

### 3. Số trang đơn lẻ: `chuong-1-co-so-logic` trang 45

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

### 4. Header lặp: `chuong-3-quan-he` trang 25

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

### 5. Footer ngày và số trang: `chuong-4-dai-so-boole` trang 4

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

### 6. Header lặp: `chuong-5-do-thi-phan-2` trang 33

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

### 7. Bảng chân trị có cấu trúc: `chuong-1-co-so-logic` trang 16

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

### 8. Bảng chân trị lệch cột: `chuong-4-dai-so-boole` trang 19

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

### 9. Bảng ở dạng hình: `chuong-4-dai-so-boole` trang 73

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

### 10. Ma trận dạng hình: `chuong-3-quan-he` trang 8

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

### 11. Hình đồ thị: `bai-tap-chuong-5` trang 1

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

### 12. Bài tập ma trận: `bai-tap-chuong-5` trang 2

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

### 13. Bài tập cây/ma trận: `bai-tap-chuong-6` trang 2

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

### 14. Bài tập nhiều ý: `bai-tap-chuong-5` trang 5

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

### 15. Công thức: `chuong-2-phep-dem` trang 54

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
