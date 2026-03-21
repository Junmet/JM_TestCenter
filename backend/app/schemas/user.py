from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=72)


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool

