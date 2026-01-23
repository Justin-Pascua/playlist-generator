from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from .config import settings

import os
import ast
import pickle

API_KEY = settings.YT_API_KEY

def get_credentials(as_json: bool = False):
    credentials = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            credentials = pickle.load(token)

    if not credentials.valid:
        credentials.refresh(Request())
        
    if as_json:
        return ast.literal_eval(credentials.to_json())

    return credentials

def get_yt_service():
    yt_service = build('youtube', 'v3', 
                       credentials = get_credentials(), 
                       developerKey = API_KEY)
    try:
        yield yt_service
    finally:
        yt_service.close()

