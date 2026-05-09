from pathlib import Path
from typing import Literal

ExportFormat = Literal["text", "md", "json"]


def _to_markdown(model) -> str:
    from .schemas import FlashcardSet, QuizSet, RagAnswer, Summary

    lines = []
    if isinstance(model, RagAnswer):
        lines.append(f"# Answer\n\n{model.answer}\n")
        if model.citations:
            lines.append("## Sources\n")
            for c in model.citations:
                lines.append(f"- {c.source_marker}: {c.filename}, trang {c.page}")
    elif isinstance(model, Summary):
        lines.append(f"# Tóm tắt\n\n{model.summary}\n")
        if model.key_points:
            lines.append("\n## Điểm chính\n")
            for kp in model.key_points:
                lines.append(f"- {kp}")
        if model.citations:
            lines.append("\n## Nguồn\n")
            for c in model.citations:
                lines.append(f"- {c.source_marker}: {c.filename}, trang {c.page}")
    elif isinstance(model, QuizSet):
        lines.append("# Quiz\n")
        for i, item in enumerate(model.items, 1):
            lines.append(f"\n## Câu {i}: {item.question}\n")
            for j, opt in enumerate(item.options):
                marker = "**" if j == item.correct_index else ""
                lines.append(f"{chr(65 + j)}. {marker}{opt}{marker}")
            lines.append(f"\n*Giải thích: {item.explanation}*")
    elif isinstance(model, FlashcardSet):
        lines.append("# Flashcards\n")
        for i, card in enumerate(model.cards, 1):
            lines.append(f"\n## Thẻ {i}\n\n**Q:** {card.front}\n\n**A:** {card.back}")
            if card.hint:
                lines.append(f"\n*Gợi ý: {card.hint}*")
    else:
        lines.append(str(model))

    return "\n".join(lines) + "\n"


def export(model, *, fmt="text", output=None):
    if fmt == "json":
        text = model.model_dump_json(indent=2) + "\n"
    elif fmt in {"text", "md"}:
        text = _to_markdown(model)
    else:
        raise ValueError(f"Unknown fmt '{fmt}'. Expected 'text' | 'md' | 'json'.")

    if output is None:
        return text

    output = Path(output) if not isinstance(output, Path) else output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return output
