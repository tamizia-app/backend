from fastapi import APIRouter

from app.api.routes import exercises, sessions


api_router = APIRouter()
api_router.include_router(exercises.router, tags=["exercises"])
api_router.include_router(sessions.router, tags=["sessions"])
