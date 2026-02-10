from pydantic import BaseModel

class UserBase(BaseModel):
    username: str
    name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

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
    username: str | None = None
