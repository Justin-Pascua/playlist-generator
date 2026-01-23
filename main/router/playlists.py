from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session

from typing import Literal
import datetime

from ..database import get_db
from ..schema import PlaylistCreate
from .. import oauth2
from ..youtube import PlaylistEditor, get_yt_service
from ..models import Playlist

router = APIRouter(
    prefix = "/playlists",
    tags = ['Playlists']
)

@router.get("/")
async def get_all_playlists():
    
    return {"message": "no playlists so far"}

@router.post("/")
async def create_playlist(payload: PlaylistCreate,
                          db: Session = Depends(get_db),
                          yt_service = Depends(get_yt_service),
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
    
    print("e")

    # create empty playlist through YouTube Data API
    playlist_editor = PlaylistEditor(mode = 'create_new', 
                                     title = payload.title, 
                                     privacy_status = payload.privacy_status)

    # add new playlist to database
    new_playlist = Playlist(
        playlist_title = playlist_editor.title,
        link = playlist_editor.link,
        user_id = current_user.id,
        created_at = datetime.date.today()
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