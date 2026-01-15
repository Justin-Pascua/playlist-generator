from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter

from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.mysql import JSON

from typing import List, Optional

from ..database import get_db
from ..schema import CanonicalCreate, AltNameCreate, AltNameResponse, SongLinkCreate, SongSummary
from ..models import Canonical, AltName, SongLink
from .. import oauth2

router = APIRouter(
    prefix = "/songs",
    tags = ['Songs']
)

@router.get("/", response_model = List[SongSummary], response_model_exclude_defaults = True)
async def get_all_songs(get_links: bool = False, get_alts: bool = False, 
                        db: Session = Depends(get_db),
                        current_user = Depends(oauth2.get_current_user)):
    """
    Returns all songs in the database, and (optionally) alternate titles plus video links
    """

    # choose fields to fetch
    select_cols = [Canonical.title.label("title")]
    if get_links:
        select_cols.append(SongLink.link.label("song_link"))
    if get_alts:
        select_cols.append(func.json_arrayagg(AltName.title).cast(JSON).label("alt_names"))

    # build query statement
    stmt = select(*select_cols).where(Canonical.user_id == current_user.id)
    if get_links:
        stmt = stmt.join(SongLink, Canonical.id == SongLink.song_id, isouter = True)
    if get_alts:
        stmt = (stmt
                .join(AltName, Canonical.id == AltName.canonical_id, isouter = True)
                .group_by(Canonical.id))

    result = db.execute(stmt).all() 
    print(result)
    return result



@router.post("/", status_code = status.HTTP_201_CREATED)
async def create_song(new_canonical: CanonicalCreate, 
                      db: Session = Depends(get_db),
                      current_user = Depends(oauth2.get_current_user)):
    """
    Inserts a song title into the canonical_names table
    """
    created_canonical = Canonical(user_id = current_user.id, **new_canonical.model_dump())
    db.add(created_canonical)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, 
                            detail = "Song already exists in your database")
    
    db.refresh(created_canonical)
    return created_canonical

@router.get("/{id}", response_model = SongSummary)
async def get_song(id: int, 
                   db: Session = Depends(get_db),
                   current_user = Depends(oauth2.get_current_user)):
    """
    Returns a specified song from the database, including its alt names and link
    """
    stmt = (select(
        Canonical.title.label('title'),
        Canonical.user_id.label('user_id'),
        SongLink.link.label("song_link"),
        func.json_arrayagg(AltName.title).label("alt_names").cast(JSON).label("alt_names")
        )
        .where(Canonical.id == id)
        .join(SongLink, Canonical.id == SongLink.song_id, isouter = True)
        .join(AltName, Canonical.id == AltName.canonical_id, isouter = True)
        .group_by(Canonical.id, Canonical.title, SongLink.link))
    
    result = db.execute(stmt).first()
    # check if song exists
    if not result:
        raise(HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Item not found"))

    # check if user has access to song
    # if not, raise HTTP exception
    if result.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this item")


    return result

@router.get("/{id}/alt-names", response_model = List[AltNameResponse])
async def get_alt_names(id: int, 
                        db: Session = Depends(get_db),
                        current_user = Depends(oauth2.get_current_user)):
    stmt = (select(
        AltName.user_id, 
        AltName.title.label('alt_name'))
        .where(AltName.canonical_id == id))
    
    result = db.execute(stmt).all()

    if not result:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Item not found")
    
    if result[0].user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this item")
    
    return result

# need to check if user is authorized to modify song[id]
@router.post("/{id}/alt-names")
async def create_alt_name(id: int, new_alt: AltNameCreate, 
                          db: Session = Depends(get_db),
                          current_user = Depends(oauth2.get_current_user)):
    """
    Create an alt name for a song
    """

    created_alt = AltName(
        user_id = current_user.id, 
        canonical_id = id, 
        **new_alt.model_dump())
    db.add(created_alt)
    db.commit()
    db.refresh(created_alt)
    
    return created_alt

@router.get("/{id}/song-links")
async def get_link(id: int,
                   db: Session = Depends(get_db),
                   current_user = Depends(oauth2.get_current_user)):
    """
    Create a link for a song
    """

    result = (db.query(SongLink)
              .filter(SongLink.user_id == current_user.id)
              .filter(SongLink.song_id == id)
              .all())

    return result

# need to check if link already exists
@router.put("/{id}/song-links")
async def assign_link(id: int, new_link: SongLinkCreate,
                      db: Session = Depends(get_db),
                      current_user = Depends(oauth2.get_current_user)):
    """
    Create or edit link for a song
    """
    created_link = SongLink(song_id = id, user_id = current_user.id, **new_link.model_dump())
    db.add(created_link)
    db.commit()
    db.refresh(created_link)

    return created_link