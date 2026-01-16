from .database import Base
from typing import List, Optional
from datetime import datetime
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Canonical(Base):
    __tablename__ = "canonical_names"

    id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True)
    title: Mapped[str] = mapped_column(String(64), nullable = False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete = "CASCADE"), nullable = False)

    # multiple users can know the same song, but a given user can only record a given song at most once
    __table_args__ = (
        UniqueConstraint("title", "user_id", name = "title_user_pair"),
    )

    user = relationship("User", back_populates = "canonicals")
    alt_names = relationship("AltName", cascade = "all, delete", passive_deletes = True)
    song_link = relationship("SongLink", cascade = "all, delete", passive_deletes = True, uselist = False)


class AltName(Base):
    __tablename__ = "alt_names"

    id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True)
    title: Mapped[str] = mapped_column(String(64), unique = True, nullable = False)
    canonical_id: Mapped[int] = mapped_column(ForeignKey("canonical_names.id", ondelete = "CASCADE"), nullable = False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete = "CASCADE"), nullable = False)

    canonical_title = relationship("Canonical", back_populates = "alt_names")
    user = relationship("User")


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True)
    playlist_title: Mapped[str] = mapped_column(String(64), nullable = True)
    link: Mapped[str] = mapped_column(String(64), unique = True, nullable = False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete = "CASCADE"), nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable = False)

    user = relationship("User")

class SongLink(Base):
    __tablename__ = "song_links"

    id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True)
    song_id: Mapped[int] = mapped_column(ForeignKey("canonical_names.id", ondelete = "CASCADE"), unique = True, nullable = False)
    link: Mapped[str] = mapped_column(String(64), unique = True, nullable = False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete = "CASCADE"), nullable = False)

    song = relationship("Canonical", back_populates = "song_link")
    user = relationship("User")

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True)
    username: Mapped[str] = mapped_column(String(64), unique = True, nullable = False)
    password: Mapped[str] = mapped_column(String(256), nullable = False)

    canonicals = relationship("Canonical", cascade = "all, delete", passive_deletes = True)
    alt_names = relationship("AltName", cascade = "all, delete", passive_deletes = True)
    song_links = relationship("SongLink", cascade = "all, delete", passive_deletes = True)
