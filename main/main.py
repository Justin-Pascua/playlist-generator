from fastapi import FastAPI

from . import models
from .database import engine
from .config import settings

# initialization process:
# - load model
# - check db
# - maybe ping YouTube API?

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "hello world"}


@app.get("/songs")
async def get_all_songs():
    # include query params to allow user to get or not get all alternate titles
    return {"message": "no songs yet"}

@app.get("/playlists")
async def get_all_playlists():
    
    return {"message": "no playlists so far"}

@app.post("/playlists")
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

@app.post("/playlists/{id}")
async def edit_playlist():
    # allow user to add, remove, replace, or change order of videos in playlist
    # add query param that indicates whether or not to reflect those changes in the song preference database
    return {"message": "editted playlist"}

@app.post("/model")
async def call_model():
    # Discord bot passes raw Discord message here
    # API calls model and generates output 
    return {"model output": "output str here"}

