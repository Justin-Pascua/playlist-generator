from fastapi import FastAPI, Depends

from . import models
from .database import engine, get_db
from .config import settings
from .schema import CanonicalCreate
from sqlalchemy.orm import Session
from .utils import insert_canonical
from .router import model, playlists, songs

# initialization process:
# - load model
# - check db
# - maybe ping YouTube API?

app = FastAPI()

app.include_router(model.router)
app.include_router(playlists.router)
app.include_router(songs.router)

@app.get("/")
async def root():
    return {"message": "hello world"}



