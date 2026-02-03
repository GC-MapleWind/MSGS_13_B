from pydantic import BaseModel


class CharacterBase(BaseModel):
    name: str
    detail_txt: str | None = None
    level: int
    job: str
    server: str
    avatar_url: str | None = None


class CharacterResponse(CharacterBase):
    id: int

    model_config = {"from_attributes": True}


class CharacterDetailResponse(CharacterResponse):
    pass
