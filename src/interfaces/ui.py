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

from src.auth import service as auth_service
from src.auth.security import verify_password
from src.auth.service import ensure_seed_admin
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


# ==========================================
# Auth helpers (session_state-based)
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


# ==========================================
# Login / Register / Sidebar
# ==========================================

def _set_user(user) -> None:
    st.session_state["user"] = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


def _login_page() -> None:
    st.set_page_config(page_title="VinLM - Đăng nhập", layout="centered")
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.title("VinLM")
    st.caption("Hệ thống RAG học tập — vui lòng đăng nhập để tiếp tục.")

    tab_login, tab_register = st.tabs(["Đăng nhập", "Đăng ký"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Tên đăng nhập", key="login_username")
            password = st.text_input("Mật khẩu", type="password", key="login_password")
            submitted = st.form_submit_button("Đăng nhập")
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
            submitted_r = st.form_submit_button("Đăng ký")
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


def _sidebar() -> tuple[list[str], int | None]:
    user = _current_user()
    st.sidebar.markdown(f"**Xin chào, `{user['username']}`** ({user['role']})")
    if st.sidebar.button("Đăng xuất", key="btn_logout"):
        for key in ("user", "quiz_data", "quiz_answers", "fc_cards", "fc_index", "fc_show_back"):
            st.session_state.pop(key, None)
        st.rerun()

    with st.sidebar.expander("Đổi mật khẩu"):
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

    st.sidebar.markdown("---")
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
                result = save_and_ingest_pdf(
                    uploaded.getvalue(),
                    uploaded.name,
                    owner_id=user["username"],
                )
                st.sidebar.success(f"Đã index {result['chunks_indexed']} chunks")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Tải lên thất bại: {e}")

    return selected, page


# ==========================================
# Feature tabs
# ==========================================

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


def _tab_guide() -> None:
    st.header("Hướng dẫn sử dụng")
    guide_md = _load_user_guide()
    st.markdown(guide_md)

    st.markdown("---")
    st.subheader("Hỏi nhanh về cách dùng")
    user_q = st.text_input(
        "Nhập câu hỏi về cách sử dụng (ví dụ: 'hướng dẫn sử dụng notebook')",
        key="guide_chat_input",
    )
    if st.button("Gửi", key="btn_guide_ask") and user_q:
        if _is_guide_request(user_q):
            st.markdown(guide_md)
        else:
            st.info(
                "Tôi chỉ trả lời các câu hỏi về cách sử dụng ứng dụng ở tab này. "
                "Hãy thử gõ \"hướng dẫn sử dụng notebook\". "
                "Nếu bạn muốn hỏi về nội dung tài liệu, vui lòng dùng tab **Hỏi đáp**."
            )


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


# ==========================================
# Admin tab — manage users
# ==========================================

def _tab_admin_users() -> None:
    st.header("Quản lý user")
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
    with st.form("admin_create_user"):
        c_username = st.text_input("Tên đăng nhập", key="adm_new_username")
        c_email = st.text_input("Email (tùy chọn)", key="adm_new_email")
        c_password = st.text_input("Mật khẩu", type="password", key="adm_new_password")
        c_role = st.selectbox("Role", ["user", "admin"], index=0, key="adm_new_role")
        c_submit = st.form_submit_button("Tạo user")
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

def run():
    ensure_seed_admin()

    if _current_user() is None:
        _login_page()
        return

    st.set_page_config(page_title="RAG Learning System", layout="wide")
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    filenames, page = _sidebar()

    tab_labels = ["Hỏi đáp", "Tóm tắt", "Quiz", "Flashcards", "Hướng dẫn"]
    if _is_admin():
        tab_labels.append("Quản lý user")

    tabs = st.tabs(tab_labels)

    with tabs[0]:
        _tab_chat(filenames, page)
    with tabs[1]:
        _tab_summary(filenames, page)
    with tabs[2]:
        _tab_quiz(filenames, page)
    with tabs[3]:
        _tab_flashcards(filenames, page)
    with tabs[4]:
        _tab_guide()
    if _is_admin():
        with tabs[5]:
            _tab_admin_users()


run()
