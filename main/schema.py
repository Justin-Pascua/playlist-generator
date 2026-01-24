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


# CANONICAL
class CanonicalCreate(BaseModel):
    """
    User input for inserting a canonical song title
    """
    title: str

class CanonicalUpdate(BaseModel):
    """
    User input for updating a canonical song title
    """
    title: str

# ALT NAME
class AltNameCreate(BaseModel):
    """
    User input for inserting an alternate song title
    """
    title: str
    canonical_id: int = 0   # 0 is canonical_id of unassigned songs

class AltNameUpdate(BaseModel):
    """
    User input for updating an alternate song title
    """
    title: Optional[str] = None
    canonical_id: Optional[int] = None
class AltNameResponse(BaseModel):
    """
    API response for sending alt names
    """
    id: int
    title: str
    canonical_id: int

# SONG LINK
class VideoCreate(BaseModel):
    """
    User input for inserting a song link
    """
    id: str
    video_title: str
    channel_name: str

class VideoResponse(BaseModel):
    """
    API response for sending song link
    """
    id: str
    video_title: str
    channel_name: str
    link: str


# FULL SONG RESOURCE
class SongResponseBase(BaseModel):
    """
    API response for sending song titles
    """
    id: int
    title: str

class SongSummary(SongResponseBase):
    """
    API response for sending song details
    """
    link: Optional[str] | None = None
    alt_names: Optional[List[str | None]] = [None]

# PLAYLIST
class PlaylistResponse(BaseModel):
    id: str
    playlist_title: str
    link: str
    created_at: datetime

class PlaylistCreate(BaseModel):
    title: str
    privacy_status: Literal["public", "private", "unlisted"] = "private"