# Context Engineering trên TF-IDF Top-3 — dev

## Phạm vi và cách làm

Thí nghiệm này dùng nguyên [Top-3 TF-IDF đã lưu](../../starter/results/discrete_math_v2/dev-20261116T043019037173Z/traces.json) cho **17 câu dev**; SHA-256 của trace nguồn là `33d0d4c73598230273cf9b27533b9bfea7d888f2747dceb8c377f41ec0f16022`. Không chạy lại retrieval, không mở benchmark test, không embed corpus, không truy cập database và không sửa kết quả cũ. Cả hai cấu hình có cùng ba candidate theo thứ hạng gốc và cùng ngân sách **800 ký tự Unicode**.

- **C0:** Duyệt Top-3 theo thứ hạng TF-IDF; thêm cả chunk nếu vừa ngân sách, bỏ qua chunk không vừa. Đây là baseline packing với header citation bổ sung `extraction_quality`; nó không ghi đè trace baseline cũ.
- **C1:** Xét các tập con của cùng Top-3, chỉ chọn **chunk đầy đủ** vừa ngân sách. Điểm chọn dựa trên rank, `content_type`, tín hiệu loại câu hỏi (định nghĩa/định lý/bảng/ví dụ), cờ chất lượng và `semantic_unit_split`. C1 không dùng gold, đáp án chuẩn hoặc trang gold. Chunk có cờ hình/ma trận/công thức được giảm ưu tiên, nhưng `needs_review` do bố cục bảng không bị coi mặc định là vô dụng.
- Mỗi block context chứa `chunk_id`, đường dẫn `source`, `page`, `extraction_quality` và **toàn bộ text**. Metadata và các `quality_reasons` đầy đủ nằm trong trace retrieval gốc. Bộ kiểm tra đối chiếu từng block với JSON V2 và xác nhận số trang nằm trong PDF nguồn; việc xem trực quan PDF mới thực hiện cho d04.

Gold chỉ được dùng **sau khi pack** để tính Context Evidence Rate. Chỉ số tự động đòi đúng ID, nguồn/trang và chuỗi evidence trong một chunk đã chọn; nó không xác nhận đáp án được hỗ trợ đầy đủ. Tôi đã đọc context của cả 15 câu có đáp án và 2 câu thiếu evidence cho **mỗi** cấu hình, rồi ghi nhãn/lý do tại [audit 34 context](context_engineering_dev_audit.json). Rubric thủ công: **0** không có evidence; **1** có evidence liên quan nhưng thiếu điều kiện/nguồn; **2** đủ evidence và citation. Hai câu thiếu evidence được chấm riêng về việc context có buộc phải từ chối hay không, chưa phải điểm abstention của agent.

## Kết quả thực đo

| Cấu hình | Context Evidence Rate | Thủ công: mức 0 / 1 / 2 | Trung bình /2 | Context hỗ trợ từ chối | Ký tự TB / tối đa | MiniLM tokens TB / tối đa | Median packing |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 | **13/15 (86,7%)** | **2 / 0 / 13** | **1,733/2** | **2/2** | **701 / 797** | **254,5 / 367** | **0,0186 ms** |
| C1 | **12/15 (80,0%)** | **2 / 1 / 12** | **1,667/2** | **2/2** | **700,2 / 792** | **256,3 / 367** | **0,0632 ms** |

Ngân sách của cả hai là **800 ký tự**, tính cả citation header; trung bình mỗi context chứa **2 chunk**. Cột token đếm bằng tokenizer MiniLM như một số đo tham khảo; **chưa đặt ngân sách token LLM** vì model agent chưa được chọn. Latency trong bảng chỉ đo đóng gói context từ Top-3 đã lưu. Retrieval TF-IDF có median **2,3 ms** trong run gốc và giống nhau cho hai cấu hình; không cộng các median với nhau thành một phép đo end-to-end. Thời gian packing rất nhỏ và chỉ đo một lượt trên máy hiện tại, nên chênh lệch không đủ để suy luận về hiệu năng khi tải lớn. Phí API trực tiếp **0 USD**; chi phí máy/điện chưa đo.

Xem [metrics tự động](../../starter/results/discrete_math_v2/context-dev-20261116T044835296260Z/metrics_auto.json), [metrics có audit thủ công](../../starter/results/discrete_math_v2/context-dev-20261116T044835296260Z/metrics_reviewed.json), [context traces](../../starter/results/discrete_math_v2/context-dev-20261116T044835296260Z/traces.json) và [run manifest](../../starter/results/discrete_math_v2/context-dev-20261116T044835296260Z/run_manifest.json). Run mới nằm trong `starter/results/`, được Git bỏ qua; file cũ không bị ghi đè.

## Audit từng câu dev

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

## Phân tích lỗi và quyết định

- **d03 là lỗi retrieval đầu vào:** TF-IDF Top-3 không chứa bảng p16; cả C0/C1 chỉ nhận ba chunk đã trả về nên không thể tạo evidence còn thiếu. Không tái tạo hàng bảng bằng suy luận từ hình/công thức.
- **d05 là ca thành công của baseline TF-IDF:** chunk định nghĩa p23 đứng hạng 1 và được cả hai packer giữ; lỗi Hybrid RRF trước đó không xuất hiện khi dùng TF-IDF Top-3 cố định.
- **d09 cho thấy cờ review cần đọc theo ngữ cảnh:** chunk p3 có cờ hình cần kiểm tra nhưng p24 đã đủ định nghĩa. C1 loại p3, song chất lượng câu trả lời vẫn mức 2 ở cả hai.
- **d11 là hồi quy do C1:** bộ chọn cộng điểm cho `content_type=definition` và tối ưu tập con ngắn, nên chọn p37 thay p42 dù cặp p42+p43 vẫn vừa 800 ký tự. Đây là lỗi tiêu chí chọn, không phải thiếu ngân sách hay thiếu nguồn.

Đã cân nhắc mở rộng ngân sách nhưng **chưa chạy C2**: d01/d03 thiếu chunk gold ngay từ Top-3, còn d11 do utility của C1. Một run 1.200 ký tự chỉ nên thực hiện sau này như **biến ngân sách riêng**, giữ nguyên retrieval và thuật toán chọn, để đo tác động độc lập.

**Đề xuất giữ C0** cho bước xây LLM Agent: C0 có CER và điểm thủ công cao hơn C1 trong run dev này. Cần đối chiếu thêm các gold chưa xem trực quan PDF, thiết kế một C1 mới có điều kiện truy vấn cụ thể hơn và lưu thành run khác nếu tiếp tục cải thiện trên dev. Không dùng tập test để chỉnh; test vẫn chưa chạy. Quyền chia sẻ PDF/trích đoạn chưa được xác minh.
