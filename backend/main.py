from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import db
from .indexes import create_indexes
from .routers import router as api_router

app = FastAPI()
app.include_router(api_router)

static_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
async def startup_event():
    await create_indexes()


@app.get("/")
async def root():
    return FileResponse(static_dir / "index.html")

@app.get("/db-test")
async def db_test():
    collections = await db.list_collection_names()

    return {
        "database": "connected",
        "collections": collections
    }
