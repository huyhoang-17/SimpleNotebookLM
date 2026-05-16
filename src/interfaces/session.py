"""Cookie-backed session persistence using JWT.

Streamlit's st.session_state lives in the WebSocket session — F5 wipes it.
This module stores a JWT in a browser cookie so users stay logged in across
reloads. DB is the source of truth for active/role (we don't trust JWT role).
"""

import logging
import os
import time
from typing import Optional

import streamlit as st
from streamlit_cookies_controller import CookieController

from ..auth import service as auth_service
from ..auth.models import User
from ..auth.security import create_access_token, decode_token
from ..config import settings

logger = logging.getLogger(__name__)

COOKIE_NAME = "vinlm_token"
VERIFY_CACHE_SECONDS = 60

_SECRET_WARNING_LOGGED = False


def _is_https() -> bool:
    if os.environ.get("STREAMLIT_SHARING_MODE"):
        return True
    if os.environ.get("STREAMLIT_SERVER_HEADLESS", "").lower() == "true":
        return True
    if os.environ.get("HOME", "").startswith("/mount/"):
        return True
    return False


def _get_controller() -> CookieController:
    ctrl = st.session_state.get("_cookie_ctrl")
    if ctrl is None:
        ctrl = CookieController(key="vinlm_cookie_ctrl")
        st.session_state["_cookie_ctrl"] = ctrl
    return ctrl


def default_secret_warning() -> bool:
    global _SECRET_WARNING_LOGGED
    is_default = settings.jwt_secret == "change-me-in-production"
    if is_default and not _SECRET_WARNING_LOGGED:
        logger.warning(
            "RAG_JWT_SECRET is the default value 'change-me-in-production'. "
            "Set a strong secret in .env before deploying — tokens issued with "
            "the default secret can be forged by anyone reading the source."
        )
        _SECRET_WARNING_LOGGED = True
    return is_default


def _user_to_session_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


def issue_session(user: User) -> None:
    token = create_access_token(subject=user.username, role=user.role)
    max_age = settings.jwt_expires_min * 60
    ctrl = _get_controller()
    try:
        ctrl.set(
            COOKIE_NAME,
            token,
            max_age=max_age,
            same_site="lax",
            secure=_is_https(),
        )
    except TypeError:
        ctrl.set(COOKIE_NAME, token)
    st.session_state["_user_verified_at"] = time.time()


def _clear_cookie_only() -> None:
    ctrl = _get_controller()
    try:
        ctrl.remove(COOKIE_NAME)
    except Exception:
        try:
            ctrl.set(COOKIE_NAME, "", max_age=0)
        except Exception:
            pass


def clear_session() -> None:
    _clear_cookie_only()
    for key in (
        "user",
        "_user_verified_at",
        "quiz_data",
        "quiz_answers",
        "fc_cards",
        "fc_index",
        "fc_show_back",
        "selected_docs",
        "nav_choice",
    ):
        st.session_state.pop(key, None)


def restore_session() -> Optional[dict]:
    default_secret_warning()

    cached_user = st.session_state.get("user")
    verified_at = st.session_state.get("_user_verified_at", 0)
    if cached_user and (time.time() - verified_at) < VERIFY_CACHE_SECONDS:
        return cached_user

    ctrl = _get_controller()
    try:
        token = ctrl.get(COOKIE_NAME)
    except Exception:
        token = None

    if not token:
        if cached_user:
            st.session_state.pop("user", None)
            st.session_state.pop("_user_verified_at", None)
        return None

    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        _clear_cookie_only()
        st.session_state.pop("user", None)
        st.session_state.pop("_user_verified_at", None)
        st.session_state["_logout_reason"] = (
            "Phiên đăng nhập đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại."
        )
        return None

    db_user = auth_service.get_user_by_username(payload["sub"])
    if db_user is None or not db_user.active:
        _clear_cookie_only()
        st.session_state.pop("user", None)
        st.session_state.pop("_user_verified_at", None)
        st.session_state["_logout_reason"] = (
            "Tài khoản đã bị vô hiệu hóa hoặc xóa. Vui lòng liên hệ admin."
        )
        return None

    user_dict = _user_to_session_dict(db_user)
    st.session_state["user"] = user_dict
    st.session_state["_user_verified_at"] = time.time()
    return user_dict
