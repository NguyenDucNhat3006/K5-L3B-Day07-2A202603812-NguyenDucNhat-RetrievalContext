# A0 Retrospective Baseline Evaluation - test

## Kết luận và giới hạn

Đã chạy đúng một lượt A0 trên 7 câu test đã mở trước đó. Đây là **retrospective paired comparison**, không phải đánh giá độc lập. Không sửa test/corpus, không gọi database, không embedding lại và không chạy lại A1. Run directory: `starter/results/discrete_math_v2/agent-a0-retro-test-20261116T151349722949Z/` (local, Git-ignored).

A0 đạt Grounded Answer Rate **0/5** (grade 0: 5, grade 1: 0, grade 2: 0). Cả năm câu có đáp án đều kết thúc bằng abstention vì output draft không qua kiểm tra citation inline của agent. Hai câu thiếu bằng chứng abstain đúng **2/2**. Cả 7 câu đều gọi retrieval tool. Đây là thất bại ở tầng phản hồi/citation; retrieval và context của cả năm câu answerable đều chứa gold evidence.

## Cấu hình đã khóa và provenance

- Agent: A0 `run_v2_agent()` với `agent_v2.SYSTEM` và `agent_v2.TOOL`; không dùng A1 repair.
- Model request: `z-ai/glm-5.3-flash:floor` qua OpenRouter; response model `z-ai/glm-5.3-flash`.
- Retriever: TF-IDF Top-3; context: C0 tối đa 800 ký tự Unicode.
- Corpus: Discrete Math V2, 332 chunks.
- Test hash: `3f267ab60758d16351c4e26167e3adb730df8afab5dd983e9db5eb1fa50fc384`.
- Corpus hash: `979a0baaf2f34735592bde1aeaf2bdb29b5a8f336f3f0bcb3fee699056f57990`.
- A0 system prompt hash: `15581527595b44a879acf2a65104a879e6ade6c2ab032b19cd966b0e19a16300`; tool schema hash: `4cf064351a62da7b1bb51af8d7463811d48d97460f016b43b6e081ee362e880f`.
- Prompt và tool schema đã được đối chiếu với nội dung trong hai commit lịch sử ghi trong manifest. A0 dev manifest không ghi source hashes; vì thế không thể chứng minh client/runner hoặc toàn bộ working tree ở lần A0 dev trùng byte với retrospective runner. Run này dùng một runner test-only mới và API adapter OpenRouter hiện có. Đây là sai khác provenance cần giữ rõ khi diễn giải.
- Người nộp đã xác nhận quyền dùng corpus cho Lab/nộp giảng viên và quyền gửi nội dung cho đánh giá API. Quyền này không phải quyền công khai PDF hoặc mọi trích đoạn.

## Metrics

| Chỉ số | A0 retrospective test | Diễn giải |
|---|---:|---|
| Hit@1 | 5/5 (100%) | Chỉ 5 câu answerable; exact chunk/source/page và evidence quote |
| Evidence Hit@3 | 5/5 (100%) | Gold evidence có trong Top-3 |
| Context Evidence Rate | 5/5 (100%) | Gold quote còn trong context C0 |
| Context audit mức 0 / 1 / 2 | 0 / 0 / 5 | Các context answerable đủ evidence; `needs_review` được giữ nguyên |
| Grounded Answer Rate | **0/5 (0%)** | Abstain trên cả năm câu answerable được chấm grade 0 |
| Answer grade 0 / 1 / 2 | 5 / 0 / 0 | Manual audit câu trả lời cuối của agent |
| Citation structure, câu trả lời cuối | 0/0 (N/A) | Không có citation cuối vì agent abstain cả 7 câu |
| Semantic citation support, câu trả lời cuối | 0/0 (N/A) | Không có citation cuối để đánh giá |
| Citation metadata trong draft | 9/9 references khớp chunk/source/page/context | Metadata đúng không đồng nghĩa draft đạt format |
| Semantic support các citation draft | 9/9 citation references support mệnh đề factual chính | Chỉ là diagnostic của draft bị loại; không tính như câu trả lời cuối. t05 có thêm nhận xét về proof không được cite riêng |
| Draft đáp ứng đầy đủ inline citation validator | 0/5 draft answerable | t01/t04 sai inline-ID set; t02/t03/t05 còn câu không citation |
| Abstention chính xác | 2/2 | t06, t07 |
| False refusal | 5/5 (100%) | t01-t05 có evidence nhưng agent từ chối sau validation |
| Tool-use correctness | 7/7 (100%) | Một tool call cho mỗi câu |
| LLM/API calls | 14 | 2/câu; không retry |
| Input / output / tổng tokens | 5,202 / 1,847 / 7,049 | OpenRouter usage |
| Latency mean / median | 3,720 / 3,577 ms | End-to-end mỗi câu |
| Actual API cost | **$0.0004882121** | OpenRouter-reported usage cost |

Actual provider mix: Relace 7 calls, Wafer 7 calls. Run nằm trong cap 14 calls, 20.000 tokens, $0.10; OpenRouter key preflight còn đủ hạn mức cho cap. Không lưu key hoặc số dư tài khoản vào manifest.

## Audit theo câu

| Case | Context | Result / failure | PDF evidence review | Calls | Latency (ms) | Tokens | Actual cost (USD) |
|---|---:|---|---|---:|---:|---:|---:|
| t01 | 2 | Draft correct; `inline_citation_mismatch`; final abstain, grade 0 | p.27 directly states the Modus Tollens example/conclusion; citation metadata matches, but inline chunk tag is absent | 2 | 3,403.2 | 896 | 0.0000531297 |
| t02 | 2 | Draft gives lower bound 3; `uncited_sentence`; final abstain, grade 0 | pp.36 and 33 state the 20/7 example and principle. Readable text supports the answer despite `needs_review`; no visual content reconstructed | 2 | 4,223.9 | 1,080 | 0.0000817410 |
| t03 | 2 | Draft gives 111/000; `uncited_sentence`; final abstain, grade 0 | p.45 explicitly states the extrema; earlier draft sentences lack inline citations | 2 | 2,658.9 | 930 | 0.0000558035 |
| t04 | 2 | Draft explains Theorem 1.8/connectedness; `inline_citation_mismatch`; final abstain, grade 0 | p.39 states the theorem and p.37 defines connectedness; metadata matches but inline chunk tags are absent | 2 | 3,209.1 | 1,086 | 0.0000865319 |
| t05 | 2 | Draft states the Hamilton-path theorem; `uncited_sentence`; final abstain, grade 0 | p.30 states the theorem. The extra proof-status statement is unnecessary and not separately cited | 2 | 4,678.7 | 968 | 0.0000596787 |
| t06 | N/A | Model and final agent abstain correctly | Evidence gives a lower bound but not the box number | 2 | 3,577.1 | 1,019 | 0.0000730342 |
| t07 | N/A | Model and final agent abstain correctly | The theorem asserts existence but gives no vertex order | 2 | 4,289.4 | 1,070 | 0.0000782931 |

PDF đối chiếu là các file local trong `data/discrete_math/raw/`; đường dẫn tương đối và SHA-256 của nguồn kiểm tra được lưu trong `audit_manual.json`. Các trang liên quan được trích text để xác minh mệnh đề; kết quả không dựa vào việc tái tạo nội dung hình. Trace, metrics, audit và manifest đầy đủ chỉ ở local run directory.

## So sánh cùng test với A1 đã khóa

| Chỉ số | A0 retrospective | A1 official final test |
|---|---:|---:|
| GAR trên câu answerable | 0/5 (0%) | **3/5 (60%)** |
| Grade 0 / 1 / 2 | 5 / 0 / 0 | 2 / 0 / 3 |
| Hit@1 / Evidence Hit@3 / Context Evidence Rate | 5/5 / 5/5 / 5/5 | 5/5 / 5/5 / 5/5 (chấm lại từ trace đã lưu) |
| Context audit 0 / 1 / 2 | 0 / 0 / 5 | 0 / 0 / 5 |
| Citation structure cuối | 0/0 (N/A) | 3/3 câu trả lời |
| Semantic citation support cuối | 0/0 (N/A) | 3/3 references được audit hỗ trợ |
| Abstention / false refusal | 2/2 / 5/5 | 2/2 / 2/5 |
| Tool use | 7/7 | 7/7 |
| Calls / tokens | 14 / 7,049 | 16 / 10,363 |
| Latency mean / median | 3.720 / 3.577 s | 4.952 / 4.502 s |
| API cost thực tế | $0.0004882121 | $0.0006918935 |

Hai cấu hình dùng cùng request model alias, R0/C0 và cho cùng retrieval/context evidence trên 7 câu. Kết quả mô tả cho thấy A1 phát hành được 3 câu có đáp án và false refusal ít hơn 3 câu. Không kết luận đây là hiệu quả nhân quả thuần của A1: provider routing khác số lượng call và A0 API client snapshot lịch sử không chứng minh được chính xác. Chênh lệch latency/chi phí cũng không phải so sánh hiệu năng có kiểm soát.

## Tái lập và trạng thái

Manifest ghi hashes trước call cho benchmark, corpus, code, prompt/tool và giá/cap; đồng thời ghi output hashes sau audit. One-shot sentinel tại `starter/results/discrete_math_v2/.a0-retro-test-one-shot.lock` chặn vô tình chạy lượt thứ hai. Không chạy lại A0 hay A1. Run artifacts đang bị `.gitignore` loại trừ; không commit/push raw trace.

Kết quả chính thức A1 không đổi: dev GAR 12/15 và final test GAR **3/5**, abstention 2/2, tool use 7/7, cost $0.0006918935. A0 test chỉ bổ sung baseline retrospective, không biến test set đã mở thành một đánh giá độc lập.
