from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from ..models.user import AdminUserCreate, UserOut, UserUpdate
from ..auth.dependencies import require_admin
from ..auth.jwt_handler import hash_password
from ..services.user_service import UserService

router = APIRouter(prefix="/api/users", tags=["用户管理"])


def _get_service():
    from ..app import get_sqlite_client
    return UserService(get_sqlite_client())


@router.get("", response_model=List[UserOut])
async def list_users(_=Depends(require_admin)):
    svc = _get_service()
    rows = svc.list_all()
    return [
        UserOut(
            id=r["id"], username=r["username"], role=r["role"],
            is_active=bool(r["is_active"]),
            created_at=str(r["created_at"]) if r["created_at"] else None,
            last_login=str(r["last_login"]) if r["last_login"] else None,
        )
        for r in rows
    ]


@router.post("", response_model=UserOut)
async def create_user(data: AdminUserCreate, _=Depends(require_admin)):
    svc = _get_service()
    if svc.get_by_username(data.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    try:
        user_id = svc.create_user(data.username, hash_password(data.password), data.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserOut(id=user_id, username=data.username, role=data.role, is_active=True)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, data: UserUpdate, _=Depends(require_admin)):
    svc = _get_service()
    user = svc.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    try:
        svc.update_user(user_id, data.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    user = svc.get_by_id(user_id)
    return UserOut(
        id=user["id"], username=user["username"], role=user["role"],
        is_active=bool(user["is_active"]),
        created_at=str(user["created_at"]) if user["created_at"] else None,
        last_login=str(user["last_login"]) if user["last_login"] else None,
    )


@router.delete("/{user_id}")
async def delete_user(user_id: int, _=Depends(require_admin)):
    svc = _get_service()
    svc.delete_user(user_id)
    return {"detail": "已删除"}
