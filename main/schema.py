from typing import List, Optional, Literal, Tuple
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

# VIDEO
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
class SongCreate(CanonicalCreate):
    """
    User input for creating a new song resource (same as CanonicalCreate)
    """
    pass

class SongResponseBase(BaseModel):
    """
    API response for sending song titles
    """
    id: int
    title: str

class SongSummary(SongResponseBase):
    """
    API response for sending additional song details
    """
    link: Optional[str] | None = None
    alt_names: Optional[List[SongResponseBase | None]] = [None]

class SongMergeRequest(BaseModel):
    """
    User input for merging songs
    """
    canonical_ids: List[int]        # identifies song to merge
    priority_id: int                # identifies which song takes priority for canonical_name and video

class SongSplinterRequest(BaseModel):
    """
    user input for splintering a song with a target alt name
    """
    alt_name_id: int 

# PLAYLIST
class PlaylistResponse(BaseModel):
    """
    API response after creating a playlist 
    """
    id: str
    playlist_title: str
    link: str
    created_at: datetime

class PlaylistCreate(BaseModel):
    """
    User input for creating a playlist
    """
    title: str
    privacy_status: Literal["public", "private", "unlisted"] = "private"

class PlaylistEdit(BaseModel):
    title: str
    privacy_status: Literal["public", "private", "unlisted", None] = None

class PlaylistItemInsert(BaseModel):
    """
    User input for inserting item into a playlist
    """
    video_id: str
    pos: int | None = None

class PlaylistItemReplace(BaseModel):
    """
    User input for replacing a video inside a playlist
    """
    video_id: str
    pos: int

class PlaylistItemMove(BaseModel):
    """
    User input for changing a video's position within a playlist
    """
    init_pos: int
    target_pos: int

class PlaylistItemEdit(BaseModel):
    """
    User input for editing a playlist
    """
    mode: Literal["Replace", "Move"]
    details: PlaylistItemReplace | PlaylistItemMove 

class PlaylistItemRemove(BaseModel):
    """
    User input for removing a video from a playlist
    """
    pos: int