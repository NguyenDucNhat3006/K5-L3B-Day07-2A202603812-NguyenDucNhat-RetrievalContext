# Lab 07 — LLM Agent trên dev

## Trạng thái

Đã implement agent gọi API Chat Completions thật, dùng tool calling để quyết định gọi `search_discrete_math`. Tool dùng TF-IDF Top-3 trên 332 chunk V2 và C0 với 800 ký tự Unicode. Query giữ nguyên câu hỏi gốc; không dùng nhãn benchmark hoặc gold trong agent. Lần gọi model thứ hai chỉ nhận context đã chọn. Đây là tool calling thật khi có API, không phải pipeline RAG cố định. Model có thể không gọi tool; trace ghi quyết định đó và agent từ chối trả lời.

Môi trường hiện không có `OPENAI_API_KEY`, `LAB07_LLM_MODEL` hoặc giá/budget hợp lệ. Chưa gọi API thật và **chưa có điểm agent dev**. Kết quả mock chỉ kiểm chứng hành vi code, không phải grounded-answer score. Chưa chạy benchmark test 7 câu.

## Kiểm tra và thước đo

Mỗi trace có query, quyết định controller, tool call và tham số, Top-3 hits, context C0, phản hồi LLM, citation, abstention, latency, usage token và cost estimate nếu có giá hợp lệ. Bộ kiểm tra citation yêu cầu ID nằm trong context, source/page đúng, và từng câu trả lời có citation inline. Đây là tính hợp lệ **cấu trúc**; người chấm vẫn phải xác nhận từng khẳng định có được text tương ứng hỗ trợ. Trace `needs_review` ghi rủi ro text so với hình/bảng/công thức chưa xác minh.

Sau khi có API và quyền gửi corpus, chạy 17 câu dev. `metrics_auto.json` cho tool use, citation structure, abstention, false refusal, latency, usage và cost. `reviews_template.json` dành cho audit thủ công theo rubric 0/1/2; tổng hợp bằng `agent_metrics.py`. Trường grounded answer giữ `requires_manual_review` trước khi audit. Với d16 và d17, kiểm tra model tìm kiếm rồi từ chối vì không có giá áo hoặc phép đo thời gian chạy; unit test mock đã kiểm tra nhánh abstention, **chưa xác nhận hành vi model thật**.

## Hai rủi ro đã thấy trên dev trước khi chạy agent

- d03: context C0 không chứa hàng bảng chân trị cần thiết; một chunk liên quan có cờ công thức chưa ánh xạ. Agent phải từ chối thay vì tự tính hoặc tự dựng bảng. Đây là lỗi retrieval/context đã kiểm chứng, chưa phải lỗi LLM.
- d01: context C0 không có evidence định nghĩa mệnh đề cần thiết. Prompt chặt có thể gây từ chối đúng về mặt grounding nhưng tăng false refusal trên câu benchmark có đáp án. Đây là giới hạn retrieval đã kiểm chứng, chưa phải lỗi LLM.
- d11: phương án C1 từng bỏ sót điều kiện hai chiều; C0 giữ evidence tốt hơn nên được khóa cho agent. Không thay đổi policy theo test.

## Đối chiếu rubric

| Tiêu chí Day07 | Trạng thái |
|---|---|
| Corpus/benchmark dev 332 chunk, 15 có đáp án + 2 thiếu evidence | Đã kiểm chứng ở bước retrieval/context |
| Ba retrieval method | Đã có trong `retrieval_v2.py`; agent chọn TF-IDF |
| Agent model thật, tool trace, điều kiện dừng | Implement; chưa kiểm chứng API thật |
| Context C0, citation, thiếu evidence | Implement; mock tests qua |
| Grounded answer, citation support, abstention trên dev | Chờ API thật và audit thủ công |
| Cải thiện ít nhất hai cấu hình agent | Chưa làm; không chỉnh prompt trước baseline API |
| Test benchmark sau khi chốt dev | Chưa chạy, theo yêu cầu |
| Chi phí/latency API | Instrumented; chưa đo |

## Giới hạn và bước cần người dùng

Xác minh quyền gửi đoạn text PDF tới API ngoài; cung cấp key, model, giá input/output hợp lệ và ngân sách chạy. Không đưa key vào repo. Sau đó chạy dev, audit 17 câu, phân tích ít nhất hai **lỗi agent thực tế** và lưu mọi bản điều chỉnh thành run mới. Không suy điểm grounded answer từ Context Evidence Rate.
