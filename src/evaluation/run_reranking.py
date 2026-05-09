import json
from pathlib import Path

import pandas as pd
from sentence_transformers import CrossEncoder

from ..config import settings
from ..rag import ANSWER_TEMPLATE, format_citations, render_prompt, retrieve
from ..schemas import RagAnswer
from ..llm import invoke_llm
from .ragas_evaluator import run_evaluation

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


def answer_with_reranker(
    question: str,
    collection_name: str,
    reranker: CrossEncoder,
    initial_k: int = 15,
    rerank_k: int = 5,
    filters: dict | None = None,
) -> RagAnswer:
    # Giai đoạn 1: Truy xuất thô (initial_k)
    chunks = retrieve(question, k=initial_k, filters=filters, collection_name=collection_name)

    if not chunks:
        return RagAnswer(
            question=question,
            answer="Tôi không có đủ thông tin trong ngữ cảnh được cung cấp để trả lời.",
        )

    # Giai đoạn 2: Tính điểm tương quan chéo bằng Cross-Encoder
    scores = reranker.predict([[question, chunk.text] for chunk in chunks])
    for chunk, score in zip(chunks, scores):
        chunk.score = float(score)

    # Xếp hạng lại và lọc ra các đoạn liên quan nhất (rerank_k)
    reranked = sorted(chunks, key=lambda c: c.score, reverse=True)[:rerank_k]

    # Đưa ngữ cảnh đã lọc vào prompt cho LLM
    prompt = render_prompt(ANSWER_TEMPLATE, question=question, chunks=reranked)
    text = invoke_llm(prompt)

    return RagAnswer(
        question=question,
        answer=text.strip(),
        citations=format_citations(reranked),
        chunks=reranked,
    )


def summary_metrics(df: pd.DataFrame) -> dict[str, float]:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    return {col: round(float(df[col].mean()), 4) for col in numeric_cols}


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def run_reranking_evaluation(
    test_cases: list[dict],
    output_dir: Path | None = None,
    initial_k: int = 15,
    rerank_k: int = 5,
) -> dict:
    if output_dir is None:
        output_dir = Path("evaluation_results/reranking")

    collection_name = settings.qdrant_collection
    reranker = CrossEncoder(RERANKER_MODEL)

    result_out: dict = {
        "reranker_model": RERANKER_MODEL,
        "initial_k": initial_k,
        "rerank_k": rerank_k,
        "summary_metrics": {},
    }

    try:
        def answer_fn(q: str) -> RagAnswer:
            return answer_with_reranker(
                q,
                collection_name=collection_name,
                reranker=reranker,
                initial_k=initial_k,
                rerank_k=rerank_k,
            )

        result = run_evaluation(test_cases, answer_fn=answer_fn, llm_provider="vllm")
        df = result.to_pandas()
        result_out["summary_metrics"] = summary_metrics(df)

    except Exception as exc:
        result_out["error"] = str(exc)

    write_json(output_dir / "reranking_results.json", result_out)
    print(f"Results saved to {output_dir}")
    return result_out


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    sample_test_cases = [
        {"question": "Nội dung chính của tài liệu là gì?", "ground_truth": ""},
    ]
    run_reranking_evaluation(sample_test_cases)
