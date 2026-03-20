from fastapi import APIRouter, Depends, Query
from typing import Optional
import pandas as pd

from ..auth.dependencies import get_current_user

router = APIRouter(prefix="/api/recommend", tags=["推荐数据"])


@router.get("")
async def list_recommendations(
    date: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    _=Depends(get_current_user)
):
    from ..app import get_sqlite_client
    db = get_sqlite_client()
    with db.get_connection() as conn:
        if date:
            df = pd.read_sql(
                "SELECT * FROM recommendations WHERE date = ? ORDER BY weight DESC LIMIT ?",
                conn, params=(date, limit)
            )
        else:
            df = pd.read_sql(
                "SELECT * FROM recommendations ORDER BY created_at DESC LIMIT ?",
                conn, params=(limit,)
            )
    return df.to_dict("records") if not df.empty else []


@router.get("/dates")
async def list_dates(_=Depends(get_current_user)):
    from ..app import get_sqlite_client
    db = get_sqlite_client()
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM recommendations ORDER BY date DESC LIMIT 30"
        ).fetchall()
    return [r["date"] for r in rows]
