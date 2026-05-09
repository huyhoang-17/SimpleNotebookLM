# RAG Learning System

Hệ thống học tập thông minh theo phong cách **NotebookLM**, xây dựng trên nền tảng **RAG (Retrieval-Augmented Generation)**. Người dùng tải lên tài liệu PDF và tương tác qua bốn tính năng chính: hỏi đáp có trích dẫn, tóm tắt, tạo quiz trắc nghiệm và flashcard.

---

## Mục lục

1. [Tính năng](#tính-năng)
2. [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
3. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
4. [Cài đặt](#cài-đặt)
5. [Cấu hình](#cấu-hình)
6. [Hướng dẫn chạy project](#hướng-dẫn-chạy-project)
7. [CLI — Tham chiếu lệnh](#cli--tham-chiếu-lệnh)
8. [REST API — Tham chiếu endpoint](#rest-api--tham-chiếu-endpoint)
9. [Evaluation](#evaluation)
10. [LLM Backends](#llm-backends)
11. [Xử lý sự cố](#xử-lý-sự-cố)

---

## Tính năng

| Tính năng | Mô tả |
|-----------|-------|
| **Hỏi đáp** | Trả lời câu hỏi dựa trên tài liệu với trích dẫn nguồn `[S1]`, `[S2]`... |
| **Tóm tắt** | Tóm tắt tài liệu theo phương pháp Map-Reduce, trích xuất key points |
| **Quiz** | Tự động tạo câu hỏi trắc nghiệm 4 đáp án, có giải thích và mức độ khó |
| **Flashcards** | Tạo bộ thẻ ghi nhớ hai mặt (front/back) kèm gợi ý và chủ đề |
| **Bộ lọc** | Lọc theo tên file, số trang, hoặc section cụ thể |
| **Đa LLM** | Hỗ trợ Gemini API, HuggingFace local, vLLM server |
| **Đa giao diện** | Web UI (Streamlit), REST API (FastAPI), CLI (Typer) |

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                     Giao diện người dùng                  │
│   Streamlit UI  ←→  FastAPI REST  ←→  Typer CLI          │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                      RAG Pipeline                         │
│  indexing.py → store.py → rag.py → learning.py           │
│  (PDF → chunks → Qdrant)  (retrieve → prompt → LLM)      │
└──────────────┬─────────────────────┬────────────────────┘
               │                     │
    ┌──────────▼──────┐   ┌──────────▼──────────┐
    │  Qdrant Vector  │   │    LLM Backend        │
    │  (local files)  │   │  gemini / hf / vllm   │
    └─────────────────┘   └─────────────────────-┘
```

### Cấu trúc thư mục

```
project/
├── src/
│   ├── config.py              # Cấu hình (pydantic-settings, prefix RAG_)
│   ├── schemas.py             # Pydantic models: RagAnswer, Summary, QuizSet, FlashcardSet
│   ├── store.py               # Qdrant vector store + HuggingFace embeddings
│   ├── filters.py             # MetadataFilter → Qdrant filter
│   ├── indexing.py            # Đọc PDF, chia chunk, lưu vào Qdrant
│   ├── rag.py                 # Retrieve + Jinja2 prompt + answer pipeline
│   ├── llm.py                 # LLM backends: hf_local / gemini / vllm
│   ├── export.py              # Xuất kết quả: text / markdown / json
│   ├── learning.py            # Summarize (map-reduce), generate_quiz, generate_flashcards
│   ├── prompts/               # Jinja2 prompt templates (.j2)
│   │   ├── answer.j2
│   │   ├── summary_single.j2
│   │   ├── summary_map.j2
│   │   ├── summary_reduce.j2
│   │   ├── quiz.j2
│   │   └── flashcards.j2
│   ├── interfaces/
│   │   ├── api.py             # FastAPI REST API
│   │   ├── cli.py             # Typer CLI
│   │   └── ui.py              # Streamlit Web UI
│   └── evaluation/
│       ├── chunking_strategies.py   # Recursive & Semantic chunking
│       ├── ragas_evaluator.py       # RAGAS evaluation pipeline
│       ├── run_chunking.py          # Benchmark chunking strategies
│       └── run_reranking.py         # Benchmark Cross-Encoder reranking
├── data/                      # Đặt file PDF vào đây (không commit)
├── storage/                   # Qdrant lưu vector index tại đây (không commit)
├── out/                       # Kết quả xuất ra (text/md/json)
├── evaluation_results/        # Kết quả benchmark
├── .env                       # Biến môi trường (không commit — chứa API key)
├── .env.example               # Mẫu .env
├── pyproject.toml
└── requirements.txt
```

---

## Yêu cầu hệ thống

| Thành phần | Yêu cầu tối thiểu |
|------------|-------------------|
| **Python** | 3.11 trở lên |
| **RAM** | 8 GB (16 GB khuyến nghị khi dùng embedding model) |
| **GPU** | Không bắt buộc — nhưng cần CUDA để chạy embedding model nhanh |
| **Dung lượng** | ~5 GB cho `sentence-transformers` + `torch` |

> **Lưu ý:** Nếu không có GPU, đặt `RAG_HF_DEVICE=-1` trong `.env` để dùng CPU. Quá trình embedding sẽ chậm hơn nhưng vẫn hoạt động bình thường.

---

## Cài đặt

### Bước 1 — Tải source code

```powershell
# Clone hoặc tải về thư mục project
# Đảm bảo bạn đang đứng tại thư mục gốc của project
cd "d:\AI in Action\Project Build Phase\Building Simple NotebookLM"
```

### Bước 2 — Tạo virtual environment

```powershell
# Tạo virtual environment
python -m venv .venv

# Kích hoạt (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Nếu bị lỗi ExecutionPolicy, chạy lệnh này trước:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

```bash
# Linux / macOS:
# python -m venv .venv
# source .venv/bin/activate
```

Sau khi kích hoạt thành công, terminal sẽ hiển thị `(.venv)` ở đầu dòng.

### Bước 3 — Cài đặt dependencies

```powershell
# Cài đặt tất cả packages
pip install -r requirements.txt
```

> **Lưu ý về PyTorch:** Nếu bạn cần GPU (CUDA), hãy cài PyTorch phù hợp với phiên bản CUDA của máy trước khi chạy lệnh trên:
> ```powershell
> # Ví dụ CUDA 12.4 (kiểm tra phiên bản tại pytorch.org/get-started)
> pip install torch --index-url https://download.pytorch.org/whl/cu124
> ```

Hoặc cài đặt dưới dạng package để dùng CLI entry point `rag-cli`:

```powershell
# Cài đặt package (bao gồm tất cả dependencies từ pyproject.toml)
pip install -e .

# Cài thêm evaluation dependencies (nếu cần benchmark)
pip install -e ".[eval]"
```

### Bước 4 — Tạo thư mục cần thiết

```powershell
# Tạo thư mục chứa PDF và output
mkdir data
mkdir out
```

```bash
# Linux / macOS:
# mkdir -p data out
```

---

## Cấu hình

### Bước 1 — Sao chép file cấu hình

```powershell
# Windows (Command Prompt hoặc PowerShell)
copy .env.example .env
```

```bash
# Linux / macOS:
# cp .env.example .env
```

### Bước 2 — Chỉnh sửa file `.env`

Mở file `.env` bằng bất kỳ text editor nào và điền các giá trị phù hợp:

```env
# ---- Bắt buộc khi dùng Gemini ----
GOOGLE_API_KEY=AIzaSy...        # Lấy tại console.cloud.google.com

# ---- Chọn LLM backend ----
RAG_LLM_PROVIDER=gemini         # gemini | hf_local | vllm

# ---- Embedding (nếu không có GPU, đổi sang -1) ----
RAG_HF_DEVICE=0                 # 0 = GPU đầu tiên, -1 = CPU
```

### Tham chiếu biến môi trường

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `RAG_LLM_PROVIDER` | `hf_local` | Backend LLM: `gemini` \| `hf_local` \| `vllm` |
| `GOOGLE_API_KEY` | _(trống)_ | API key Gemini — **bắt buộc** khi `RAG_LLM_PROVIDER=gemini` |
| `RAG_GEMINI_MODEL` | `gemini-2.5-flash` | Tên model Gemini |
| `RAG_EMBEDDING_MODEL` | `GreenNode/GreenNode-Embedding-Large-VN-Mixed-V1` | Model embedding HuggingFace |
| `RAG_HF_DEVICE` | `1` | GPU index cho embedding (`-1` = CPU, `0` = GPU 0) |
| `RAG_HF_MODEL` | _(đường dẫn local)_ | Model HuggingFace cho `hf_local` backend |
| `RAG_HF_MAX_NEW_TOKENS` | `2048` | Số token tối đa sinh ra |
| `RAG_CHUNK_SIZE` | `1000` | Kích thước mỗi chunk (ký tự) |
| `RAG_CHUNK_OVERLAP` | `150` | Số ký tự overlap giữa các chunk |
| `RAG_TOP_K` | `5` | Số chunks truy xuất mặc định |
| `RAG_DATA_DIR` | `data` | Thư mục chứa file PDF |
| `RAG_STORAGE_DIR` | `storage/qdrant` | Thư mục lưu Qdrant vector index |
| `RAG_QDRANT_COLLECTION` | `rag_chunks` | Tên collection trong Qdrant |
| `RAG_API_URL` | `http://localhost:8000` | URL API server (dùng bởi Streamlit UI) |
| `RAG_QUIZ_DEFAULT_COUNT` | `8` | Số câu quiz mặc định |
| `RAG_FLASHCARDS_DEFAULT_COUNT` | `15` | Số flashcard mặc định |
| `RAG_SUMMARIZE_BATCH_SIZE` | `10` | Số chunk xử lý mỗi batch khi tóm tắt |
| `RAG_SUMMARIZE_RETRIEVAL_K` | `12` | Số chunks truy xuất khi tóm tắt |
| `RAG_GENERATION_RETRIEVAL_K` | `16` | Số chunks truy xuất khi sinh quiz/flashcards |

---

## Hướng dẫn chạy project

> **Lưu ý chung:** Tất cả lệnh dưới đây chạy từ **thư mục gốc của project** với virtual environment đã kích hoạt.

---

### Bước 0 — Kiểm tra cài đặt

Trước khi chạy lần đầu, hãy xác nhận môi trường đã sẵn sàng:

```powershell
# Kiểm tra Python version (phải >= 3.11)
python --version

# Kiểm tra các package chính đã được cài
python -c "import langchain; import qdrant_client; import streamlit; print('OK')"
```

---

### Bước 1 — Index tài liệu PDF

Đây là bước **bắt buộc** phải làm trước tất cả các bước còn lại.

**1.1. Đặt file PDF vào thư mục `data/`**

```powershell
# Ví dụ: sao chép file vào thư mục data
copy "C:\Users\Ten\Documents\lecture.pdf" data\
```

**1.2. Chạy indexing**

```powershell
# Phương pháp 1: Dùng module Python (khuyến nghị)
python -m src.interfaces.cli ingest

# Phương pháp 2: Nếu đã cài qua pip install -e .
rag-cli ingest

# Phương pháp 3: Xóa index cũ và tạo lại từ đầu
python -m src.interfaces.cli ingest --recreate
```

Kết quả thành công sẽ hiển thị:

```
Xong. Đã index 247 chunks.
```

> **Lý do dùng `--recreate`:** Khi bạn thêm/xóa file PDF, hoặc thay đổi `RAG_CHUNK_SIZE`, hãy chạy lại với `--recreate` để đảm bảo index nhất quán.

---

### Bước 2 — Chọn giao diện để sử dụng

Bạn có thể dùng một trong ba giao diện: **Web UI**, **REST API**, hoặc **CLI**. Chúng dùng chung cùng một engine RAG bên dưới.

---

### Cách A — Web UI (Streamlit) — Khuyến nghị cho người dùng mới

Web UI cần API server chạy trước. Mở **hai cửa sổ terminal riêng biệt**:

**Terminal 1 — Khởi động API server:**

```powershell
# Kích hoạt virtual environment
.\.venv\Scripts\Activate.ps1

# Chạy API server
uvicorn src.interfaces.api:app --port 8000
```

Chờ đến khi thấy:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Terminal 2 — Khởi động Streamlit UI:**

```powershell
# Kích hoạt virtual environment (trong terminal mới)
.\.venv\Scripts\Activate.ps1

# Chạy Streamlit
streamlit run src\interfaces\ui.py
```

Trình duyệt tự động mở tại **http://localhost:8501**. Nếu không, mở thủ công bằng cách nhập URL vào trình duyệt.

> **Lưu ý cổng:** API server mặc định dùng cổng `8000`. Nếu cổng đó bị chiếm, đổi cả hai:
> - API: `uvicorn src.interfaces.api:app --port 8080`
> - `.env`: `RAG_API_URL=http://localhost:8080`

---

### Cách B — REST API (FastAPI)

Phù hợp cho tích hợp với ứng dụng khác hoặc kiểm thử từng endpoint.

**Khởi động server:**

```powershell
# Chế độ development (tự reload khi code thay đổi)
uvicorn src.interfaces.api:app --reload --port 8000

# Chế độ production
uvicorn src.interfaces.api:app --host 0.0.0.0 --port 8000 --workers 2
```

**Mở API documentation:** http://localhost:8000/docs (Swagger UI tương tác)

**Kiểm tra server hoạt động:**

```powershell
# Windows PowerShell
Invoke-WebRequest -Uri "http://localhost:8000/health" | Select-Object -ExpandProperty Content
```

```bash
# Linux / macOS / Git Bash:
# curl http://localhost:8000/health
```

Kết quả: `{"status":"ok"}`

**Gửi câu hỏi:**

```powershell
# Windows PowerShell
$body = '{"question": "Nội dung chính của tài liệu là gì?", "k": 5}'
Invoke-WebRequest -Uri "http://localhost:8000/ask" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body | Select-Object -ExpandProperty Content
```

```bash
# Linux / macOS / Git Bash:
# curl -X POST http://localhost:8000/ask \
#   -H "Content-Type: application/json" \
#   -d '{"question": "Nội dung chính của tài liệu là gì?", "k": 5}'
```

---

### Cách C — CLI (Command Line)

Phù hợp cho automation, scripting, hoặc dùng trực tiếp trong terminal.

**Hỏi đáp:**

```powershell
python -m src.interfaces.cli ask "Định nghĩa RAG là gì?"

# Chỉ định số chunks truy xuất
python -m src.interfaces.cli ask "RAG là gì?" --k 8

# Lọc theo tài liệu cụ thể
python -m src.interfaces.cli ask "Nội dung chính?" --filters "{\"filename\": \"lecture.pdf\"}"
```

**Tóm tắt:**

```powershell
# Tóm tắt toàn bộ corpus, in ra terminal
python -m src.interfaces.cli summarize

# Tóm tắt một tài liệu và lưu dạng Markdown
python -m src.interfaces.cli summarize --document "lecture.pdf" --fmt md --output out\summary.md

# Tóm tắt theo chủ đề
python -m src.interfaces.cli summarize --query "phần về embedding" --fmt json
```

**Tạo quiz:**

```powershell
# Quiz từ toàn bộ corpus (số câu mặc định: 8)
python -m src.interfaces.cli quiz

# 10 câu từ một tài liệu, in ra terminal
python -m src.interfaces.cli quiz --document "lecture.pdf" --count 10

# Xuất quiz dạng JSON
python -m src.interfaces.cli quiz --count 5 --fmt json --output out\quiz.json
```

**Tạo flashcards:**

```powershell
# Flashcards từ toàn bộ corpus
python -m src.interfaces.cli flashcards

# 20 flashcards từ tài liệu cụ thể
python -m src.interfaces.cli flashcards --document "lecture.pdf" --count 20

# Xuất dạng Markdown
python -m src.interfaces.cli flashcards --count 15 --fmt md --output out\flashcards.md
```

**Debug retrieval:**

```powershell
# Xem các chunks được truy xuất cho một câu hỏi (debug mode)
python -m src.interfaces.cli debug-retrieval "embedding là gì?"
python -m src.interfaces.cli debug-retrieval "RAG pipeline" --k 10
```

---

## CLI — Tham chiếu lệnh

### `ingest`

```
python -m src.interfaces.cli ingest [OPTIONS]
```

| Option | Mô tả |
|--------|-------|
| `--recreate` | Xóa collection hiện tại và tạo lại từ đầu |

### `ask`

```
python -m src.interfaces.cli ask QUESTION [OPTIONS]
```

| Option | Mặc định | Mô tả |
|--------|----------|-------|
| `--k INT` | `RAG_TOP_K` | Số chunks truy xuất |
| `--filters JSON` | _(trống)_ | Bộ lọc dạng JSON: `{"filename": "...", "page": N}` |

### `summarize`

```
python -m src.interfaces.cli summarize [OPTIONS]
```

| Option | Mặc định | Mô tả |
|--------|----------|-------|
| `--document TEXT` | _(tất cả)_ | Tên file PDF cần tóm tắt |
| `--query TEXT` | _(trống)_ | Câu truy vấn định hướng tóm tắt |
| `--filters JSON` | _(trống)_ | Bộ lọc metadata |
| `--k INT` | `RAG_SUMMARIZE_RETRIEVAL_K` | Số chunks truy xuất |
| `--fmt TEXT` | `text` | Định dạng xuất: `text` \| `md` \| `json` |
| `--output PATH` | _(stdout)_ | Đường dẫn file lưu kết quả |

### `quiz`

```
python -m src.interfaces.cli quiz [OPTIONS]
```

| Option | Mặc định | Mô tả |
|--------|----------|-------|
| `--document TEXT` | _(tất cả)_ | Tên file PDF |
| `--query TEXT` | _(trống)_ | Chủ đề quiz |
| `--count INT` | `RAG_QUIZ_DEFAULT_COUNT` | Số câu hỏi |
| `--fmt TEXT` | `text` | `text` \| `md` \| `json` |
| `--output PATH` | _(stdout)_ | File lưu kết quả |

### `flashcards`

```
python -m src.interfaces.cli flashcards [OPTIONS]
```

Tham số giống `quiz`, nhưng `--count` mặc định là `RAG_FLASHCARDS_DEFAULT_COUNT`.

### `debug-retrieval`

```
python -m src.interfaces.cli debug-retrieval QUERY [OPTIONS]
```

In ra JSON chứa danh sách chunks được truy xuất, kèm score và metadata.

---

## REST API — Tham chiếu endpoint

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/health` | Kiểm tra server |
| `GET` | `/documents` | Danh sách tài liệu đã index kèm số chunk |
| `POST` | `/upload` | Tải lên và index file PDF mới |
| `POST` | `/ask` | Hỏi đáp có trích dẫn |
| `POST` | `/summarize` | Tóm tắt tài liệu |
| `POST` | `/quiz` | Tạo quiz trắc nghiệm |
| `POST` | `/flashcards` | Tạo flashcards |

### `POST /ask`

**Request body:**
```json
{
  "question": "Embedding là gì?",
  "k": 5,
  "filters": {
    "filename": "lecture.pdf",
    "page": null,
    "section": null
  }
}
```

**Response:** `RagAnswer`
```json
{
  "question": "Embedding là gì?",
  "answer": "Embedding là... [S1] ... [S2]",
  "citations": [
    {"source_index": 1, "source_marker": "[S1]", "filename": "lecture.pdf", "page": 12}
  ],
  "chunks": [...]
}
```

### `POST /upload`

Upload file PDF (multipart/form-data):

```powershell
# Windows PowerShell
$form = @{ file = Get-Item ".\data\lecture.pdf" }
Invoke-WebRequest -Uri "http://localhost:8000/upload" -Method POST -Form $form
```

```bash
# Linux / macOS / Git Bash:
# curl -X POST http://localhost:8000/upload -F "file=@data/lecture.pdf"
```

### `POST /summarize`

```json
{
  "document": "lecture.pdf",
  "query": "phần về kiến trúc transformer",
  "k": 12
}
```

Tất cả fields là tùy chọn — bỏ trống `document` để tóm tắt toàn bộ corpus.

### `POST /quiz` và `POST /flashcards`

```json
{
  "document": "lecture.pdf",
  "count": 10,
  "k": 16,
  "filters": null
}
```

---

## Evaluation

Module evaluation dùng RAGAS để đánh giá chất lượng RAG pipeline. Cần cài thêm dependencies:

```powershell
pip install -e ".[eval]"
# hoặc:
pip install ragas datasets pandas
```

**Benchmark chunking strategies:**

```powershell
# So sánh Recursive Chunking với các kích thước khác nhau
# và Semantic Chunking
python -m src.evaluation.run_chunking
```

**Benchmark Cross-Encoder reranking:**

```powershell
# So sánh retrieval có/không có reranking (BAAI/bge-reranker-v2-m3)
python -m src.evaluation.run_reranking
```

Kết quả được lưu vào `evaluation_results/` dưới dạng JSON với các metrics RAGAS:

| Metric | Mô tả |
|--------|-------|
| `faithfulness` | Câu trả lời có trung thực với context không? |
| `answer_relevancy` | Câu trả lời có liên quan đến câu hỏi không? |
| `context_precision` | Trong các chunks được truy xuất, bao nhiêu % thực sự hữu ích? |
| `context_recall` | Bao nhiêu % thông tin cần thiết đã được truy xuất? |

---

## LLM Backends

### Gemini (khuyến nghị để bắt đầu)

Không cần GPU, dễ setup. Cần có Google API key.

```env
RAG_LLM_PROVIDER=gemini
RAG_GEMINI_MODEL=gemini-2.5-flash
GOOGLE_API_KEY=AIzaSy...
```

Lấy API key tại: https://aistudio.google.com/app/apikey

### HuggingFace Local

Chạy model hoàn toàn offline, cần GPU.

```env
RAG_LLM_PROVIDER=hf_local
RAG_HF_MODEL=Qwen/Qwen3-4B-Instruct     # HuggingFace Hub ID
# hoặc đường dẫn local:
# RAG_HF_MODEL=C:\models\Qwen3-4B-Instruct
RAG_HF_DEVICE=0                          # GPU 0
RAG_HF_MAX_NEW_TOKENS=2048
```

Model được tải lần đầu tiên khi khởi động (có thể mất vài phút tùy tốc độ internet).

### vLLM (high-throughput)

Dùng khi đã deploy model trên vLLM server riêng. Phù hợp cho production.

```powershell
# Bước 1: Khởi động vLLM server (trong terminal riêng)
# Cần cài vllm: pip install vllm
# vllm serve Qwen/Qwen3-4B-Instruct --port 8001
```

```env
RAG_LLM_PROVIDER=vllm
RAG_VLLM_API_BASE=http://localhost:8001/v1
RAG_HF_MODEL=Qwen/Qwen3-4B-Instruct
RAG_VLLM_API_KEY=EMPTY
```

---

## Xử lý sự cố

### Lỗi kích hoạt virtual environment trên Windows

**Triệu chứng:** `cannot be loaded because running scripts is disabled on this system`

**Giải pháp:**
```powershell
# Chạy với quyền Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### Lỗi `GOOGLE_API_KEY is required`

**Triệu chứng:** `ValueError: GOOGLE_API_KEY is required when llm_provider='gemini'`

**Giải pháp:** Mở file `.env` và điền giá trị `GOOGLE_API_KEY`:
```env
GOOGLE_API_KEY=AIzaSy...your-actual-key-here
```

---

### Lỗi `Collection not found` khi hỏi đáp

**Triệu chứng:** `qdrant_client.http.exceptions.UnexpectedResponse: Collection not found`

**Giải pháp:** Chưa chạy indexing. Đặt PDF vào `data/` rồi chạy:
```powershell
python -m src.interfaces.cli ingest
```

---

### Lỗi `No module named 'src'`

**Triệu chứng:** `ModuleNotFoundError: No module named 'src'`

**Nguyên nhân:** Chạy lệnh sai thư mục, hoặc dùng `python src/interfaces/cli.py` thay vì `-m`.

**Giải pháp:**
```powershell
# Đảm bảo đang đứng ở thư mục gốc project
cd "d:\AI in Action\Project Build Phase\Building Simple NotebookLM"

# Dùng cú pháp -m, KHÔNG dùng đường dẫn file
python -m src.interfaces.cli ask "câu hỏi của bạn"
```

---

### Embedding model tải chậm

**Triệu chứng:** Lần đầu chạy `ingest` mất rất lâu.

**Giải pháp:** Model `GreenNode/GreenNode-Embedding-Large-VN-Mixed-V1` (~1.5 GB) được tải về từ HuggingFace Hub lần đầu tiên. Các lần sau sẽ dùng cache. Mặc định cache tại `C:\Users\<tên>\\.cache\huggingface\`.

---

### Cổng 8000 bị chiếm dụng

**Triệu chứng:** `ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)`

**Giải pháp:** Đổi cổng và cập nhật `.env`:
```powershell
uvicorn src.interfaces.api:app --port 8080
```
```env
RAG_API_URL=http://localhost:8080
```

---

### Streamlit không kết nối được API

**Triệu chứng:** Thông báo lỗi "Không thể kết nối đến API server" trong Streamlit UI.

**Giải pháp:**
1. Đảm bảo API server đang chạy (Terminal 1)
2. Kiểm tra `RAG_API_URL` trong `.env` khớp với cổng của API server
3. Thử truy cập http://localhost:8000/health trong trình duyệt để xác nhận API hoạt động
