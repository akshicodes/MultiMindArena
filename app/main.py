from fastapi import FastAPI

from .database import db
from .indexes import create_indexes
from .routers import router as api_router

app = FastAPI()
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    await create_indexes()

@app.get("/")
async def root():
    return {"message": "MultiMind Arena Running"}

@app.get("/db-test")
async def db_test():
    collections = await db.list_collection_names()

    return {
        "database": "connected",
        "collections": collections
    }
