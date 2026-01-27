from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from typing import Literal, List
import datetime

from ..database import get_db
from ..schema import (PlaylistCreate, PlaylistEdit, PlaylistResponse, 
                      PlaylistItemInsert, PlaylistItemRemove, 
                      PlaylistItemMove, PlaylistItemReplace, 
                      PlaylistItemEdit, PlaylistItemResponse)
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
    # create blank playlist through YT API
    playlist_editor = youtube.PlaylistEditor(
        mode = 'create_new', 
        title = payload.title,
        privacy_status = payload.privacy_status,
        yt_service = yt_service
    )

    # record playlist details in database
    new_playlist = Playlist(
        id = playlist_editor.id,
        playlist_title = payload.title,
        link = playlist_editor.link,
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

@router.patch("/{id}")
async def edit_playlist(id: str, edit_details: PlaylistEdit,
                        db: Session = Depends(get_db),
                        yt_service: Resource = Depends(youtube.get_yt_service),
                        current_user = Depends(oauth2.get_current_user)):

    # verify that playlist exists in db and that user has access
    playlist = db.scalar(select(Playlist).where(Playlist.id == id))
    if not playlist:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this playlist")
    
    # attempt edit over YT API
    try:
        request = yt_service.playlists().update(
            part = "id,snippet,status",
            body = {
                "id": playlist.id,
                "snippet": {
                    "title": edit_details.title,
                },
                "status": {
                    "privacyStatus": edit_details.privacy_status
                }
            }
        )
        response = request.execute()
    except HttpError as e:
        raise HTTPException(status_code = e.status_code,
                            detail = e.error_details[0]['message'])

    # record changes in db
    playlist.playlist_title = edit_details.title
    db.commit()
    db.refresh(playlist)
    
    return {playlist}

@router.delete("/{id}")
async def delete_playlist(id: str, db: Session = Depends(get_db),
                          yt_service: Resource = Depends(youtube.get_yt_service),
                          current_user = Depends(oauth2.get_current_user)):

    # check that playlist exists in db and that user has access to it
    playlist = db.scalar(select(Playlist).where(Playlist.id == id))
    if not playlist:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this playlist")
    
    # delete actual playlist through YT API
    try:
        response = youtube.delete_playlist(id, yt_service)
    # if YT API throws error, convert to Exception type native to FastAPI
    except HttpError as e:
        raise HTTPException(status_code = e.status_code,
                            detail = e.error_details[0]['message'])

    db.delete(playlist)
    db.commit()

    return Response(status_code = status.HTTP_204_NO_CONTENT)

@router.get("/{id}/items", response_model = List[PlaylistItemResponse])
async def get_playlist_items(id: str,
                             db: Session = Depends(get_db),
                             yt_service: Resource = Depends(youtube.get_yt_service),
                             current_user = Depends(oauth2.get_current_user)):
    # check that playlist exists in db and that user has access to it
    playlist = db.scalar(select(Playlist).where(Playlist.id == id))
    if not playlist:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this playlist")
    
    # initialize editor
    try:
        playlist_editor = youtube.PlaylistEditor(mode = 'from_existing', playlist_id = id, yt_service = yt_service)
    except Exception as e:
        raise e

    response = playlist_editor.items

    return response

@router.post("/{id}/items", response_model = PlaylistItemResponse)
async def insert_video(id: str,
                       details: PlaylistItemInsert, 
                       db: Session = Depends(get_db),
                       yt_service: Resource = Depends(youtube.get_yt_service),
                       current_user = Depends(oauth2.get_current_user)):
    """
    Insert video into playlist
    """
    # check that playlist exists in db and that user has access to it
    playlist = db.scalar(select(Playlist).where(Playlist.id == id))
    if not playlist:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this playlist")
    
    # initialize editor
    try:
        playlist_editor = youtube.PlaylistEditor(mode = 'from_existing', playlist_id = id, yt_service = yt_service)
    except Exception as e:
        raise e

    playlist_editor.insert_video(video_id = details.video_id,
                                 pos = details.pos,
                                 yt_service = yt_service)
    
    response = playlist_editor.items[details.pos if details.pos is not None else -1]

    return response

@router.patch("/{id}/items", response_model = PlaylistItemResponse)
async def edit_playlist_item(id: str,
                             details: PlaylistItemEdit, 
                             db: Session = Depends(get_db),
                             yt_service: Resource = Depends(youtube.get_yt_service),
                             current_user = Depends(oauth2.get_current_user)):
    """
    Replace or move video within a playlist
    """
    # check that playlist exists in db and that user has access to it
    playlist = db.scalar(select(Playlist).where(Playlist.id == id))
    if not playlist:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this playlist")
    
    # initialize editor
    try:
        playlist_editor = youtube.PlaylistEditor(mode = 'from_existing', playlist_id = id, yt_service = yt_service)
    except Exception as e:
        raise e
    
    response = None
    if details.mode == "Move":
        playlist_editor.move_video(init_pos = details.sub_details.init_pos, 
                                   target_pos = details.sub_details.target_pos, 
                                   yt_service = yt_service)
        response = playlist_editor.items[details.sub_details.target_pos]
    elif details.mode == "Replace":
        playlist_editor.replace_video(video_id = details.sub_details.video_id,
                                      pos = details.sub_details.pos,
                                      yt_service = yt_service)
        response = playlist_editor.items[details.sub_details.pos]

    return response

@router.delete("/{id}/items")
async def remove_playlist_item(id: str,
                               details: PlaylistItemRemove, 
                               db: Session = Depends(get_db),
                               yt_service: Resource = Depends(youtube.get_yt_service),
                               current_user = Depends(oauth2.get_current_user)):
    """
    Remove a video within a specified playlist
    """
    # check that playlist exists in db and that user has access to it
    playlist = db.scalar(select(Playlist).where(Playlist.id == id))
    if not playlist:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this playlist")
    
    # initialize editor
    try:
        playlist_editor = youtube.PlaylistEditor(mode = 'from_existing', playlist_id = id, yt_service = yt_service)
    except Exception as e:
        raise e
    
    playlist_editor.delete_video(pos = details.pos, yt_service = yt_service)

    return Response(status_code = status.HTTP_204_NO_CONTENT)
