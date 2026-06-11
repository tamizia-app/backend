from fastapi import APIRouter

from app.api.routes import classrooms, exercises, sessions, students


api_router = APIRouter()
api_router.include_router(classrooms.router, tags=["classrooms"])
api_router.include_router(students.router, tags=["students"])
api_router.include_router(exercises.router, tags=["exercises"])
api_router.include_router(sessions.router, tags=["sessions"])
