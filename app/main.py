from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.iam.application.exceptions import IAMException
from app.core.config import get_settings
from app.iam.presentation.routes import router as iam_router
from app.school.application.exceptions.school_exceptions import SchoolException
from app.school.presentation.teacher_routes import teacher_router
from app.school.presentation.classroom_routes import classroom_router
from app.school.presentation.student_routes import student_router
from app.schemas.common import HealthResponse


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Backend MVP para captura y análisis de evidencias de lectoescritura. "
        "No realiza diagnóstico clínico y solo entrega indicadores de apoyo."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(iam_router, prefix=settings.api_v1_prefix)
app.include_router(teacher_router, prefix=settings.api_v1_prefix)
app.include_router(classroom_router, prefix=settings.api_v1_prefix)
app.include_router(student_router, prefix=settings.api_v1_prefix)


@app.exception_handler(IAMException)
def iam_exception_handler(request: Request, exc: IAMException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(SchoolException)
def school_exception_handler(request: Request, exc: SchoolException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.app_name, environment=settings.environment)

