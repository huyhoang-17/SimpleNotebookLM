import json
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path when run directly
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import typer

from ..export import export as export_result
from ..indexing import ingest as _ingest
from ..learning import generate_flashcards, generate_quiz, summarize as summarize_learning
from ..rag import answer, retrieve

app = typer.Typer(help="RAG Learning System CLI")


def _parse_filters(filters_str: Optional[str]) -> Optional[dict]:
    if not filters_str:
        return None
    try:
        return json.loads(filters_str)
    except json.JSONDecodeError:
        typer.echo(f"Warning: could not parse filters JSON: {filters_str}", err=True)
        return None


def _print_answer(text: str) -> None:
    typer.echo("\n" + text + "\n")


def _print_sources(chunks) -> None:
    if not chunks:
        return
    typer.echo("Nguồn:")
    seen = set()
    for chunk in chunks:
        key = (chunk.metadata.filename, chunk.metadata.page)
        if key not in seen:
            seen.add(key)
            typer.echo(f"  - {chunk.metadata.filename}, trang {chunk.metadata.page}")


def _emit(result, output: Optional[str], fmt: str) -> None:
    text = export_result(result, fmt=fmt, output=Path(output) if output else None)
    if output is None:
        typer.echo(text)
    else:
        typer.echo(f"Đã lưu vào {output}")


@app.command()
def ingest(
    recreate: bool = typer.Option(False, "--recreate", help="Xóa và tạo lại collection"),
):
    count = _ingest(recreate=recreate)
    typer.echo(f"Xong. Đã index {count} chunks.")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Câu hỏi"),
    k: Optional[int] = typer.Option(None, help="Số chunks truy xuất"),
    filters: Optional[str] = typer.Option(None, help="Bộ lọc dạng JSON"),
):
    result = answer(question, k=k, filters=_parse_filters(filters))
    _print_answer(result.answer)
    _print_sources(result.chunks)


@app.command("debug-retrieval")
def debug_retrieval(
    question: str = typer.Argument(..., help="Câu truy vấn"),
    k: Optional[int] = typer.Option(None, help="Số chunks"),
    filters: Optional[str] = typer.Option(None, help="Bộ lọc dạng JSON"),
):
    chunks = retrieve(question, k=k, filters=_parse_filters(filters))
    typer.echo(json.dumps([c.model_dump() for c in chunks], ensure_ascii=False, indent=2))


@app.command("summarize")
def summarize_cmd(
    document: Optional[str] = typer.Option(None, help="Tên file tài liệu"),
    query: Optional[str] = typer.Option(None, help="Câu truy vấn cho tóm tắt"),
    filters: Optional[str] = typer.Option(None, help="Bộ lọc dạng JSON"),
    k: Optional[int] = typer.Option(None),
    output: Optional[str] = typer.Option(None, help="Đường dẫn file đầu ra"),
    fmt: str = typer.Option("text", help="Định dạng: text, md, json"),
):
    result = summarize_learning(
        document=document, query=query, filters=_parse_filters(filters), k=k
    )
    _emit(result, output, fmt)


@app.command("quiz")
def quiz_cmd(
    document: Optional[str] = typer.Option(None),
    query: Optional[str] = typer.Option(None),
    filters: Optional[str] = typer.Option(None),
    count: Optional[int] = typer.Option(None),
    k: Optional[int] = typer.Option(None),
    output: Optional[str] = typer.Option(None),
    fmt: str = typer.Option("text"),
):
    result = generate_quiz(
        document=document, query=query, filters=_parse_filters(filters), count=count, k=k
    )
    _emit(result, output, fmt)


@app.command("flashcards")
def flashcards_cmd(
    document: Optional[str] = typer.Option(None),
    query: Optional[str] = typer.Option(None),
    filters: Optional[str] = typer.Option(None),
    count: Optional[int] = typer.Option(None),
    k: Optional[int] = typer.Option(None),
    output: Optional[str] = typer.Option(None),
    fmt: str = typer.Option("text"),
):
    result = generate_flashcards(
        document=document, query=query, filters=_parse_filters(filters), count=count, k=k
    )
    _emit(result, output, fmt)


if __name__ == "__main__":
    app()
