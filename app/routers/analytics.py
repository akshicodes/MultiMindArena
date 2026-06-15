from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from ..database import db
from ..models import analytics_model

router = APIRouter()

@router.post("/analytics", status_code=201)
async def create_analytics(analytics: analytics_model.AnalyticsModel):
    result = await db.analytics.insert_one(jsonable_encoder(analytics))
    return {"inserted_id": str(result.inserted_id)}

@router.get("/analytics")
async def get_analytics():
    analytics = await db.analytics.find().to_list(length=100)
    for item in analytics:
        item["_id"] = str(item["_id"])
    return analytics
