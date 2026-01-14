from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from ..schema import CanonicalCreate, AltNameCreate
from ..models import Canonical, AltName

router = APIRouter(
    prefix = "/songs",
    tags = ['Songs']
)

@router.get("/")
async def get_all_songs(get_alts: bool = False, get_links: bool = False, db: Session = Depends(get_db)):
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
    created_canonical = Canonical(**new_canonical.model_dump())
    db.add(created_canonical)
    db.commit()
    db.refresh(created_canonical)
    return created_canonical

@router.get("/{id}")
async def get_song(new_alt: AltNameCreate, db: Session = Depends(get_db)):
    """
    Returns a specified song from the database
    """
    new_alt['canonical_id'] = id
    created_alt = AltName(**new_alt.model_dump())
    db.add(created_alt)
    db.commit()
    db.refresh(created_alt)
    pass

@router.get("/{id}/alt-names")
async def get_alt_names():
    pass

@router.post("/{id}/alt-names")
async def create_alt_name():
    pass

