from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from ..utils import insert_canonical
from ..schema import CanonicalCreate

router = APIRouter(
    prefix = "/songs",
    tags = ['Songs']
)

@router.get("/")
async def get_all_songs():
    """
    Returns all songs in the database, and (optionally) alternate titles plus video links
    """
    # include query params to allow user to...
    # - get or not get all alternate titles
    # - get or not get alt titles
    return {"message": "no songs yet"}

@router.post("/")
async def create_song(new_canonical: CanonicalCreate, 
                      db: Session = Depends(get_db)):
    """
    Inserts a song title into the canonical_names table
    """
    created_canonical = insert_canonical(new_canonical, db)
    return created_canonical

@router.get("/{id}")
async def get_song():
    """
    Returns a specified song from the database
    """
    pass

@router.get("/{id}/alt-names")
async def get_alt_names():
    pass

@router.post("/{id}/alt-names")
async def create_alt_name():
    pass

