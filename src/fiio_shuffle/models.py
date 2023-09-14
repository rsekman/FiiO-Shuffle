from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from typing import Optional


class Base(DeclarativeBase):
    pass


class Album(Base):
    __tablename__ = "albums"
    id: Mapped[int] = mapped_column(primary_key=True)
    added: Mapped[int]
    artist: Mapped[str]
    title: Mapped[str]
    year: Mapped[int]

    cover_id: Mapped[Optional[int]] = mapped_column(ForeignKey("covers.id"))
    cover: Mapped[Optional["Cover"]] = relationship()

    __table_args__ = (UniqueConstraint("artist", "title", "year"),)


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = {"prefixes": ["TEMPORARY"]}

    id: Mapped[int] = mapped_column(primary_key=True)
    artist: Mapped[str]
    title: Mapped[str]
    year: Mapped[int]
    timestamp: Mapped[int]


class Cover(Base):
    __tablename__ = "covers"

    id: Mapped[int] = mapped_column(primary_key=True)
    added: Mapped[int]
    uuid: Mapped[str]
    extension: Mapped[str]
