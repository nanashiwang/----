from fastapi import APIRouter, Depends, HTTPException, status

from ..auth.dependencies import get_current_user
from ..auth.jwt_handler import create_access_token, hash_password, verify_password
from ..models.user import ProfileUpdate, TokenOut, UserCreate, UserLogin, UserOut
from ..services.user_service import UserService

router = APIRouter(prefix="/api/auth", tags=["认证"])


def _get_service():
    from ..app import get_sqlite_client
    return UserService(get_sqlite_client())


def _build_user_out(user: dict) -> UserOut:
    return UserOut(
        id=user["id"],
        username=user["username"],
        role=user["role"],
        is_active=bool(user["is_active"]),
        created_at=str(user["created_at"]) if user["created_at"] else None,
        last_login=str(user["last_login"]) if user["last_login"] else None,
    )


@router.post("/login", response_model=TokenOut)
async def login(data: UserLogin):
    svc = _get_service()
    user = svc.get_by_username(data.username)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已禁用")

    svc.update_last_login(user["id"])
    user = svc.get_by_id(user["id"])

    token = create_access_token({"sub": user["username"], "role": user["role"], "uid": user["id"]})
    return TokenOut(access_token=token, user=_build_user_out(user))


@router.post("/register", response_model=UserOut)
async def register(data: UserCreate):
    svc = _get_service()
    if svc.get_by_username(data.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    try:
        user_id = svc.create_user(data.username, hash_password(data.password), "user")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserOut(id=user_id, username=data.username, role="user", is_active=True)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: dict = Depends(get_current_user)):
    svc = _get_service()
    user = svc.get_by_id(current_user.get("uid"))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return _build_user_out(user)


@router.put("/me", response_model=TokenOut)
async def update_me(data: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    svc = _get_service()
    user = svc.get_by_id(current_user.get("uid"))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if not verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误")

    update_data = {}
    next_username = user["username"]

    if data.username is not None:
        username = data.username.strip()
        if not username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名不能为空")
        if username != user["username"]:
            existing = svc.get_by_username(username)
            if existing and existing["id"] != user["id"]:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
            update_data["username"] = username
            next_username = username

    if data.new_password is not None:
        new_password = data.new_password.strip()
        if not new_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能为空")
        if verify_password(new_password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与当前密码相同")
        update_data["password_hash"] = hash_password(new_password)

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未检测到需要更新的内容")

    svc.update_user(user["id"], update_data)
    updated_user = svc.get_by_id(user["id"])
    token = create_access_token({
        "sub": next_username,
        "role": updated_user["role"],
        "uid": updated_user["id"],
    })
    return TokenOut(access_token=token, user=_build_user_out(updated_user))
