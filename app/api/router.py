from fastapi import APIRouter

from app.api.routes import auth, classrooms, exercises, me, sessions, students


api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(me.router)
api_router.include_router(classrooms.router, tags=["classrooms"])
api_router.include_router(students.router, tags=["students"])
api_router.include_router(exercises.router, tags=["exercises"])
api_router.include_router(sessions.router, tags=["sessions"])
