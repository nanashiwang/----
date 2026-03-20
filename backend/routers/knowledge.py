from fastapi import APIRouter, Depends, Query
from typing import Optional

from ..auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


@router.get("/hot")
async def list_hot_knowledge(limit: int = Query(20, le=100), _=Depends(get_current_user)):
    from ..app import get_mongo_client
    mongo = get_mongo_client()
    items = list(mongo.get_collection("hot_knowledge").find().sort("confidence", -1).limit(limit))
    for item in items:
        item["_id"] = str(item["_id"])
        if item.get("created_at"):
            item["created_at"] = str(item["created_at"])
        if item.get("last_tested"):
            item["last_tested"] = str(item["last_tested"])
    return items


@router.get("/cold/{agent_name}")
async def list_cold_knowledge(agent_name: str, _=Depends(get_current_user)):
    from ..app import get_mongo_client
    mongo = get_mongo_client()
    items = list(mongo.get_collection(f"cold_knowledge_{agent_name}").find())
    for item in items:
        item["_id"] = str(item["_id"])
        if item.get("created_at"):
            item["created_at"] = str(item["created_at"])
    return items


@router.delete("/hot/{knowledge_id}")
async def delete_hot_knowledge(knowledge_id: str, _=Depends(require_admin)):
    from ..app import get_mongo_client
    from bson import ObjectId
    mongo = get_mongo_client()
    mongo.get_collection("hot_knowledge").delete_one({"_id": ObjectId(knowledge_id)})
    return {"detail": "已删除"}
