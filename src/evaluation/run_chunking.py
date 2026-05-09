import json
from pathlib import Path

import pandas as pd

from ..config import settings
from ..indexing import ingest
from ..rag import answer
from ..schemas import RagAnswer
from ..store import get_embeddings
from .chunking_strategies import ChunkingStrategy, build_all_strategies
from .ragas_evaluator import run_evaluation


def summary_metrics(df: pd.DataFrame) -> dict[str, float]:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    return {col: round(float(df[col].mean()), 4) for col in numeric_cols}


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _evaluate_strategy(
    strategy: ChunkingStrategy, output_dir: Path, test_cases: list[dict]
) -> dict:
    collection_name = f"{settings.qdrant_collection}__{strategy.strategy_id}"
    chunk_count = ingest(recreate=True, collection_name=collection_name, chunker=strategy.chunker)

    result_out: dict = {
        "strategy_id": strategy.strategy_id,
        "chunk_count": chunk_count,
        "params": strategy.params,
        "summary_metrics": {},
    }

    try:
        def answer_fn(q: str) -> RagAnswer:
            return answer(q, collection_name=collection_name)

        result = run_evaluation(test_cases, answer_fn=answer_fn, llm_provider="vllm")
        df = result.to_pandas()
        result_out["summary_metrics"] = summary_metrics(df)

    except Exception as exc:
        result_out["error"] = str(exc)

    write_json(output_dir / f"{strategy.strategy_id}.json", result_out)
    return result_out


def run_chunking_evaluation(
    test_cases: list[dict],
    output_dir: Path | None = None,
) -> list[dict]:
    if output_dir is None:
        output_dir = Path("evaluation_results/chunking")

    embeddings = get_embeddings()
    strategies = build_all_strategies(embeddings=embeddings)

    results = []
    for strategy in strategies:
        print(f"Evaluating strategy: {strategy.strategy_id}")
        result = _evaluate_strategy(strategy, output_dir, test_cases)
        results.append(result)

    write_json(output_dir / "summary.json", results)
    print(f"Results saved to {output_dir}")
    return results


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

    sample_test_cases = [
        {"question": "Nội dung chính của tài liệu là gì?", "ground_truth": ""},
    ]
    run_chunking_evaluation(sample_test_cases)
