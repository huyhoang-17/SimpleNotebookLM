# Database & Migrations

VinLM dùng SQLite làm default (file `storage/auth.db`). Có thể chuyển sang PostgreSQL qua biến môi trường.

## Schema (5 bảng)

- `users` — tài khoản (admin/user)
- `question_logs` — lịch sử Q&A
- `documents` — source of truth của tài liệu (filename, owner, status, chunk_count…)
- `ingestion_jobs` — log mỗi lần upload + ingest (success/failed/error message)
- `question_citations` — chuẩn hóa lịch sử trích dẫn theo từng câu hỏi

## Auto-migrate khi khởi động

`ensure_seed_admin()` chạy `alembic upgrade head` khi `RAG_DB_AUTO_MIGRATE=true` (default).
Tắt bằng `RAG_DB_AUTO_MIGRATE=false` → fallback `SQLModel.metadata.create_all()`.

## Chuyển sang PostgreSQL

```bash
pip install "psycopg[binary]>=3.1"
# Trong .env
RAG_DB_URL=postgresql+psycopg://user:pass@localhost:5432/vinlm
```

Khởi động lại app → Alembic tự `upgrade head` trên Postgres (idempotent — gọi nhiều lần không sao).

## Chạy migration thủ công

```bash
alembic upgrade head        # latest
alembic upgrade +1          # 1 revision
alembic downgrade -1        # rollback 1
alembic current             # version hiện tại
alembic history             # lịch sử
```

## Backfill (revision `0003`)

Scan toàn bộ Qdrant payload hiện có → populate `documents`. Skip nếu DB chưa có user khớp `owner_id` payload → gán `status='orphan'`. Idempotent: chạy lại sẽ skip rows đã tồn tại.
