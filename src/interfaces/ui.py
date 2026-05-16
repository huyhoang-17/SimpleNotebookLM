import html
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path when run with `streamlit run`
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Force CPU-only mode before torch/accelerate/pynvml are imported.
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import streamlit as st

# Bridge Streamlit Cloud secrets into os.environ.
try:
    _streamlit_secrets = dict(st.secrets) if hasattr(st, "secrets") else {}
except Exception:
    _streamlit_secrets = {}
for _k, _v in _streamlit_secrets.items():
    if isinstance(_v, str) and _k not in os.environ:
        os.environ[_k] = _v

from src.auth import service as auth_service
from src.auth.security import verify_password
from src.auth.service import ensure_seed_admin
from src.indexing import save_and_ingest_pdf
from src.learning import generate_flashcards, generate_quiz
from src.learning import summarize as summarize_learning
from src.rag import answer, fetch_all_chunks


# ==========================================
# Theme / CSS
# ==========================================

GLOBAL_CSS = """
<style>
:root {
    --bg: #F3F4F6;
    --card: #FFFFFF;
    --border: #E5E7EB;
    --text: #111827;
    --muted: #6B7280;
    --subtle: #9CA3AF;
    --accent: #F97316;
    --accent-soft: #FFF7ED;
    --accent-strong: #C2410C;
    --accent-grad: linear-gradient(135deg, #FB923C, #EA580C);
}

/* ===== App background ===== */
.stApp { background: var(--bg); }
header[data-testid="stHeader"] { background: transparent; }
.main .block-container { max-width: 1080px; padding-top: 2rem; padding-bottom: 4rem; }

/* ===== Sidebar ===== */
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid var(--border); }
[data-testid="stSidebar"] > div:first-child { padding-top: 0.6rem; }

.vinlm-brand {
    display: flex; align-items: center; gap: 0.7rem;
    padding: 0.5rem 0.3rem 1rem 0.3rem;
    border-bottom: 1px solid #F3F4F6;
    margin-bottom: 0.8rem;
}
.vinlm-brand .logo-box {
    width: 38px; height: 38px; border-radius: 11px;
    background: var(--accent-grad);
    display: flex; align-items: center; justify-content: center;
    color: white; font-weight: 700; font-size: 1.05rem;
    box-shadow: 0 4px 10px rgba(249, 115, 22, 0.25);
}
.vinlm-brand .brand-text { line-height: 1.15; }
.vinlm-brand .brand-name { font-weight: 700; font-size: 1.08rem; color: var(--text); }
.vinlm-brand .brand-sub { color: var(--subtle); font-size: 0.78rem; }

.section-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--subtle);
    margin: 1.1rem 0 0.4rem 0.15rem;
    font-weight: 600;
}

/* Radio styled as nav list */
[data-testid="stSidebar"] [role="radiogroup"] { gap: 0.15rem; }
[data-testid="stSidebar"] [role="radiogroup"] > label {
    padding: 0.5rem 0.65rem;
    border-radius: 9px;
    cursor: pointer;
    transition: background 120ms, color 120ms;
    margin: 0;
    border: 1px solid transparent;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover { background: #F9FAFB; }
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
    background: var(--accent-soft);
    border-color: #FDD7B0;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {
    color: var(--accent-strong) !important;
    font-weight: 600;
}
[data-testid="stSidebar"] [role="radiogroup"] label p {
    margin: 0; font-size: 0.93rem; color: var(--text); font-weight: 500;
}
/* Hide the round radio indicator — we use the whole row as a nav item */
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none !important; }

/* User card at bottom of sidebar */
.user-card {
    margin-top: 1.5rem;
    padding: 0.85rem;
    border-radius: 12px;
    background: #F9FAFB;
    border: 1px solid #F3F4F6;
    display: flex; align-items: center; gap: 0.7rem;
}
.user-card .avatar {
    width: 38px; height: 38px; border-radius: 50%;
    background: var(--accent-grad);
    color: white; font-weight: 700; font-size: 0.95rem;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.user-card .info { line-height: 1.25; min-width: 0; flex: 1; }
.user-card .username {
    font-weight: 600; font-size: 0.93rem; color: var(--text);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.user-card .role { font-size: 0.78rem; color: var(--muted); text-transform: capitalize; }

/* ===== Main area: page header & greeting ===== */
.page-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    margin-bottom: 1.4rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border);
}
.page-header .titles .page-title {
    font-size: 1.5rem; font-weight: 600;
    margin: 0; color: var(--text);
}
.page-header .titles .page-subtitle {
    color: var(--muted); font-size: 0.92rem;
    margin-top: 0.2rem;
}
.report-pill {
    display: inline-block; padding: 0.45rem 0.85rem;
    border: 1px solid var(--border); border-radius: 999px;
    background: white; color: var(--muted);
    font-size: 0.82rem; font-weight: 500;
    text-decoration: none;
}

.greeting { text-align: center; margin: 1.2rem 0 1.8rem 0; }
.greeting h2 {
    font-size: 1.7rem; font-weight: 700;
    color: var(--text); margin: 0 0 0.35rem 0;
}
.greeting p {
    color: var(--muted); font-size: 0.93rem;
    max-width: 540px; margin: 0 auto;
}

/* ===== Cards ===== */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    border: 1px solid var(--border) !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    background: var(--card);
}

/* ===== Inputs ===== */
.stTextArea textarea, .stTextInput input {
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
    background: #FFFFFF;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.15) !important;
}

/* ===== Buttons ===== */
.stButton > button {
    border-radius: 10px;
    border: 1px solid var(--border);
    background: #FFFFFF;
    color: #374151;
    font-weight: 500;
    transition: all 120ms;
}
.stButton > button:hover {
    background: #F9FAFB; border-color: #D1D5DB;
}
.stButton > button[kind="primary"] {
    background: var(--accent); border-color: var(--accent); color: white;
}
.stButton > button[kind="primary"]:hover {
    background: #EA580C; border-color: #EA580C;
}

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
    border-radius: 12px;
    border: 1px dashed #D1D5DB;
    background: #F9FAFB;
}

/* Expanders */
details[data-testid="stExpander"] {
    border-radius: 12px;
    border: 1px solid var(--border);
}

/* Sliders accent */
[data-testid="stSlider"] [role="slider"] { background: var(--accent) !important; }

/* Toast */
[data-testid="stToast"] { border-radius: 12px; }

/* ===== Login page ===== */
.login-wrap {
    max-width: 420px; margin: 3rem auto 1rem auto;
    text-align: center;
}
.login-wrap .logo-box {
    width: 56px; height: 56px; border-radius: 16px;
    background: var(--accent-grad);
    color: white; font-weight: 700; font-size: 1.5rem;
    display: inline-flex; align-items: center; justify-content: center;
    box-shadow: 0 6px 14px rgba(249, 115, 22, 0.25);
    margin-bottom: 1rem;
}
.login-wrap h1 { margin: 0; font-size: 1.7rem; color: var(--text); }
.login-wrap p { color: var(--muted); margin-top: 0.3rem; }
</style>
"""


# ==========================================
# Auth helpers
# ==========================================

def _current_user() -> dict | None:
    return st.session_state.get("user")


def _is_admin() -> bool:
    user = _current_user()
    return bool(user and user.get("role") == "admin")


def _owner_filter() -> dict:
    user = _current_user()
    if not user or user.get("role") == "admin":
        return {}
    return {"owner_id": user["username"]}


# ==========================================
# Document/filter helpers
# ==========================================

def _list_documents() -> list[dict]:
    try:
        chunks = fetch_all_chunks(filters=_owner_filter() or None)
    except Exception:
        return []
    seen: dict[str, dict] = {}
    for chunk in chunks:
        doc_id = chunk.metadata.document_id
        if doc_id not in seen:
            seen[doc_id] = {
                "document_id": doc_id,
                "filename": chunk.metadata.filename,
                "owner_id": chunk.metadata.owner_id,
            }
    return list(seen.values())


def _build_filters(filenames: list[str], page: int | None) -> dict | None:
    f: dict = dict(_owner_filter())
    if filenames:
        f["filenames"] = filenames
    if page is not None:
        f["page"] = page
    return f or None


def _doc_checkbox_filter(docs: list[dict]) -> list[str]:
    """Render filter checkboxes in the current container. Returns selected filenames."""
    if not docs:
        st.caption("Chưa có tài liệu. Hãy upload PDF ở mục bên dưới.")
        st.session_state["selected_docs"] = set()
        return []

    filenames_set = {d["filename"] for d in docs}
    selected_docs: set[str] = st.session_state.get("selected_docs", set()) & filenames_set
    st.session_state["selected_docs"] = selected_docs

    col_all, col_none = st.columns(2)
    with col_all:
        if st.button("Chọn tất cả", key="btn_sel_all"):
            st.session_state["selected_docs"] = set(filenames_set)
            for d in docs:
                st.session_state[f"doc_cb_{d['document_id']}"] = True
            st.rerun()
    with col_none:
        if st.button("Bỏ chọn", key="btn_sel_none"):
            st.session_state["selected_docs"] = set()
            for d in docs:
                st.session_state[f"doc_cb_{d['document_id']}"] = False
            st.rerun()

    container = st.container(height=240) if len(docs) > 6 else st.container()

    new_selected: set[str] = set()
    with container:
        for d in docs:
            cb_key = f"doc_cb_{d['document_id']}"
            if cb_key not in st.session_state:
                st.session_state[cb_key] = d["filename"] in selected_docs
            checked = st.checkbox(d["filename"], key=cb_key)
            if checked:
                new_selected.add(d["filename"])

    st.session_state["selected_docs"] = new_selected
    return sorted(new_selected)


# ==========================================
# Reusable layout helpers
# ==========================================

def _brand_html() -> str:
    return (
        '<div class="vinlm-brand">'
        '<div class="logo-box">V</div>'
        '<div class="brand-text">'
        '<div class="brand-name">VinLM</div>'
        '<div class="brand-sub">RAG Learning</div>'
        '</div>'
        '</div>'
    )


def _user_card_html(user: dict) -> str:
    initial = (user.get("username") or "?")[0].upper()
    username = html.escape(user.get("username") or "")
    role = html.escape(user.get("role") or "")
    return (
        '<div class="user-card">'
        f'<div class="avatar">{html.escape(initial)}</div>'
        '<div class="info">'
        f'<div class="username">{username}</div>'
        f'<div class="role">{role}</div>'
        '</div>'
        '</div>'
    )


def _page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="page-header">'
        f'<div class="titles">'
        f'<div class="page-title">{html.escape(title)}</div>'
        f'<div class="page-subtitle">{html.escape(subtitle)}</div>'
        f'</div>'
        f'<a class="report-pill" href="https://github.com/huyhoang-17/SimpleNotebookLM/issues" target="_blank">Báo lỗi</a>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _greeting() -> None:
    user = _current_user() or {}
    name = user.get("username", "")
    st.markdown(
        f'<div class="greeting">'
        f'<h2>Xin chào, {html.escape(name)} 👋</h2>'
        f'<p>Đặt câu hỏi, tóm tắt nội dung, tạo quiz hay flashcards từ tài liệu PDF của bạn.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _set_user(user) -> None:
    st.session_state["user"] = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


# ==========================================
# Login page
# ==========================================

def _login_page() -> None:
    st.set_page_config(page_title="VinLM - Đăng nhập", layout="centered")
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="login-wrap">'
        '<div class="logo-box">V</div>'
        '<h1>VinLM</h1>'
        '<p>Hệ thống RAG học tập — vui lòng đăng nhập để tiếp tục.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["Đăng nhập", "Đăng ký"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Tên đăng nhập", key="login_username")
            password = st.text_input("Mật khẩu", type="password", key="login_password")
            submitted = st.form_submit_button("Đăng nhập", type="primary")
        if submitted:
            user = auth_service.authenticate(username.strip(), password)
            if user is None:
                st.error("Sai tên đăng nhập/mật khẩu hoặc tài khoản đã bị vô hiệu hóa.")
            else:
                _set_user(user)
                st.success(f"Xin chào, {user.username}!")
                st.rerun()

    with tab_register:
        with st.form("register_form", clear_on_submit=False):
            r_username = st.text_input("Tên đăng nhập", key="reg_username")
            r_email = st.text_input("Email (tùy chọn)", key="reg_email")
            r_password = st.text_input("Mật khẩu (≥6 ký tự)", type="password", key="reg_password")
            r_confirm = st.text_input("Xác nhận mật khẩu", type="password", key="reg_confirm")
            submitted_r = st.form_submit_button("Đăng ký", type="primary")
        if submitted_r:
            if r_password != r_confirm:
                st.error("Mật khẩu xác nhận không khớp.")
            else:
                try:
                    auth_service.create_user(
                        username=r_username.strip(),
                        password=r_password,
                        email=(r_email.strip() or None),
                        role="user",
                    )
                    st.success("Đăng ký thành công. Vui lòng chuyển sang tab Đăng nhập.")
                except ValueError as e:
                    st.error(f"Đăng ký thất bại: {e}")


# ==========================================
# Sidebar
# ==========================================

NAV_ITEMS_BASE = [
    "💬 Hỏi đáp",
    "✨ Tóm tắt",
    "🎯 Quiz",
    "🃏 Flashcards",
    "📖 Hướng dẫn",
]
NAV_ADMIN_ITEM = "⚙️ Quản lý user"


def _sidebar() -> tuple[str, list[str], int | None]:
    user = _current_user()

    with st.sidebar:
        st.markdown(_brand_html(), unsafe_allow_html=True)

        st.markdown('<div class="section-label">Chức năng</div>', unsafe_allow_html=True)
        items = list(NAV_ITEMS_BASE)
        if _is_admin():
            items.append(NAV_ADMIN_ITEM)
        nav = st.radio(
            "Điều hướng",
            items,
            key="nav_choice",
            label_visibility="collapsed",
        )

        st.markdown('<div class="section-label">Tài liệu</div>', unsafe_allow_html=True)
        docs = _list_documents()
        selected = _doc_checkbox_filter(docs)
        page_val = st.number_input("Trang (0 = tất cả)", min_value=0, value=0, step=1)
        page = int(page_val) if page_val > 0 else None

        st.markdown('<div class="section-label">Tải lên</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("Chọn file PDF", type=["pdf"], label_visibility="collapsed")
        if uploaded and st.button("Tải lên", key="btn_upload", type="primary"):
            with st.spinner("Đang tải lên và index..."):
                try:
                    result = save_and_ingest_pdf(
                        uploaded.getvalue(),
                        uploaded.name,
                        owner_id=user["username"],
                    )
                    st.session_state["upload_toast"] = {
                        "status": "success",
                        "filename": uploaded.name,
                        "chunks": result["chunks_indexed"],
                    }
                    st.rerun()
                except Exception as e:
                    st.session_state["upload_toast"] = {
                        "status": "error",
                        "msg": str(e),
                    }
                    st.rerun()

        with st.expander("Đổi mật khẩu"):
            old_pw = st.text_input("Mật khẩu cũ", type="password", key="cp_old")
            new_pw = st.text_input("Mật khẩu mới (≥6 ký tự)", type="password", key="cp_new")
            if st.button("Cập nhật mật khẩu", key="btn_change_pw"):
                db_user = auth_service.get_user_by_id(user["id"])
                if db_user is None or not verify_password(old_pw, db_user.password_hash):
                    st.error("Mật khẩu cũ không đúng.")
                else:
                    try:
                        auth_service.change_password(user["id"], new_pw)
                        st.success("Đã đổi mật khẩu.")
                    except ValueError as e:
                        st.error(f"Lỗi: {e}")

        st.markdown(_user_card_html(user), unsafe_allow_html=True)
        if st.button("Đăng xuất", key="btn_logout"):
            for key in (
                "user", "quiz_data", "quiz_answers",
                "fc_cards", "fc_index", "fc_show_back",
                "selected_docs", "nav_choice",
            ):
                st.session_state.pop(key, None)
            st.rerun()

    return nav, selected, page


# ==========================================
# Upload toast
# ==========================================

def _render_upload_toast() -> None:
    toast = st.session_state.pop("upload_toast", None)
    if not toast:
        return
    if toast.get("status") == "success":
        msg = f"Đã index {toast['chunks']} chunks từ '{toast['filename']}'"
        st.toast(msg, icon="✅")
        st.success(msg)
    else:
        msg = f"Tải lên thất bại: {toast.get('msg', '')}"
        st.toast(msg, icon="❌")
        st.error(msg)


# ==========================================
# Feature views
# ==========================================

def _view_chat(filenames: list[str], page: int | None) -> None:
    _page_header("Hỏi đáp", "Đặt câu hỏi dựa trên nội dung tài liệu đã upload.")
    _greeting()

    with st.container(border=True):
        question = st.text_area(
            "Câu hỏi của bạn",
            placeholder="Nhập câu hỏi...",
            height=120,
        )
        k = st.slider("Số chunks truy xuất", min_value=1, max_value=20, value=5)
        ask = st.button("Hỏi", key="btn_ask", type="primary")

    if ask and question:
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


def _view_summary(filenames: list[str], page: int | None) -> None:
    _page_header("Tóm tắt", "Tạo bản tóm tắt cho tài liệu đã chọn.")

    with st.container(border=True):
        query = st.text_area(
            "Truy vấn tóm tắt (để trống = tóm tắt toàn bộ)",
            height=120,
        )
        run_btn = st.button("Tóm tắt", key="btn_summary", type="primary")

    if run_btn:
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


def _view_quiz(filenames: list[str], page: int | None) -> None:
    _page_header("Quiz", "Tạo bộ câu hỏi trắc nghiệm từ tài liệu.")

    with st.container(border=True):
        query = st.text_area(
            "Chủ đề quiz (để trống = từ toàn bộ tài liệu)",
            height=120,
        )
        count = st.slider("Số câu hỏi", min_value=1, max_value=20, value=8)
        run_btn = st.button("Tạo Quiz", key="btn_quiz", type="primary")

    if run_btn:
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


def _view_flashcards(filenames: list[str], page: int | None) -> None:
    _page_header("Flashcards", "Học theo phương pháp thẻ ghi nhớ.")

    with st.container(border=True):
        query = st.text_area(
            "Chủ đề flashcard (để trống = từ toàn bộ tài liệu)",
            height=120,
        )
        count = st.slider("Số flashcard", min_value=1, max_value=30, value=15)
        run_btn = st.button("Tạo Flashcards", key="btn_fc", type="primary")

    if run_btn:
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


_GUIDE_PATH = Path(__file__).resolve().parent.parent / "docs" / "user_guide.md"
_GUIDE_TRIGGERS = (
    "hướng dẫn sử dụng notebook",
    "hướng dẫn sử dụng",
    "hướng dẫn dùng",
    "cách sử dụng",
    "cách dùng",
    "hướng dẫn",
    "guide",
    "help",
)


def _load_user_guide() -> str:
    try:
        return _GUIDE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "_Tài liệu hướng dẫn chưa được tạo._"


def _is_guide_request(text: str) -> bool:
    t = text.strip().lower()
    if not t:
        return False
    return any(trigger in t for trigger in _GUIDE_TRIGGERS)


def _view_guide() -> None:
    _page_header("Hướng dẫn sử dụng", "Tài liệu và mẹo dùng VinLM hiệu quả.")
    guide_md = _load_user_guide()
    with st.container(border=True):
        st.markdown(guide_md)

    st.markdown("---")
    st.subheader("Hỏi nhanh về cách dùng")
    with st.container(border=True):
        user_q = st.text_area(
            "Nhập câu hỏi về cách sử dụng (ví dụ: 'hướng dẫn sử dụng notebook')",
            key="guide_chat_input",
            height=120,
        )
        send = st.button("Gửi", key="btn_guide_ask", type="primary")

    if send and user_q:
        if _is_guide_request(user_q):
            st.markdown(guide_md)
        else:
            st.info(
                "Tôi chỉ trả lời các câu hỏi về cách sử dụng ứng dụng ở mục này. "
                "Hãy thử gõ \"hướng dẫn sử dụng notebook\". "
                "Nếu bạn muốn hỏi về nội dung tài liệu, vui lòng dùng mục **Hỏi đáp**."
            )


def _view_admin_users() -> None:
    _page_header("Quản lý user", "Tạo, sửa, vô hiệu hóa, xóa người dùng (chỉ admin).")
    current = _current_user() or {}

    users = auth_service.list_users()
    st.subheader("Danh sách user")
    if not users:
        st.info("Chưa có user nào.")
    else:
        table = [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email or "",
                "role": u.role,
                "active": u.active,
                "created_at": u.created_at.isoformat(sep=" ", timespec="seconds"),
                "last_login": u.last_login.isoformat(sep=" ", timespec="seconds") if u.last_login else "",
            }
            for u in users
        ]
        st.dataframe(table, use_container_width=True)

    st.markdown("---")
    st.subheader("Tạo user mới")
    with st.container(border=True):
        with st.form("admin_create_user"):
            c_username = st.text_input("Tên đăng nhập", key="adm_new_username")
            c_email = st.text_input("Email (tùy chọn)", key="adm_new_email")
            c_password = st.text_input("Mật khẩu", type="password", key="adm_new_password")
            c_role = st.selectbox("Role", ["user", "admin"], index=0, key="adm_new_role")
            c_submit = st.form_submit_button("Tạo user", type="primary")
    if c_submit:
        try:
            auth_service.create_user(
                username=c_username.strip(),
                password=c_password,
                email=(c_email.strip() or None),
                role=c_role,
            )
            st.success(f"Đã tạo user '{c_username}'.")
            st.rerun()
        except ValueError as e:
            st.error(f"Lỗi: {e}")

    if not users:
        return

    st.markdown("---")
    st.subheader("Sửa user")
    options = {f"{u.username} (id={u.id}, role={u.role}, active={u.active})": u for u in users}
    label = st.selectbox("Chọn user", list(options.keys()), key="adm_pick_user")
    target = options[label]
    is_self = target.id == current.get("id")

    col1, col2 = st.columns(2)
    with col1:
        new_role = st.selectbox(
            "Role mới",
            ["user", "admin"],
            index=0 if target.role == "user" else 1,
            key=f"adm_role_{target.id}",
        )
        if st.button("Cập nhật role", key=f"adm_btn_role_{target.id}"):
            if is_self and new_role != "admin":
                st.error("Admin không được tự hạ quyền của chính mình.")
            else:
                try:
                    auth_service.set_role(target.id, new_role)
                    st.success("Đã cập nhật role.")
                    st.rerun()
                except ValueError as e:
                    st.error(f"Lỗi: {e}")

        toggle_label = "Vô hiệu hóa" if target.active else "Kích hoạt"
        if st.button(toggle_label, key=f"adm_btn_active_{target.id}"):
            if is_self and target.active:
                st.error("Admin không được tự vô hiệu hóa chính mình.")
            else:
                auth_service.set_active(target.id, not target.active)
                st.success(f"Đã {toggle_label.lower()} user.")
                st.rerun()

    with col2:
        new_pw = st.text_input("Mật khẩu mới", type="password", key=f"adm_pw_{target.id}")
        if st.button("Reset mật khẩu", key=f"adm_btn_pw_{target.id}"):
            try:
                auth_service.change_password(target.id, new_pw)
                st.success("Đã reset mật khẩu.")
            except ValueError as e:
                st.error(f"Lỗi: {e}")

        if st.button("Xóa user", key=f"adm_btn_del_{target.id}"):
            if is_self:
                st.error("Admin không được tự xóa chính mình.")
            else:
                auth_service.delete_user(target.id)
                st.success(f"Đã xóa user '{target.username}'.")
                st.rerun()


# ==========================================
# Entry point
# ==========================================

VIEW_DISPATCH = {
    "💬 Hỏi đáp": "chat",
    "✨ Tóm tắt": "summary",
    "🎯 Quiz": "quiz",
    "🃏 Flashcards": "flashcards",
    "📖 Hướng dẫn": "guide",
    "⚙️ Quản lý user": "admin",
}


def run():
    ensure_seed_admin()

    if _current_user() is None:
        _login_page()
        return

    st.set_page_config(page_title="VinLM — RAG Learning", layout="wide")
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    nav, filenames, page = _sidebar()
    _render_upload_toast()

    view = VIEW_DISPATCH.get(nav, "chat")
    if view == "chat":
        _view_chat(filenames, page)
    elif view == "summary":
        _view_summary(filenames, page)
    elif view == "quiz":
        _view_quiz(filenames, page)
    elif view == "flashcards":
        _view_flashcards(filenames, page)
    elif view == "guide":
        _view_guide()
    elif view == "admin" and _is_admin():
        _view_admin_users()


run()
