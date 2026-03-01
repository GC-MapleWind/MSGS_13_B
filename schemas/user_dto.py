from pydantic import BaseModel, Field


class UserBase(BaseModel):
    student_id: str = Field(validation_alias="username")
    name: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str


class KakaoLoginResponse(BaseModel):
    is_new_user: bool
    register_token: str | None = None
    access_token: str | None = None
    token_type: str | None = "bearer"


class KakaoRegisterRequest(BaseModel):
    register_token: str
    student_id: str
    nickname: str


class TokenData(BaseModel):
    student_id: str | None = None
