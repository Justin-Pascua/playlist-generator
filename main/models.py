from .database import Base
from typing import List, Optional
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Canonical(Base):
    __tablename__ = "canonical_names"

    id: Mapped[int] = mapped_column(primary_key = True, nullable = False)
    title: Mapped[str] = mapped_column(String(64), unique = True, nullable = False)
    user_id: Mapped[int] = mapped_column(nullable = False)

    def __repr__(self):
        return f"Canonical(id = {self.id!r}, title = {self.title!r}, user_id = {self.user_id!r})"

class AltName(Base):
    __tablename__ = "alt_names"

    id: Mapped[int] = mapped_column(primary_key = True)
    title: Mapped[str] = mapped_column(String(64), primary_key = True)
    canonical: Mapped[str] = mapped_column(String(64), nullable = False)
    user_id: Mapped[int] = mapped_column(nullable = False)

    def __repr__(self):
        return f"AltName(id = {self.id!r}, title = {self.title!r}, canonical = {self.canonical!r}, user_id = {self.user_id!r})"
    
class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key = True)
    playlist_title: Mapped[str] = mapped_column(String(64))
    link: Mapped[str] = mapped_column(String(64), unique = True, nullable = False)
    user_id: Mapped[int] = mapped_column(nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable = False)

    def __repr__(self):
        return f"Playlist(id = {self.id!r}, playlist_title = {self.playlist_title!r}, link = {self.link!r}, user_id = {self.user_id!r}, created_at = {self.created_at})"
    
class SongLink(Base):
    __tablename__ = "song_links"

    id: Mapped[int] = mapped_column(primary_key = True)
    song_title: Mapped[str] = mapped_column(String(64), unique = True, nullable = False)
    link: Mapped[str] = mapped_column(String(64), unique = True, nullable = False)
    user_id: Mapped[int] = mapped_column(nullable = False)

    def __repr__(self):
        return f"Playlist(id = {self.id!r}, song_title = {self.song_title!r}, link = {self.link!r}, user_id = {self.user_id!r})"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key = True)
    email: Mapped[str] = mapped_column(String(64), primary_key = True, unique = True)
    username: Mapped[str] = mapped_column(String(64), primary_key = True, unique = True)
    password: Mapped[str] = mapped_column(String(64), nullable = False)

