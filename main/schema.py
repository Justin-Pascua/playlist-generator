from typing import List, Optional, Literal
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[int] = None

class PlaylistCreate(BaseModel):
    pass

class CanonicalCreate(BaseModel):
    """
    User input for inserting a canonical song title
    """
    title: str
    user_id: int

class AltNameCreate(BaseModel):
    """
    User input for inserting an alternate song title
    """
    title: str
    user_id: int


