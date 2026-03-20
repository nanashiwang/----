from fastapi import APIRouter, Depends, Query
from typing import Optional

from ..auth.dependencies import get_current_user

router = APIRouter(prefix="/api/review", tags=["复盘分析"])


@router.get("")
async def list_reviews(limit: int = Query(10, le=50), _=Depends(get_current_user)):
    from ..app import get_mongo_client
    mongo = get_mongo_client()
    briefs = list(mongo.get_collection("review_briefs").find().sort("date", -1).limit(limit))
    for b in briefs:
        b["_id"] = str(b["_id"])
        if b.get("date"):
            b["date"] = str(b["date"])
    return briefs


@router.get("/sqlite")
async def list_review_records(
    date: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    _=Depends(get_current_user)
):
    from ..app import get_sqlite_client
    db = get_sqlite_client()
    with db.get_connection() as conn:
        if date:
            rows = conn.execute(
                "SELECT * FROM reviews WHERE date = ? ORDER BY id DESC LIMIT ?",
                (date, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM reviews ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]
