from fastapi import FastAPI
from app.api.routes import router as youtube_router

app = FastAPI(title="YouTube Crawler API")

app.include_router(youtube_router, prefix="/api", tags=[""])
