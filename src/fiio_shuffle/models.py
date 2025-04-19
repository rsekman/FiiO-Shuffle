from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Table,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    relationship,
)

Base = declarative_base()

AlbumInPlaylist = Table(
    "albums_in_playlists",
    Base.metadata,
    Column("album_id", ForeignKey("albums.id")),
    Column("playlist_uuid", ForeignKey("playlists.uuid")),
    UniqueConstraint("album_id", "playlist_uuid"),
)


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = Column(type_=Integer, primary_key=True)
    added: Mapped[datetime]
    artist: Mapped[str]
    title: Mapped[str]
    year: Mapped[int]
    playlists: Mapped[List["Playlist"]] = relationship(
        "Playlist", back_populates="albums", secondary=AlbumInPlaylist
    )

    cover_id: Mapped[Optional[int]] = Column(ForeignKey("covers.id"))
    cover: Mapped[Optional["Cover"]] = relationship("Cover")

    __table_args__ = (UniqueConstraint("artist", "title", "year"),)


class Cover(Base):
    __tablename__ = "covers"

    id: Mapped[int] = Column(type_=Integer, primary_key=True)
    added: Mapped[datetime]
    uuid: Mapped[UUID]
    extension: Mapped[str]


class Playlist(Base):
    __tablename__ = "playlists"
    __table_args__ = (UniqueConstraint("uuid"),)

    uuid: Mapped[UUID] = Column(Uuid, primary_key=True)
    title: Mapped[str]

    albums: Mapped[List["Album"]] = relationship(
        "Album", back_populates="playlists", secondary=AlbumInPlaylist
    )


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = {"prefixes": ["TEMPORARY"]}

    id: Mapped[Integer] = Column(type_=Integer, primary_key=True)
    artist: Mapped[str]
    title: Mapped[str]
    year: Mapped[int]
    timestamp: Mapped[datetime]

    playlist_uuid: Mapped[[int]] = Column(ForeignKey("playlists.uuid"))
    playlist: Mapped[Optional["Playlist"]] = relationship("Playlist")
