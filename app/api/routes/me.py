from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import MeResponse
from app.services import auth as auth_service


router = APIRouter()


@router.get("/me", response_model=MeResponse, tags=["me"])
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return auth_service.build_me_response(current_user)
