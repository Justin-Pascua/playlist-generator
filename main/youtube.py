from fastapi import Depends

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from typing import Literal
import os
import ast
import pickle

from .config import settings
from .schema import PlaylistCreate

API_KEY = settings.YT_API_KEY
TOKEN_PATH = "token.json"

# initialize credentials for building yt_service
credentials = None

try: 
    credentials = Credentials.from_authorized_user_file(
        TOKEN_PATH, 
        ["https://www.googleapis.com/auth/youtubepartner",
            "https://www.googleapis.com/auth/youtube",
            "https://www.googleapis.com/auth/youtube.force-ssl"])
except FileNotFoundError:
    raise FileNotFoundError(f"Specified file ({TOKEN_PATH}) not found")
except Exception as e:
    raise e

# Don't need to worry about refreshing credentials. 
# This is done by googleapiclient in the backend when making requests
# if not credentials.valid:
#     credentials.refresh(Request())


def get_yt_service():
    print("Calling get_yt_service")
    yt_service = build('youtube', 'v3', 
                       credentials = credentials, 
                       developerKey = API_KEY)
    try:
        yield yt_service
    finally:
        yt_service.close()

def search_video(query_string: str, yt_service: Resource = Depends(get_yt_service)):
    root = 'http://youtu.be/'

    request = yt_service.search().list(
        part = "snippet",
        q = query_string,
        type = "video"
    )
    response = request.execute()
    
    top_vid = response['items'][0]

    id = top_vid['id']['videoId']
    title = top_vid['snippet']['title']
    channel = top_vid['snippet']['channelTitle']
    link = root + id
    
    return {'id': id,
            'title': title,
            'channel': channel,
            'link': link}

def create_blank_playlist(payload: PlaylistCreate,
                          yt_service: Resource = Depends(get_yt_service)):
    request = yt_service.playlists().insert(
        part = "id,snippet,status",
        body = {"snippet": {"title": payload.title},
                "status": {"privacyStatus": payload.privacy_status}
                })
    response = request.execute()

    return response

def get_playlist_items(playlist_id: str, yt_service: Resource = Depends(get_yt_service)):
    request = yt_service.playlistItems().list(
        part = "id,snippet",
        playlistId = playlist_id
    )
    response = request.execute()

    return response

def delete_playlist(playlist_id: str, yt_service: Resource = Depends(get_yt_service)):
    request = yt_service.playlists().delete(
        id = playlist_id
    )
    response = request.execute()

    return response

def insert_video_in_playlist(playlist_id: str, video_id: str,
                             pos: int | None = None, 
                             yt_service: Resource = Depends(get_yt_service)):
    request = yt_service.playlistItems().insert(
        part = 'id,snippet,status',
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "position": pos,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id}
            }
        }
    )
    response = request.execute()

    return response

def delete_playlist_item(item_id: str, yt_service: Resource = Depends(get_yt_service)):

    pass

def delete_playlist_item_at_pos(playlist_id: str, pos: int, 
                                yt_service: Resource = Depends(get_yt_service)):

    pass

def replace_playlist_item(playlist_id: str, pos: int, video_id: str, 
                          yt_service: Resource = Depends(get_yt_service)):

    pass

def move_playlist_item(playlist_id: str, init_pos: int, target_pos: int,
                       yt_service: Resource = Depends(get_yt_service)):

    pass