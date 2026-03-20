from fastapi import APIRouter, HTTPException, status
from datetime import datetime

from ..models.user import UserLogin, UserCreate, UserOut, TokenOut
from ..auth.jwt_handler import hash_password, verify_password, create_access_token
from ..services.user_service import UserService

router = APIRouter(prefix="/api/auth", tags=["认证"])


def _get_service():
    from ..app import get_sqlite_client
    return UserService(get_sqlite_client())


@router.post("/login", response_model=TokenOut)
async def login(data: UserLogin):
    svc = _get_service()
    user = svc.get_by_username(data.username)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已禁用")

    svc.update_last_login(user["id"])

    token = create_access_token({"sub": user["username"], "role": user["role"], "uid": user["id"]})
    return TokenOut(
        access_token=token,
        user=UserOut(
            id=user["id"], username=user["username"], role=user["role"],
            is_active=bool(user["is_active"]),
            created_at=str(user["created_at"]) if user["created_at"] else None,
            last_login=str(user["last_login"]) if user["last_login"] else None,
        )
    )


@router.post("/register", response_model=UserOut)
async def register(data: UserCreate):
    svc = _get_service()
    if svc.get_by_username(data.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    user_id = svc.create_user(data.username, hash_password(data.password), "user")
    return UserOut(id=user_id, username=data.username, role="user", is_active=True)
