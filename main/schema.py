from typing import List
from pydantic import BaseModel, ValidationError

class PlaylistCreateRequest(BaseModel):
    date: str
    songs: List[str]

class PlaylistModifyRequest(BaseModel):
    pass