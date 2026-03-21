from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    token_type: str = "bearer"
    access_token: str
    refresh_token: str
    expires_in: int  # seconds

    user: dict

