# Weekly Journal

Ghi lại hành trình xây dựng sản phẩm mỗi tuần — những gì đã làm, học được gì, AI giúp như thế nào.

> **Cập nhật mỗi cuối tuần** (trước khi tạo PR). Không cần dài, chỉ cần thật.

---

## Template

```markdown
## Tuần N — DD/MM/YYYY

### Đã làm
-

### Khó nhất tuần này
-

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | | |

### Học được
-

### Nếu làm lại, sẽ làm khác
-

### Kế hoạch tuần tới
-
```

---

## Ví dụ

### Tuần 1 — 31/03/2026

**Thành viên:** Nguyễn Văn A, Trần Thị B, Lê Văn C

#### Đã làm
- Setup project TypeScript + cấu hình `.env`
- Xây dựng agent loop cơ bản: nhận input → gọi Claude API → in output
- Thêm tool `search_web` đầu tiên (dùng Brave Search API)
- Viết README cho repo nhóm

#### Khó nhất tuần này
- Tool call response của Claude trả về sai format — mất 2 tiếng debug mới phát hiện ra thiếu `"type": "tool_result"` trong message history.
- Lần đầu dùng TypeScript nên type error khá nhiều, phải học cách dùng `as` và generic.

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Giải thích Anthropic tool use API, debug message format | Giải quyết được bug trong 15 phút |
| Cursor | Autocomplete TypeScript types | Tiết kiệm khoảng 30% thời gian gõ |

#### Học được
- Tool use trong Claude hoạt động theo vòng lặp: model gọi tool → app trả kết quả → model tiếp tục. Cần giữ đúng message history.
- `zod` rất hữu ích để validate tool input schema.
- Nên đặt timeout cho API call ngay từ đầu, không để sau mới thêm.

#### Nếu làm lại, sẽ làm khác
- Setup TypeScript strict mode ngay từ đầu thay vì thêm sau (refactor mệt hơn).
- Viết unit test cho `parseToolCall()` trước khi tích hợp vào agent loop.

#### Kế hoạch tuần tới
- Thêm tool `read_file` và `write_file`
- Implement memory: lưu conversation history vào file JSON
- Thử chạy agent giải 1 bài tập thực tế

---

### Tuần 2 — 07/04/2026

**Thành viên:** Nguyễn Văn A, Trần Thị B, Lê Văn C

#### Đã làm
- Thêm tool `read_file`, `write_file`, `list_dir`
- Agent có thể tự đọc file trong repo và đề xuất refactor
- Implement conversation memory: lưu 20 message gần nhất
- Thử nghiệm: cho agent tự fix 3 bug đơn giản → thành công 2/3

#### Khó nhất tuần này
- Memory bị lỗi khi conversation quá dài (vượt context window). Phải implement sliding window: chỉ giữ system prompt + 20 message gần nhất.
- Agent đôi khi loop vô hạn khi tool trả lỗi — chưa có stop condition tốt.

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Thiết kế sliding window memory, review code agent loop | Phát hiện thêm edge case khi tool throw exception |
| Gemini CLI | So sánh approach lưu memory: file JSON vs SQLite | Tư vấn dùng JSON cho prototype, SQLite khi cần query |

#### Học được
- Context window là resource có hạn — cần thiết kế memory strategy từ sớm.
- Stop condition quan trọng không kém gì agent logic: `max_iterations`, `no_new_tool_calls`, `explicit_done`.
- AI agent review code của mình rất có ích: Claude Code tìm ra 2 potential null pointer mà mình bỏ sót.

#### Nếu làm lại, sẽ làm khác
- Viết interface `Memory` trước, rồi implement sau — thay vì hard-code array từ đầu.
- Log tất cả tool call ra file ngay từ đầu để debug dễ hơn.

#### Kế hoạch tuần tới
- Fix vòng lặp vô hạn: thêm `max_iterations = 10`
- Thêm tool `run_tests` để agent tự kiểm tra code sau khi sửa
- Demo cho instructor cuối tuần

---

### Tuần 3 — 18/04/2026

**Thành viên:** Nguyễn Công Hùng, Hà Huy Hoàng

#### Đã làm
- Xây dựng toàn bộ backend FastAPI: `OCRService` (DeepSeek-OCR), `IndexingService` (ChromaDB + chunking theo trang), `RAGService` (Qwen3-0.6B local + Gemini API)
- Xây dựng frontend React: ChatContainer, MessageBubble, ThinkingIndicator, SourcesPanel, Header, `useChat` hook — hỗ trợ chuyển đổi model Qwen/Gemini real-time
- Setup AI logging hooks: mỗi lần dùng Claude Code hoặc GitHub Copilot tự động ghi vào `.ai-log/session.jsonl`
- Viết test scripts: `test_pipeline.py` (test toàn bộ RAG pipeline), `test_gemini.py` (test Gemini riêng), `test.py` (smoke test)
- Cập nhật `retrieve_generate.py` để hỗ trợ cả Qwen (local) và Gemini (API), có reranker BAAI/bge-reranker-v2-m3

#### Khó nhất tuần này
- **Pydantic settings crash khi thiếu `.env`**: `python -m app.main` lỗi ngay lúc import vì `Settings()` không tìm thấy biến môi trường bắt buộc — mất thời gian truy nguyên qua stack trace dài.
- **Qwen model không load được**: thiếu package `accelerate`, lỗi chỉ xuất hiện khi model bắt đầu tải weights — phải `pip install accelerate` sau khi đã debug một lúc.
- **Frontend báo `Unexpected end of JSON input`**: backend trả HTTP 500 không kèm JSON body hợp lệ, frontend parse lỗi — phải trace cả hai phía mới tìm ra.
- **Gemini SDK deprecated**: `google.generativeai` in `FutureWarning` — toàn bộ package sắp bị khai tử, cần migrate sang `google.genai`.

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Setup AI logging hooks, thiết kế architecture RAG pipeline | Hooks hoạt động tốt, ghi log đúng theo từng event |
| GitHub Copilot | Debug lỗi terminal (pydantic, accelerate, HTTP 500), giải thích stack trace, viết `test_pipeline.py` | Giải quyết được hầu hết lỗi; Gemini migration vẫn còn dở |

#### Học được
- RAG pipeline là chuỗi phụ thuộc nhiều tầng: OCR → chunk → embed → store → retrieve → rerank → generate — lỗi ở bất kỳ tầng nào sẽ âm thầm làm sai kết quả cuối.
- Pydantic `BaseSettings` fail fast nếu thiếu env var bắt buộc — luôn giữ `.env.example` đồng bộ với model.
- `accelerate` là dependency ngầm của HuggingFace khi load model lên GPU/CPU device map — không có trong `requirements.txt` starter nhưng cần thiết thực tế.
- Deprecated SDK (`google.generativeai`) vẫn chạy được nhưng sẽ bị drop bất cứ lúc nào — nên migrate sớm, không để kỹ thuật nợ tích lũy.

#### Nếu làm lại, sẽ làm khác
- Test từng service độc lập với unit test trước khi tích hợp vào FastAPI — tìm lỗi sớm hơn, không phải trace qua toàn bộ stack.
- Dùng `google.genai` (mới) ngay từ đầu thay vì `google.generativeai` (deprecated).
- Thêm health check endpoint trả về status từng service (OCR, DB, LLM) để debug nhanh khi frontend báo 500.

#### Kế hoạch tuần tới
- Migrate Gemini sang `google.genai` SDK mới
- Test end-to-end với PDF thực tế: upload → OCR → index → chat
- Fix npm vulnerabilities trong frontend (`npm audit fix`)
- Viết `.env` đầy đủ và document các biến bắt buộc trong `QUICKSTART.md`
