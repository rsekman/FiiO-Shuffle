from sqlalchemy import (
    ForeignKey,
    UniqueConstraint,
    Column,
    Integer,
    Uuid,
    Table,
)
from sqlalchemy.orm import (
    declarative_base,
    Mapped,
    relationship,
)
from typing import Optional, List
from datetime import datetime


Base = declarative_base()

AlbumInPlaylist = Table(
    "albums_in_playlists",
    Base.metadata,
    Column("album_id", ForeignKey("albums.id")),
    Column("playlist_id", ForeignKey("playlists.uuid")),
    UniqueConstraint("album_id", "playlist_id"),
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
    uuid: Mapped[str]
    extension: Mapped[str]


class Playlist(Base):
    __tablename__ = "playlists"
    __table_args__ = (UniqueConstraint("uuid"),)

    uuid: Mapped[str] = Column(Uuid, primary_key=True)
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
