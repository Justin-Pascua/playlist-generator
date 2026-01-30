from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter

from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.mysql import JSON

from typing import List, Optional

from ..database import get_db
from ..schema import (SongSummary, SongCreate, SongMergeRequest, SongSplinterRequest,
                      CanonicalCreate, CanonicalUpdate, 
                      AltNameCreate, AltNameResponse, AltNameUpdate, 
                      VideoCreate, VideoResponse,
                      DefaultResponse)
from ..models import Canonical, AltName, Video
from .. import auth_utils

router = APIRouter(
    prefix = "/songs",
    tags = ['Songs']
)

# SONG SUMMARIES
@router.get("/", response_model = List[SongSummary])
async def get_all_songs(query_str: str = None,
                        db: Session = Depends(get_db),
                        current_user = Depends(auth_utils.get_current_user)):
    """
    Returns all songs in the database, and (optionally) alternate titles plus video links
    """

    # choose fields to fetch
    stmt = (select(
        Canonical.title.label('title'),
        Canonical.id.label('id'),
        Canonical.user_id.label('user_id'),
        Video.link.label("link"),
        func.coalesce(
                func.JSON_ARRAYAGG(
                    func.JSON_OBJECT(
                        "id", AltName.id,
                        "title", AltName.title,
                    )
                ),
                func.cast("[]", JSON),
            ).label("alt_names"),
        )
        .join(Video, Canonical.id == Video.canonical_name_id, isouter = True)
        .join(AltName, Canonical.id == AltName.canonical_id, isouter = True)
        .group_by(Canonical.id, Canonical.title, Video.link))
    
    if query_str is not None:
        stmt = stmt.having(func.sum(AltName.title == query_str) > 0)

    result = db.execute(stmt).all() 
    
    if not result:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = 'No songs found')

    return result

@router.get("/{id}", response_model = SongSummary)
async def get_song(id: int, 
                   db: Session = Depends(get_db),
                   current_user = Depends(auth_utils.get_current_user)):
    """
    Returns a specified song from the database, including its alt names and link
    """
    stmt = (select(
        Canonical.title.label('title'),
        Canonical.id.label('id'),
        Canonical.user_id.label('user_id'),
        Video.link.label("link"),
        func.coalesce(
                func.JSON_ARRAYAGG(
                    func.JSON_OBJECT(
                        "id", AltName.id,
                        "title", AltName.title,
                    )
                ),
                func.cast("[]", JSON),
            ).label("alt_names"),
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

@router.post("/", status_code = status.HTTP_201_CREATED, response_model = SongSummary, response_model_exclude_defaults = True)
async def create_song(new_song: SongCreate, 
                      db: Session = Depends(get_db),
                      current_user = Depends(auth_utils.get_current_user)):
    """
    Inserts a song title into the canonical_names table and alt_names table
    """
    # check that title doesn't already exist as either a canonical name or alt name
    stmt = (select(Canonical.title)
            .where(Canonical.title == new_song.title)
            .where(Canonical.user_id == current_user.id))
    result = db.execute(stmt).scalar()
    if result is not None:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT,
                            detail = "Provided name already exists in canonical_names")
    
    stmt = (select(AltName.title)
            .where(AltName.title == new_song.title)
            .where(AltName.user_id == current_user.id))
    result = db.execute(stmt).scalar()
    if result is not None:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT,
                            detail = "Provided name already exists in alt_names")

    # if no conflicts, then can safely add title to both canonical_names and alt_names
    created_canonical = Canonical(user_id = current_user.id, **new_song.model_dump())
    db.add(created_canonical)
    db.commit()
    db.refresh(created_canonical)

    created_alt = AltName(user_id = current_user.id, canonical_id = created_canonical.id, **new_song.model_dump())
    db.add(created_alt)
    db.commit()
    db.refresh(created_alt)

    response = {'id': created_canonical.id,
                'title': created_canonical.title,
                'alt_names': [{'id': created_alt.id, 'title': created_alt.title}]
                }

    return response

@router.post("/merges", status_code = status.HTTP_200_OK, response_model = SongSummary | DefaultResponse)
async def merge_songs(merge_details: SongMergeRequest,
                      db: Session = Depends(get_db),
                      current_user = Depends(auth_utils.get_current_user)):
    """
    Merge multiple (up to 5) song resources
    """
    # throw exception if too many elements provided in canonical_ids field 
    # this is done to protect the system against adversial calls and clumsy users from themselves 
    if len(merge_details.canonical_ids) > 5:
        raise HTTPException(status_code = status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail = {
                                "message": "At most 5 ids can be provided at once",
                                "max_allowed": 5,
                                "provided": len(merge_details)
                            })
    
    # check that each song exists and that user has access
    for id in merge_details.canonical_ids:
        result = db.execute(select(Canonical).where(Canonical.id == id)).scalars().first()
        if not result:
            raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                                detail = {
                                    "message": "Song not found",
                                    "invalid_id": id
                                })
        
        if result.user_id != current_user.id:
            raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                                detail = {
                                    "message": "You do not have access to this song",
                                    "invalid_id": id
                                })
    
    # remove id of main song from list of ids for cleaner logic in the following operations
    if merge_details.priority_id in merge_details.canonical_ids:
        # not using .remove() in case there are multiple instances that need to be removed
        merge_details.canonical_ids = [id for id in merge_details.canonical_ids if id != merge_details.priority_id]
    
    # if list is now empty, then user just tried to merge a song with just itself. Exit and return 200
    if len(merge_details.canonical_ids) == 0:
        return {"detail": "No changes were made as the provided id's point to the same resource"}

    # reassign alt names to all point to canonical_title of main song
    stmt = (update(AltName)
            .where(AltName.canonical_id.in_(merge_details.canonical_ids))
            .values(canonical_id = merge_details.priority_id))
    db.execute(stmt)
    db.commit()

    # delete canonical name of side
    song = db.scalar(select(Canonical).where(Canonical.id.in_(merge_details.canonical_ids)))
    db.delete(song)
    db.commit()

    # delete video of side
    video = db.scalar(select(Video).where(Video.canonical_name_id.in_(merge_details.canonical_ids)))
    if video:
        db.delete(video)
        db.commit()
    
    stmt = (select(
        Canonical.title.label('title'),
        Canonical.id.label('id'),
        Canonical.user_id.label('user_id'),
        Video.link.label("link"),
        func.coalesce(
                func.JSON_ARRAYAGG(
                    func.JSON_OBJECT(
                        "id", AltName.id,
                        "title", AltName.title,
                    )
                ),
                func.cast("[]", JSON),
            ).label("alt_names"),
        )
        .where(Canonical.id == merge_details.priority_id)
        .join(Video, Canonical.id == Video.canonical_name_id, isouter = True)
        .join(AltName, Canonical.id == AltName.canonical_id, isouter = True)
        .group_by(Canonical.id, Canonical.title, Video.link))
    
    result = db.execute(stmt).first()

    return result

@router.post("/splinters", status_code = status.HTTP_201_CREATED, response_model = SongSummary)
async def splinter_song(splinter_details: SongSplinterRequest,
                        db: Session = Depends(get_db),
                        current_user = Depends(auth_utils.get_current_user)):
    """
    Create a new song resource by de-coupling a specified alt name from its current song resource
    """
    # take an alt name of a specified song, and turn it into its own song
    stmt = (select(AltName.id, 
               AltName.user_id,
               AltName.canonical_id,
               AltName.title.label('title'),
               Canonical.title.label('canonical_title'),)
            .join(Canonical, Canonical.id == AltName.canonical_id)
            .where(AltName.id == splinter_details.alt_name_id))
    current_alt_name = db.execute(stmt).first()

    if not current_alt_name:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = "Specified alt name does not exist")
    
    if current_alt_name.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = "You do not have access to this alt name")

    # do not allow splintering if specified alt name is same as the canonical name it points to
    if current_alt_name.title == current_alt_name.canonical_title:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT,
                            detail = "Cannot splinter this alt name because it is the canonical name of the overlying song resource")
    

    new_canonical = Canonical(title = current_alt_name.title, user_id = current_user.id)
    db.add(new_canonical)
    
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code = status.HTTP_409_CONFLICT,
                            detail = "This alt name already exists as a canonical name")
    
    db.refresh(new_canonical)

    updated_alt_name = db.scalar(select(AltName).where(AltName.id == splinter_details.alt_name_id))
    updated_alt_name.canonical_id = new_canonical.id
    
    db.commit()

    response = {
        "id": new_canonical.id,
        "title": new_canonical.title,
        "alt_names": [{'id': updated_alt_name.id, 'title': updated_alt_name.title}]
    }
    
    return response

@router.delete("/{id}", status_code = status.HTTP_204_NO_CONTENT)
async def delete_song(id: int,
                      db: Session = Depends(get_db),
                      current_user = Depends(auth_utils.get_current_user)):
    """
    Delete a song resource, including its alternate titles and song link
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

# CANONICAL NAMES
@router.patch("/{id}")
async def update_canonical_name(id: int,
                                new_canonical: CanonicalUpdate,
                                db: Session = Depends(get_db),
                                current_user = Depends(auth_utils.get_current_user)):
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

# VIDEOS
@router.put("/{canonical_id}/videos", response_model = VideoResponse)
async def upsert_video(canonical_id: int, new_video: VideoCreate,
                       response: Response,
                       db: Session = Depends(get_db),
                       current_user = Depends(auth_utils.get_current_user)):
    """
    Create or replace the video associated to canonical title
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
        video.video_title = new_video.video_title
        video.channel_name = new_video.channel_name

        response.status_code = status.HTTP_200_OK
    # otherwise, insert into db
    else:
        video = Video(
            id = new_video.id,
            canonical_name_id = canonical_id, 
            link = root + new_video.id, 
            user_id = current_user.id,
            video_title = new_video.video_title,
            channel_name = new_video.video_title
            )
        db.add(video)
        
        response.status_code = status.HTTP_201_CREATED

    db.commit()
    db.refresh(video)

    return video

@router.get("/{canonical_id}/videos", response_model = VideoResponse)
async def get_video(canonical_id: int,
                   db: Session = Depends(get_db),
                   current_user = Depends(auth_utils.get_current_user)):
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
                            detail = f"No video found")
    
    return result

@router.delete("/{canonical_id}/videos")
async def delete_video(canonical_id: int,
                      db: Session = Depends(get_db),
                      current_user = Depends(auth_utils.get_current_user)):
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
                            detail = f"Video not found")
    if video.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this video")
    
    db.delete(video)
    db.commit()

    return Response(status_code = status.HTTP_204_NO_CONTENT)

