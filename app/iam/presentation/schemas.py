from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    lastname: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    institute_name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=50)


class SigninRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class SigninResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class SignoutRequest(BaseModel):
    refresh_token: str


class SignoutResponse(BaseModel):
    message: str
