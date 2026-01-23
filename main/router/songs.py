from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter

from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.mysql import JSON

from typing import List, Optional

from ..database import get_db
from ..schema import (SongSummary,
                      CanonicalCreate, CanonicalUpdate, 
                      AltNameCreate, AltNameResponse, AltNameUpdate, 
                      VideoCreate, VideoResponse)
from ..models import Canonical, AltName, Video
from .. import oauth2

router = APIRouter(
    prefix = "/songs",
    tags = ['Songs']
)

# SONG SUMMARIES
@router.get("/", response_model = List[SongSummary], response_model_exclude_defaults = True)
async def get_all_songs(get_links: bool = False, get_alts: bool = False, 
                        db: Session = Depends(get_db),
                        current_user = Depends(oauth2.get_current_user)):
    """
    Returns all songs in the database, and (optionally) alternate titles plus video links
    """

    # choose fields to fetch
    select_cols = [Canonical.title.label("title"), Canonical.id.label("id")]
    if get_links:
        select_cols.append(Video.link.label("song_link"))
    if get_alts:
        select_cols.append(func.json_arrayagg(AltName.title).cast(JSON).label("alt_names"))

    # build query statement
    stmt = select(*select_cols).where(Canonical.user_id == current_user.id)
    if get_links:
        stmt = stmt.join(Video, Canonical.id == Video.canonical_name_id, isouter = True)
    if get_alts:
        stmt = (stmt
                .join(AltName, Canonical.id == AltName.canonical_id, isouter = True)
                .group_by(Canonical.id))

    result = db.execute(stmt).all() 
    
    if not result:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = 'No songs found')

    return result

@router.get("/{id}", response_model = SongSummary)
async def get_song(id: int, 
                   db: Session = Depends(get_db),
                   current_user = Depends(oauth2.get_current_user)):
    """
    Returns a specified song from the database, including its alt names and link
    """
    stmt = (select(
        Canonical.title.label('title'),
        Canonical.id.label('id'),
        Canonical.user_id.label('user_id'),
        Video.link.label("song_link"),
        func.json_arrayagg(AltName.title).label("alt_names").cast(JSON).label("alt_names")
        )
        .where(Canonical.id == id)
        .join(Video, Canonical.id == Video.canonical_name_id, isouter = True)
        .join(AltName, Canonical.id == AltName.canonical_id, isouter = True)
        .group_by(Canonical.id, Canonical.title, Video.link))
    
    result = db.execute(stmt).first()
    # check if song exists
    if not result:
        raise(HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Song not found"))

    # check if user has access to song
    # if not, raise HTTP exception
    if result.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this song")


    return result

# CANONICAL NAMES
@router.post("/", status_code = status.HTTP_201_CREATED)
async def create_song(new_canonical: CanonicalCreate, 
                      db: Session = Depends(get_db),
                      current_user = Depends(oauth2.get_current_user)):
    """
    Inserts a song title into the canonical_names table
    """
    created_canonical = Canonical(user_id = current_user.id, **new_canonical.model_dump())
    db.add(created_canonical)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, 
                            detail = "Song already exists in your database")
    
    db.refresh(created_canonical)
    return created_canonical

@router.patch("/{id}")
async def update_canonical_name(id: int,
                                new_canonical: CanonicalUpdate,
                                db: Session = Depends(get_db),
                                current_user = Depends(oauth2.get_current_user)):
    """
    Update the canonical title of a song
    """

    song = db.scalar(select(Canonical).where(Canonical.id == id))

    if not song:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Song not found")
    
    if song.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this song")
    
    song.title = new_canonical.title

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code = status.HTTP_409_CONFLICT,
                            detail = f"New name conflicts with an existing song")
    
    db.refresh(song)
    return song

@router.delete("/{id}", status_code = status.HTTP_204_NO_CONTENT)
async def delete_song(id: int,
                      db: Session = Depends(get_db),
                      current_user = Depends(oauth2.get_current_user)):
    """
    Delete a song, including its alternate titles and song link
    """
    song = db.scalar(select(Canonical).where(Canonical.id == id))
    if not song:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Song not found")
    
    if song.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this song") 

    db.delete(song)
    db.commit()

    return Response(status_code = status.HTTP_204_NO_CONTENT)

# VIDEOS
@router.put("/{canonical_id}/video")
async def upsert_video(canonical_id: int, new_video: VideoCreate,
                      db: Session = Depends(get_db),
                      current_user = Depends(oauth2.get_current_user)):
    """
    Create or replace video associated to canonical title
    """
    song = db.scalar(select(Canonical).where(Canonical.id == canonical_id))
    if not song:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Song not found")
    
    if song.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this song")
    
    video = db.scalar(select(Video)
                     .where(Video.canonical_name_id == canonical_id)
                     .where(Video.user_id == current_user.id))
    
    root = 'http://youtu.be/'

    # if link exists, then update
    if video:
        video.id = new_video.id
        video.link = root + new_video.id
    # otherwise, insert into db
    else:
        video = Video(
            id = new_video.id,
            canonical_name_id = canonical_id, 
            user_id = current_user.id, 
            link = root + new_video.id)
        db.add(video)

    db.commit()
    db.refresh(video)

    return video

@router.get("/{canonical_id}/video", response_model = VideoResponse)
async def get_video(canonical_id: int,
                   db: Session = Depends(get_db),
                   current_user = Depends(oauth2.get_current_user)):
    """
    Get video info for a song
    """
    song = db.scalar(select(Canonical).where(Canonical.id == canonical_id))
    if not song:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Song not found")
    
    if song.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this song")
    
    result = db.scalar(select(Video).where(Video.canonical_name_id == canonical_id))

    if not result:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"No link found")
    
    return result

@router.delete("/{canonical_id}/video")
async def delete_video(canonical_id: int,
                      db: Session = Depends(get_db),
                      current_user = Depends(oauth2.get_current_user)):
    """
    Delete video item from database
    """

    song = db.scalar(select(Canonical).where(Canonical.id == canonical_id))
    if not song:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Song not found")
    if song.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this song")
    
    video = db.scalar(select(Video).where(Video.canonical_name_id == canonical_id))
    if not video:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Link not found")
    if video.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this link")
    
    db.delete(video)
    db.commit()

    return Response(status_code = status.HTTP_204_NO_CONTENT)

