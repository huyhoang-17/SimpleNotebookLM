import os
import sys
from pathlib import Path

# Ensure project root is on sys.path when run with `streamlit run`
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Force CPU-only mode before torch/accelerate/pynvml are imported.
# On CPU-only hosts (Streamlit Cloud), accelerate calls pynvml.nvmlInit() which
# raises "Found no NVIDIA driver" — suppressing CUDA entirely prevents that path.
# GPU users who set CUDA_VISIBLE_DEVICES in their own environment won't be affected
# because their env var is set before the process starts, making these no-ops.
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import streamlit as st

from src.indexing import save_and_ingest_pdf
from src.learning import generate_flashcards, generate_quiz
from src.learning import summarize as summarize_learning
from src.rag import answer, fetch_all_chunks

GLOBAL_CSS = """
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { height: 50px; padding: 0px 16px; }
    .stButton > button { width: 100%; }
</style>
"""


def _list_documents() -> list[dict]:
    try:
        chunks = fetch_all_chunks()
    except Exception:
        return []
    seen: dict[str, str] = {}
    for chunk in chunks:
        doc_id = chunk.metadata.document_id
        if doc_id not in seen:
            seen[doc_id] = chunk.metadata.filename
    return [{"document_id": k, "filename": v} for k, v in seen.items()]


def _build_filters(filenames: list[str], page: int | None) -> dict | None:
    f: dict = {}
    if filenames:
        f["filenames"] = filenames
    if page is not None:
        f["page"] = page
    return f or None


def _sidebar() -> tuple[list[str], int | None]:
    st.sidebar.title("Bộ lọc")

    docs = _list_documents()
    filenames = [d["filename"] for d in docs]
    selected = st.sidebar.multiselect("Chọn tài liệu", filenames)

    page_val = st.sidebar.number_input("Trang (0 = tất cả)", min_value=0, value=0, step=1)
    page = int(page_val) if page_val > 0 else None

    st.sidebar.markdown("---")
    st.sidebar.subheader("Tải tài liệu lên")
    uploaded = st.sidebar.file_uploader("Chọn file PDF", type=["pdf"])
    if uploaded and st.sidebar.button("Tải lên"):
        with st.sidebar.spinner("Đang tải lên và index..."):
            try:
                result = save_and_ingest_pdf(uploaded.getvalue(), uploaded.name)
                st.sidebar.success(f"Đã index {result['chunks_indexed']} chunks")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Tải lên thất bại: {e}")

    return selected, page


def _tab_chat(filenames: list[str], page: int | None) -> None:
    st.header("Hỏi đáp")
    question = st.text_input("Câu hỏi của bạn", placeholder="Nhập câu hỏi...")
    k = st.slider("Số chunks truy xuất", min_value=1, max_value=20, value=5)

    if st.button("Hỏi", key="btn_ask") and question:
        with st.spinner("Đang trả lời..."):
            try:
                result = answer(question, k=k, filters=_build_filters(filenames, page))
                st.markdown(result.answer)
                if result.citations:
                    with st.expander("Nguồn trích dẫn"):
                        for c in result.citations:
                            st.write(f"**{c.source_marker}**: {c.filename}, trang {c.page}")
            except Exception as e:
                st.error(f"Lỗi: {e}")


def _tab_summary(filenames: list[str], page: int | None) -> None:
    st.header("Tóm tắt")
    query = st.text_input("Truy vấn tóm tắt (để trống = tóm tắt toàn bộ)")

    if st.button("Tóm tắt", key="btn_summary"):
        with st.spinner("Đang tóm tắt..."):
            try:
                result = summarize_learning(
                    query=query or None,
                    filters=_build_filters(filenames, page),
                )
                st.markdown(result.summary)
                if result.key_points:
                    st.subheader("Điểm chính")
                    for kp in result.key_points:
                        st.markdown(f"- {kp}")
                if result.citations:
                    with st.expander("Nguồn"):
                        for c in result.citations:
                            st.write(f"**{c.source_marker}**: {c.filename}, trang {c.page}")
            except Exception as e:
                st.error(f"Lỗi: {e}")


def _tab_quiz(filenames: list[str], page: int | None) -> None:
    st.header("Quiz")
    query = st.text_input("Chủ đề quiz (để trống = từ toàn bộ tài liệu)")
    count = st.slider("Số câu hỏi", min_value=1, max_value=20, value=8)

    if st.button("Tạo Quiz", key="btn_quiz"):
        with st.spinner("Đang tạo quiz..."):
            try:
                result = generate_quiz(
                    query=query or None,
                    count=count,
                    filters=_build_filters(filenames, page),
                )
                st.session_state["quiz_data"] = result
            except Exception as e:
                st.error(f"Lỗi: {e}")
                st.session_state["quiz_data"] = None
            st.session_state["quiz_answers"] = {}

    quiz_result = st.session_state.get("quiz_data")
    if quiz_result:
        for i, item in enumerate(quiz_result.items, 1):
            st.subheader(f"Câu {i}: {item.question}")
            choice = st.radio(
                "Chọn đáp án:", item.options,
                key=f"quiz_q{i}", index=None,
            )
            if choice is not None and st.button(f"Kiểm tra câu {i}", key=f"check_{i}"):
                idx = item.options.index(choice)
                if idx == item.correct_index:
                    st.success("Đúng!")
                else:
                    st.error(f"Sai. Đáp án đúng: {item.options[item.correct_index]}")
                st.info(f"Giải thích: {item.explanation}")


def _tab_flashcards(filenames: list[str], page: int | None) -> None:
    st.header("Flashcards")
    query = st.text_input("Chủ đề flashcard (để trống = từ toàn bộ tài liệu)")
    count = st.slider("Số flashcard", min_value=1, max_value=30, value=15)

    if st.button("Tạo Flashcards", key="btn_fc"):
        with st.spinner("Đang tạo flashcards..."):
            try:
                result = generate_flashcards(
                    query=query or None,
                    count=count,
                    filters=_build_filters(filenames, page),
                )
                st.session_state["fc_cards"] = result.cards
                st.session_state["fc_index"] = 0
                st.session_state["fc_show_back"] = False
            except Exception as e:
                st.error(f"Lỗi: {e}")

    cards = st.session_state.get("fc_cards", [])
    if cards:
        idx = st.session_state.get("fc_index", 0) % len(cards)
        card = cards[idx]

        st.markdown(f"### Thẻ {idx + 1} / {len(cards)}")
        st.markdown(f"**Câu hỏi:** {card.front}")

        if st.button("Lật thẻ", key="fc_flip"):
            st.session_state["fc_show_back"] = not st.session_state.get("fc_show_back", False)

        if st.session_state.get("fc_show_back"):
            st.success(f"**Trả lời:** {card.back}")
            if card.hint:
                st.caption(f"Gợi ý: {card.hint}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Trước", key="fc_prev"):
                st.session_state["fc_index"] = (idx - 1) % len(cards)
                st.session_state["fc_show_back"] = False
                st.rerun()
        with col2:
            if st.button("Tiếp →", key="fc_next"):
                st.session_state["fc_index"] = (idx + 1) % len(cards)
                st.session_state["fc_show_back"] = False
                st.rerun()


def run():
    st.set_page_config(page_title="RAG Learning System", layout="wide")
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    filenames, page = _sidebar()
    tabs = st.tabs(["Hỏi đáp", "Tóm tắt", "Quiz", "Flashcards"])

    for tab, fn in zip(tabs, [_tab_chat, _tab_summary, _tab_quiz, _tab_flashcards]):
        with tab:
            fn(filenames, page)


run()