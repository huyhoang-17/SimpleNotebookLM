from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from . import service
from .deps import get_current_user, require_role
from .models import User
from .security import create_access_token, verify_password


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    @classmethod
    def from_model(cls, user: User) -> "UserPublic":
        return cls(
            id=user.id or 0,
            username=user.username,
            email=user.email,
            role=user.role,
            active=user.active,
            created_at=user.created_at,
            last_login=user.last_login,
        )


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


class AdminCreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: Optional[str] = None
    role: str = "user"


class AdminUpdateUserRequest(BaseModel):
    role: Optional[str] = None
    active: Optional[bool] = None
    email: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


router = APIRouter()


@router.post("/auth/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    try:
        user = service.create_user(
            username=req.username,
            password=req.password,
            email=req.email,
            role="user",
            active=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return UserPublic.from_model(user)


@router.post("/auth/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = service.authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password, or account disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=user.username, role=user.role)
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return UserPublic.from_model(user)


@router.post("/auth/change-password")
def change_password(req: ChangePasswordRequest, user: User = Depends(get_current_user)):
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    service.change_password(user.id, req.new_password)
    return {"status": "ok"}


# ---------- Admin endpoints ----------

@router.get("/admin/users", response_model=list[UserPublic])
def admin_list_users(_admin: User = Depends(require_role("admin"))):
    return [UserPublic.from_model(u) for u in service.list_users()]


@router.post("/admin/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def admin_create_user(req: AdminCreateUserRequest, _admin: User = Depends(require_role("admin"))):
    try:
        user = service.create_user(
            username=req.username,
            password=req.password,
            email=req.email,
            role=req.role,
            active=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return UserPublic.from_model(user)


@router.patch("/admin/users/{user_id}", response_model=UserPublic)
def admin_update_user(
    user_id: int,
    req: AdminUpdateUserRequest,
    admin: User = Depends(require_role("admin")),
):
    target = service.get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if req.active is False and target.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot disable themselves",
        )
    if req.role is not None and req.role != "admin" and target.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot demote themselves",
        )

    try:
        if req.role is not None:
            target = service.set_role(target.id, req.role)
        if req.active is not None:
            target = service.set_active(target.id, req.active)
        if req.email is not None:
            target = service.update_email(target.id, req.email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return UserPublic.from_model(target)


@router.post("/admin/users/{user_id}/reset-password")
def admin_reset_password(
    user_id: int,
    req: ResetPasswordRequest,
    _admin: User = Depends(require_role("admin")),
):
    target = service.get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        service.change_password(target.id, req.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"status": "ok"}


@router.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin: User = Depends(require_role("admin"))):
    target = service.get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot delete themselves",
        )
    service.delete_user(user_id)
    return {"status": "ok"}
