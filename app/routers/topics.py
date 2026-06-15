from fastapi import APIRouter, Query
from fastapi.encoders import jsonable_encoder

from ..database import db
from ..models import llm_config_model, topics_model

router = APIRouter(prefix="/topics", tags=["topics"])

@router.get("/")
async def list_topics(category: str | None = Query(None), limit: int = Query(20, ge=1, le=100)):
    filters = {}
    if category:
        filters["category"] = category

    cursor = db.topics.find(filters).limit(limit)
    topics = await cursor.to_list(length=limit)
    for topic in topics:
        topic["_id"] = str(topic["_id"])
    return {"topics": topics}


@router.post("/", status_code=201)
async def create_topic(topic: topics_model.TopicModel):
    result = await db.topics.insert_one(jsonable_encoder(topic))
    return {"inserted_id": str(result.inserted_id), "topic": topic.topic}


@router.get("/random")
async def get_random_topic(category: str | None = Query(None)):
    pipeline = []
    if category:
        pipeline.append({"$match": {"category": category}})
    pipeline.append({"$sample": {"size": 1}})

    docs = await db.topics.aggregate(pipeline).to_list(length=1)
    if not docs:
        return {"topic": None}
    topic = docs[0]
    topic["_id"] = str(topic["_id"])
    return topic


@router.post("/api/llm-configs", status_code=201)
async def create_llm_config(config: llm_config_model.LLMConfigModel):
    result = await db.llm_configs.insert_one(jsonable_encoder(config))
    return {"inserted_id": str(result.inserted_id)}
