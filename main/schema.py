from typing import List
from pydantic import BaseModel, ValidationError

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


