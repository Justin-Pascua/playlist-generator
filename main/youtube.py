from fastapi import Depends

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import Resource, build

from .config import settings

from typing import Literal
import os
import ast
import pickle

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

# Don't need to worry about refreshing. This is done by googleapiclient in the backend
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

def create_blank_playlist(title: str,
                          privacy_status: Literal["public", "private", "unlisted"] = "private",
                          yt_service: Resource = Depends(get_yt_service)):
    pass