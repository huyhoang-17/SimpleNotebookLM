# VinLM — RAG Learning System

Hệ thống học tập thông minh theo phong cách **NotebookLM**, xây dựng trên nền tảng **RAG (Retrieval-Augmented Generation)**. Người dùng đăng nhập, tải lên tài liệu PDF của riêng mình và tương tác qua bốn tính năng chính: hỏi đáp có trích dẫn, tóm tắt, tạo quiz trắc nghiệm và flashcard. Hệ thống hỗ trợ nhiều người dùng (per-user ownership) và có panel quản trị dành cho admin.

---

## Mục lục

1. [Tính năng](#tính-năng)
2. [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
3. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
4. [Cài đặt](#cài-đặt)
5. [Cấu hình](#cấu-hình)
6. [Hướng dẫn chạy project](#hướng-dẫn-chạy-project)
7. [Xác thực & Phân quyền](#xác-thực--phân-quyền)
8. [CLI — Tham chiếu lệnh](#cli--tham-chiếu-lệnh)
9. [REST API — Tham chiếu endpoint](#rest-api--tham-chiếu-endpoint)
10. [Deploy](#deploy)
11. [Evaluation](#evaluation)
12. [LLM Backends](#llm-backends)
13. [Xử lý sự cố](#xử-lý-sự-cố)

---

## Tính năng

| Tính năng | Mô tả |
|-----------|-------|
| **Hỏi đáp** | Trả lời câu hỏi dựa trên tài liệu với trích dẫn nguồn `[S1]`, `[S2]`... |
| **Tóm tắt** | Tóm tắt tài liệu theo phương pháp Map-Reduce, trích xuất key points |
| **Quiz** | Tự động tạo câu hỏi trắc nghiệm 4 đáp án, có giải thích và mức độ khó |
| **Flashcards** | Tạo bộ thẻ ghi nhớ hai mặt (front/back) kèm gợi ý và chủ đề |
| **Bộ lọc** | Lọc theo tên file, số trang, hoặc section cụ thể |
| **Xác thực** | Đăng ký / Đăng nhập, JWT cho REST API, session cho Streamlit UI |
| **Phân quyền** | Mỗi user chỉ thấy tài liệu của mình; admin thấy & quản lý toàn hệ thống |
| **Quản trị** | Admin tạo / sửa role / vô hiệu hoá / reset mật khẩu / xoá user |
| **Lịch sử hỏi đáp** | Mọi câu hỏi đều được log; tab Lịch sử cho phép tìm kiếm và xoá |
| **Đa LLM** | Hỗ trợ Gemini API, HuggingFace local, vLLM server |
| **Đa giao diện** | Web UI (Streamlit), REST API (FastAPI), CLI (Typer) |

---

## Kiến trúc hệ thống

```
┌───────────────────────────────────────────────────────────┐
│                     Giao diện người dùng                   │
│   Streamlit UI  ←→  FastAPI REST  ←→  Typer CLI            │
│   (session)         (JWT bearer)      (unauth, --user)     │
└──────────────────────────┬────────────────────────────────┘
                           │  Depends(get_current_user)
                           │  + owner_filter_for(user)
┌──────────────────────────▼────────────────────────────────┐
│                      RAG Pipeline                          │
│  indexing.py → store.py → rag.py → learning.py             │
│  (PDF → chunks → Qdrant)  (retrieve → prompt → LLM)        │
└──────────────┬─────────────────┬──────────────┬───────────┘
               │                 │              │
    ┌──────────▼──────┐  ┌───────▼──────┐  ┌────▼──────────┐
    │  Qdrant Vector  │  │ LLM Backend  │  │  Auth (SQLite) │
    │  + owner_id tag │  │ gemini / hf  │  │  User +        │
    │  (local files)  │  │ / vllm       │  │  QuestionLog   │
    └─────────────────┘  └──────────────┘  └────────────────┘
```

### Cấu trúc thư mục

```
project/
├── src/
│   ├── config.py              # Cấu hình (pydantic-settings, prefix RAG_)
│   ├── schemas.py             # Pydantic models: ChunkMetadata, RagAnswer, Summary, QuizSet, FlashcardSet
│   ├── store.py               # Qdrant vector store + HuggingFace embeddings (payload có owner_id)
│   ├── filters.py             # MetadataFilter → Qdrant filter
│   ├── indexing.py            # Đọc PDF, chia chunk, lưu vào Qdrant (gắn owner_id)
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
│   ├── auth/                  # Xác thực & quản lý user
│   │   ├── models.py          # SQLModel: User, QuestionLog
│   │   ├── db.py              # SQLite engine, init_db
│   │   ├── security.py        # bcrypt (passlib) + JWT HS256 (python-jose)
│   │   ├── service.py         # CRUD user, authenticate, ensure_seed_admin, log_question
│   │   ├── deps.py            # get_current_user, require_role, owner_filter_for
│   │   └── router.py          # /auth/* và /admin/users/*
│   ├── interfaces/
│   │   ├── api.py             # FastAPI REST API (đã gắn JWT cho mọi RAG endpoint)
│   │   ├── cli.py             # Typer CLI
│   │   ├── ui.py              # Streamlit Web UI (login + admin tab)
│   │   ├── session.py         # Tiện ích state cho Streamlit
│   │   └── styles.py          # CSS tuỳ chỉnh cho Streamlit
│   ├── docs/
│   │   └── user_guide.md      # Hướng dẫn người dùng cuối (Vietnamese)
│   └── evaluation/
│       ├── chunking_strategies.py   # Recursive & Semantic chunking
│       ├── ragas_evaluator.py       # RAGAS evaluation pipeline
│       ├── run_chunking.py          # Benchmark chunking strategies
│       └── run_reranking.py         # Benchmark Cross-Encoder reranking
├── data/                      # Đặt file PDF vào đây (không commit)
├── storage/                   # Qdrant vector index + auth.db SQLite (không commit)
├── out/                       # Kết quả xuất ra (text/md/json)
├── evaluation_results/        # Kết quả benchmark
├── .streamlit/
│   └── config.toml            # Theme + headless cho Streamlit Cloud
├── .env                       # Biến môi trường (không commit — chứa API key + JWT secret)
├── .env.example               # Mẫu .env
├── pyproject.toml
├── requirements.txt
└── requirements-eval.txt
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
# Tạo thư mục chứa PDF, output và storage (vector index + auth DB)
mkdir data
mkdir out
mkdir storage
```

```bash
# Linux / macOS:
# mkdir -p data out storage
```

> Thư mục `storage/` sẽ chứa cả `storage/qdrant/` (vector index) và `storage/auth.db` (SQLite cho user + question logs). **Không commit thư mục này.**

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
GOOGLE_API_KEY=AIzaSy...        # Lấy tại aistudio.google.com/app/apikey

# ---- Chọn LLM backend ----
RAG_LLM_PROVIDER=gemini         # gemini | hf_local | vllm

# ---- Embedding (mặc định CPU; có GPU thì đổi sang 0) ----
RAG_HF_DEVICE=-1                # -1 = CPU, 0 = GPU đầu tiên

# ---- Auth (BẮT BUỘC override ở production) ----
RAG_JWT_SECRET=<chuỗi-ngẫu-nhiên-tối-thiểu-32-ký-tự>
RAG_ADMIN_USERNAME=admin
RAG_ADMIN_PASSWORD=<mật-khẩu-admin-mạnh>
```

### Tham chiếu biến môi trường

**LLM & Embedding**

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `RAG_LLM_PROVIDER` | `gemini` | Backend LLM: `gemini` \| `hf_local` \| `vllm` |
| `GOOGLE_API_KEY` | _(trống)_ | API key Gemini — **bắt buộc** khi `RAG_LLM_PROVIDER=gemini` |
| `RAG_GEMINI_MODEL` | `gemini-2.5-flash` | Tên model Gemini |
| `RAG_LLM_TEMPERATURE` | `0.1` | Temperature cho generation |
| `RAG_EMBEDDING_MODEL` | `GreenNode/GreenNode-Embedding-Large-VN-Mixed-V1` | Model embedding HuggingFace |
| `RAG_HF_DEVICE` | `-1` | GPU index cho embedding (`-1` = CPU, `0` = GPU 0) |
| `RAG_HF_MODEL` | _(đường dẫn local)_ | Model HuggingFace cho `hf_local` backend |
| `RAG_HF_MAX_NEW_TOKENS` | `2048` | Số token tối đa sinh ra |
| `RAG_VLLM_API_BASE` | `http://localhost:8001/v1` | Endpoint của vLLM server |
| `RAG_VLLM_API_KEY` | `EMPTY` | API key cho vLLM (thường để mặc định) |

**RAG pipeline**

| Biến | Mặc định | Mô tả |
|------|----------|-------|
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

**Xác thực & quản trị**

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `RAG_AUTH_DB_PATH` | `storage/auth.db` | Đường dẫn file SQLite chứa users + question_logs |
| `RAG_JWT_SECRET` | `change-me-in-production` | Secret ký JWT — **bắt buộc override** ở production |
| `RAG_JWT_EXPIRES_MIN` | `1440` (24 giờ) | Thời hạn access token (phút) |
| `RAG_JWT_ALGORITHM` | `HS256` | Thuật toán ký JWT |
| `RAG_ADMIN_USERNAME` | `admin` | Username của tài khoản admin được seed lần đầu |
| `RAG_ADMIN_PASSWORD` | _(trống)_ | Mật khẩu admin seed. Nếu trống, mật khẩu ngẫu nhiên sẽ được in ra log với mức WARNING khi khởi động lần đầu |

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

Web UI gọi **trực tiếp** RAG pipeline + auth service trong cùng process (không qua HTTP), vì vậy **không cần khởi động FastAPI** nếu bạn chỉ dùng Streamlit.

Khởi động:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run src\interfaces\ui.py
```

Trình duyệt tự động mở tại **http://localhost:8501**. Trang đầu tiên là màn hình **Đăng nhập / Đăng ký** — nhập tài khoản admin đã seed (xem [Seed admin lần đầu](#seed-admin-lần-đầu)).

### Cách A.b — Streamlit + FastAPI cùng lúc (tuỳ chọn)

Nếu muốn cả UI và REST API hoạt động song song (ví dụ để tích hợp với hệ thống khác), mở **hai cửa sổ terminal riêng biệt**:

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

**Gửi câu hỏi** (cần Bearer token — xem mục [Đăng nhập và gọi API có JWT](#đăng-nhập-và-gọi-api-có-jwt)):

```powershell
# Windows PowerShell
$body = '{"question": "Nội dung chính của tài liệu là gì?", "k": 5}'
Invoke-WebRequest -Uri "http://localhost:8000/ask" `
    -Method POST `
    -ContentType "application/json" `
    -Headers @{ Authorization = "Bearer $token" } `
    -Body $body | Select-Object -ExpandProperty Content
```

```bash
# Linux / macOS / Git Bash:
# curl -X POST http://localhost:8000/ask \
#   -H "Authorization: Bearer $TOKEN" \
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

## Xác thực & Phân quyền

VinLM dùng **JWT HS256** cho REST API và **session state** cho Streamlit UI. CSDL user là **SQLite** (file `storage/auth.db`), không cần dịch vụ ngoài.

### Mô hình user

| Trường | Kiểu | Ghi chú |
|--------|------|---------|
| `id` | int PK | tự sinh |
| `username` | str (≥3 ký tự, unique) | dùng làm `owner_id` cho mọi chunk người dùng upload |
| `email` | str (optional) | |
| `password_hash` | str | hash bằng `passlib[bcrypt]` |
| `role` | `user` \| `admin` | `user` chỉ thấy tài liệu của mình, `admin` thấy & quản lý tất cả |
| `active` | bool | tài khoản bị `active=false` không đăng nhập được |
| `created_at`, `last_login` | datetime | |

Bảng phụ `question_logs` ghi lại mọi câu hỏi (question, answer preview, k, filenames, success/error) — dùng cho tab **Lịch sử** trong Streamlit và endpoint admin.

### Seed admin lần đầu

Khi FastAPI hoặc Streamlit khởi động lần đầu, `ensure_seed_admin()` chạy trong lifespan:
- Nếu DB rỗng → tạo user `RAG_ADMIN_USERNAME` (mặc định `admin`) với role `admin`.
- Mật khẩu lấy từ `RAG_ADMIN_PASSWORD`. Nếu không set, một mật khẩu ngẫu nhiên 12 ký tự được sinh và **in ra log với mức WARNING** — **đăng nhập và đổi ngay**.

### Ownership & filter

- Mỗi chunk trong Qdrant có metadata `owner_id`. Tất cả endpoint RAG (`/ask`, `/summarize`, `/quiz`, `/flashcards`, `/documents`, `/upload`) đều `Depends(get_current_user)` và merge `owner_filter_for(user)` vào filter:
  - `user` → `{"owner_id": <username>}` (chỉ thấy tài liệu của mình).
  - `admin` → `{}` (thấy tất cả).
- Client **không thể giả mạo** `owner_id` — server luôn ghi đè giá trị này từ JWT.

### Bảo vệ admin

Admin không thể làm các thao tác sau lên **chính mình** (server trả `400`):
- Vô hiệu hoá `active=false`.
- Hạ role xuống `user`.
- Xoá tài khoản.

---

## CLI — Tham chiếu lệnh

### `ingest`

```
python -m src.interfaces.cli ingest [OPTIONS]
```

| Option | Mô tả |
|--------|-------|
| `--recreate` | Xóa collection hiện tại và tạo lại từ đầu |
| `--user TEXT` | Gán `owner_id` cho các chunk được ingest. Nếu bỏ trống, chunk không có owner và chỉ admin thấy được. |

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

> ⚠️ Mọi endpoint **trừ** `/health`, `/auth/register`, `/auth/login` đều yêu cầu header `Authorization: Bearer <access_token>`. Lấy token qua `POST /auth/login` (form-encoded).

### Endpoints RAG

| Method | Endpoint | Auth | Mô tả |
|--------|----------|------|-------|
| `GET` | `/health` | _none_ | Kiểm tra server |
| `GET` | `/documents` | user | Danh sách tài liệu đã index của user kèm số chunk (admin thấy tất cả) |
| `POST` | `/upload` | user | Tải lên và index file PDF mới (gắn `owner_id` từ JWT) |
| `POST` | `/ask` | user | Hỏi đáp có trích dẫn |
| `POST` | `/summarize` | user | Tóm tắt tài liệu |
| `POST` | `/quiz` | user | Tạo quiz trắc nghiệm |
| `POST` | `/flashcards` | user | Tạo flashcards |

### Endpoints Auth

| Method | Endpoint | Auth | Mô tả |
|--------|----------|------|-------|
| `POST` | `/auth/register` | _none_ | Đăng ký user mới (role `user`) |
| `POST` | `/auth/login` | _none_ | Đăng nhập (form `username` + `password`), trả về `access_token` |
| `GET` | `/auth/me` | user | Thông tin tài khoản hiện tại |
| `POST` | `/auth/change-password` | user | Đổi mật khẩu (yêu cầu mật khẩu cũ) |

### Endpoints Admin (yêu cầu role `admin`)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/admin/users` | Liệt kê tất cả user |
| `POST` | `/admin/users` | Tạo user mới (chọn role tuỳ ý) |
| `PATCH` | `/admin/users/{user_id}` | Cập nhật `role` / `active` / `email` |
| `POST` | `/admin/users/{user_id}/reset-password` | Reset mật khẩu user khác |
| `DELETE` | `/admin/users/{user_id}` | Xoá user (và toàn bộ question_logs của user đó) |

### Đăng nhập và gọi API có JWT

```powershell
# Bước 1 — Đăng nhập (form-encoded, KHÔNG phải JSON)
$resp = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" `
    -Method POST `
    -ContentType "application/x-www-form-urlencoded" `
    -Body "username=admin&password=<mật-khẩu>"
$token = $resp.access_token

# Bước 2 — Gọi endpoint protected
Invoke-RestMethod -Uri "http://localhost:8000/documents" `
    -Headers @{ Authorization = "Bearer $token" }
```

```bash
# Linux / macOS / Git Bash:
# TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
#   -d "username=admin&password=<mật-khẩu>" | jq -r .access_token)
# curl http://localhost:8000/documents -H "Authorization: Bearer $TOKEN"
```

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

Upload file PDF (multipart/form-data) — server tự gán `owner_id` từ JWT.

```powershell
# Windows PowerShell
$form = @{ file = Get-Item ".\data\lecture.pdf" }
Invoke-WebRequest -Uri "http://localhost:8000/upload" `
    -Method POST `
    -Headers @{ Authorization = "Bearer $token" } `
    -Form $form
```

```bash
# Linux / macOS / Git Bash:
# curl -X POST http://localhost:8000/upload \
#   -H "Authorization: Bearer $TOKEN" \
#   -F "file=@data/lecture.pdf"
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

## Deploy

VinLM được thiết kế để chạy **single-node**, không phụ thuộc dịch vụ ngoài (Qdrant local files + SQLite). Có thể deploy theo các phương án sau.

### Local / VPS — Streamlit + FastAPI cùng lúc

Trên cùng một máy, chạy 2 process:

```powershell
# Terminal 1 — API
uvicorn src.interfaces.api:app --host 0.0.0.0 --port 8000

# Terminal 2 — UI
streamlit run src\interfaces\ui.py --server.port 8501 --server.headless true
```

Reverse-proxy (nginx/Caddy) đặt phía trước để bật HTTPS. Đảm bảo **chỉ expose Streamlit ra public**, FastAPI chạy nội bộ trên `127.0.0.1:8000`.

### Streamlit Cloud

UI có thể deploy trực tiếp lên Streamlit Cloud. Vì Streamlit Cloud cấp app từ một repo git, lưu ý:

- Entry point: `src/interfaces/ui.py`.
- `.streamlit/config.toml` đã sẵn sàng (`headless = true`, theme cam-trắng).
- **Secrets**: đăng ký các biến môi trường sau trong **Secrets** của app (UI sẽ tự bridge sang `os.environ`):
  - `GOOGLE_API_KEY`
  - `RAG_JWT_SECRET` (đặt giá trị mạnh — đừng dùng default)
  - `RAG_ADMIN_USERNAME`, `RAG_ADMIN_PASSWORD`
  - `RAG_LLM_PROVIDER=gemini`, `RAG_HF_DEVICE=-1` (Streamlit Cloud không có GPU)
- SQLite `storage/auth.db` được tạo trên disk của container; **lưu ý disk Streamlit Cloud không persistent giữa các lần restart** → user/admin sẽ bị seed lại. Với deploy serious nên migrate sang Postgres/external DB hoặc backup `storage/` định kỳ.
- `data/` upload trong runtime cũng có cùng giới hạn — sau khi container restart, cần re-ingest.

### Production checklist

- [ ] **`RAG_JWT_SECRET` đã override** (mặc định `change-me-in-production` sẽ KHÔNG được chấp nhận trong real prod).
- [ ] **`RAG_ADMIN_PASSWORD` đã set** trước khi khởi động lần đầu (nếu không, mật khẩu in ra log).
- [ ] HTTPS đã bật ở reverse proxy.
- [ ] `.env` và `storage/auth.db` không bị commit vào git.
- [ ] Backup `storage/` (chứa cả vector index và `auth.db`).
- [ ] Quan sát log `WARNING` khi seed admin để biết mật khẩu ngẫu nhiên (nếu lỡ quên set).

### Workers / scale-out

```powershell
uvicorn src.interfaces.api:app --host 0.0.0.0 --port 8000 --workers 2
```

⚠️ **Cảnh báo**: Qdrant chạy chế độ local-file (`storage/qdrant`) — nhiều worker cùng mở file lock có thể gây contention. Nếu cần scale, đổi sang **Qdrant server riêng** (`QdrantClient(url=...)`) thay vì local files.

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

---

### Lỗi bcrypt khi hash mật khẩu

**Triệu chứng:** `AttributeError: module 'bcrypt' has no attribute '__about__'` hoặc passlib bị fail khi `hash()`.

**Nguyên nhân:** `passlib 1.7.4` đọc `bcrypt.__about__` đã bị xoá từ `bcrypt 4.1.0`.

**Giải pháp:** Pin `bcrypt < 4.1` (đã có trong `requirements.txt`):
```
bcrypt>=4.0,<4.1
```

Nếu đã lỡ cài bản mới, hạ phiên bản:
```powershell
pip install "bcrypt>=4.0,<4.1"
```

---

### Lỗi 401 "Could not validate credentials" khi gọi API

**Triệu chứng:** Mọi endpoint trừ `/health`, `/auth/register`, `/auth/login` trả về `401`.

**Nguyên nhân:** Thiếu header `Authorization: Bearer <token>`, token đã hết hạn (`RAG_JWT_EXPIRES_MIN`), hoặc token được ký bằng `RAG_JWT_SECRET` khác.

**Giải pháp:**
1. Login lại để lấy token mới qua `POST /auth/login` (form-encoded).
2. Đảm bảo `RAG_JWT_SECRET` không đổi giữa hai lần khởi động server, nếu không mọi token cũ đều bị invalid.

---

### Quên mật khẩu admin

**Triệu chứng:** Không có `RAG_ADMIN_PASSWORD` ở lần khởi động đầu, mật khẩu in ra log đã mất.

**Giải pháp:**
- **Khuyến nghị**: xoá file `storage/auth.db` (mất toàn bộ user), đặt lại `RAG_ADMIN_PASSWORD` trong `.env`, khởi động lại — admin được seed lại với mật khẩu bạn chọn.
- Hoặc dùng SQLite CLI cập nhật trực tiếp `password_hash` (cần hash bằng passlib).

---

### `no such table: users` khi viết test

**Triệu chứng:** Test với FastAPI `TestClient` báo `sqlite3.OperationalError: no such table: users`.

**Nguyên nhân:** `TestClient(app)` thuần **không chạy lifespan**, nên `ensure_seed_admin()` (chỗ tạo bảng) bị bỏ qua.

**Giải pháp:** Phải dùng `with`-block:
```python
from fastapi.testclient import TestClient
from src.interfaces.api import app

with TestClient(app) as client:    # ← lifespan chạy ở đây
    resp = client.post("/auth/login", data={"username": "admin", "password": "..."})
```
