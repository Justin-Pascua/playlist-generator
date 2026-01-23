from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from googleapiclient.discovery import Resource

from typing import Literal, List
import datetime

from ..database import get_db
from ..schema import PlaylistCreate, PlaylistResponse
from ..models import Playlist
from .. import oauth2, youtube

router = APIRouter(
    prefix = "/playlists",
    tags = ['Playlists']
)

@router.get("/", response_model = List[PlaylistResponse])
async def get_all_playlists(db: Session = Depends(get_db),
                            current_user = Depends(oauth2.get_current_user)):
    
    stmt = select(Playlist).where(Playlist.user_id == current_user.id)
    result = db.execute(stmt).scalars().all()

    if not result:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = 'No playlists found')
    
    return result

@router.get("/{id}", response_model = PlaylistResponse)
async def get_playlist(id: str, db: Session = Depends(get_db),
                       current_user = Depends(oauth2.get_current_user)):
    
    playlist = db.execute(select(Playlist)
                         .where(Playlist.id == id)).scalars().first()

    if not playlist:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Playlist not found")

    if playlist.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do have access to this playlist")

    return playlist

@router.post("/")
async def create_playlist(payload: PlaylistCreate, db: Session = Depends(get_db),
                          yt_service: Resource = Depends(youtube.get_yt_service),
                          current_user = Depends(oauth2.get_current_user)):
    # user should pass a date and a list of song strings
    # query db to check for matches
    # for all matches, get links
    # for all non-matches, 
    #   - search YouTube API
    #   - get link to top result (might need to think about this more carefully later)
    # 
    # gather all links and send request to YouTube API to create a playlist
    # add links and titles of unknown songs to database

    # request = yt_service.playlists().insert(
    #     part = "id,snippet,status",
    #     body = {"snippet": {"title": payload.title},
    #             "status": {"privacyStatus": payload.privacy_status}
    #             })
    # response = request.execute()
    response = youtube.create_blank_playlist(payload, yt_service)

    root = "https://youtube.com/playlist?list="

    new_playlist = Playlist(
        id = response['id'],
        playlist_title = payload.title,
        link = root + response['id'],
        user_id = current_user.id,
        created_at = datetime.datetime.now()
    )

    db.add(new_playlist)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    
    db.refresh(new_playlist)
    return new_playlist


    return 

@router.post("/playlists/{id}")
async def edit_playlist():
    # allow user to add, remove, replace, or change order of videos in playlist
    # add query param that indicates whether or not to reflect those changes in the song preference database
    return {"message": "editted playlist"}

@router.delete("/{id}")
async def delete_playlist(id: str, db: Session = Depends(get_db),
                          current_user = Depends(oauth2.get_current_user)):
    playlist = db.scalar(select(Playlist).where(Playlist.id == id))
    if not playlist:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this playlist")
    
    db.delete(playlist)
    db.commit()

    return Response(status_code = status.HTTP_204_NO_CONTENT)