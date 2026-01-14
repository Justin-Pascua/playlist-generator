from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from ..utils import insert_canonical
from ..schema import CanonicalCreate

router = APIRouter(
    prefix = "/playlists",
    tags = ['Playlists']
)

@router.get("/")
async def get_all_playlists():
    
    return {"message": "no playlists so far"}

@router.post("/")
async def create_playlist():
    # user should pass a date and a list of song strings
    # query db to check for matches
    # for all matches, get links
    # for all non-matches, 
    #   - search YouTube API
    #   - get link to top result (might need to think about this more carefully later)
    # 
    # gather all links and send request to YouTube API to create a playlist
    # add links and titles of unknown songs to database

    return {"playlist": "link here"}

@router.post("/playlists/{id}")
async def edit_playlist():
    # allow user to add, remove, replace, or change order of videos in playlist
    # add query param that indicates whether or not to reflect those changes in the song preference database
    return {"message": "editted playlist"}