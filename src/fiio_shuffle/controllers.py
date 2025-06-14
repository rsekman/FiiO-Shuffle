from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import magic
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from .db import with_db
from .models import Album, Cover, Offer, Playlist
from .utils import JSONResponse, JSONResponseError, get_data_dir


@with_db
def get_all_playlists(db, session):
    s = select(Playlist).order_by(Playlist.title)
    return list(session.execute(s).scalars())


@with_db
def get_random_album(playlists, db, session):
    n_albums = session.query(func.count(Album.id)).scalar()
    if n_albums == 0:
        return None

    uuids = [UUID(pl) for pl in playlists]

    q = select(Album).options(joinedload(Album.cover)).join(Album.playlists)
    if len(uuids) != 0:
        q = q.filter(Playlist.uuid.in_( uuids))
    q = q.group_by(Album.id).order_by(func.random()).limit(1)
    album = session.execute(q).scalar()

    return album


@with_db
def process_offers(request, db, session):
    # We insert the offered albums into a temporary table so we can select the ones
    # that the client should upload with a simple SQL statement.
    # The database engine will optimise for us!
    try:
        temp_albs = [
            Offer(
                artist=a["artist"],
                title=a["title"],
                year=a["year"],
                timestamp=datetime.fromtimestamp(a["timestamp"]),
                playlist_uuid=UUID(a["playlist_uuid"]),
            )
            for a in request["albums"]
        ]
    except KeyError as e:
        return JSONResponseError(f"Invalid data: {e}")

    session.bulk_save_objects(temp_albs)
    q = (
        select(Offer.artist, Offer.title, Offer.year, Album.id)
        .join(
            Album,
            (Album.artist == Offer.artist)
            & (Album.title == Offer.title)
            & (Album.year == Offer.year),
            isouter=True,
        )
        .join(Cover, Album.cover_id == Cover.id, isouter=True)
        .where(
            (Album.id == None)  # noqa: E711
            | (Album.cover_id == None)  # noqa: E711
            | (Offer.timestamp > Cover.added)
        )
    )
    create_albums = [
        {
            "artist": a["artist"],
            "title": a["title"],
            "year": a["year"],
            "added": datetime.fromtimestamp(a["timestamp"]),
        }
        for a in request["albums"]
    ]
    stmt = insert(Album).values(create_albums).on_conflict_do_nothing()
    session.execute(stmt)

    albs = (
        select(Album, Playlist)
        .join(
            Offer,
            (Album.artist == Offer.artist)
            & (Album.title == Offer.title)
            & (Album.year == Offer.year),
        )
        .join(Playlist, (Playlist.uuid == Offer.playlist_uuid))
    )
    for a in session.execute(albs):
        if a.Playlist not in a.Album.playlists:
            a[0].playlists.append(a.Playlist)
    out = [
        {
            "artist": a.artist,
            "title": a.title,
            "year": a.year,
        }
        for a in session.execute(q)
    ]
    session.commit()

    return JSONResponse({"albums": out}, True)


@with_db
def process_playlists(request, db, session):
    try:
        pls = request["playlists"]
        uuids = [{"uuid": UUID(pl["uuid"]), "title": pl["title"]} for pl in pls]
    except (KeyError, ValueError) as e:
        return JSONResponseError(f"Invalid data: {e}")
    stmt = insert(Playlist).values(uuids).on_conflict_do_nothing()
    session.execute(stmt)
    session.commit()
    return JSONResponse({}, True)


def _album_from_data(data, session):
    now = datetime.now()
    q = select(Album).where(
        (Album.artist == data["artist"])
        & (Album.title == data["title"])
        & (Album.year == data["year"])
    )
    album = session.execute(q).scalar()
    return album or Album(added=now, **data)


@with_db
def upload_cover(cover_file, metadata, db, session):
    # Validate the cover before running any DB queries
    metadata = metadata["data"]
    try:
        buf = cover_file.read(2048)
        cover_file.seek(0)
        mime_type = magic.from_buffer(buf, mime=True)
        if not mime_type.startswith("image/"):
            raise ValueError(mime_type)
    except KeyError:
        return JSONResponseError("No cover file provided")
    except ValueError:
        return JSONResponseError(f"Cover is not an image, but of MIME type {mime_type}")

    try:
        album = _album_from_data(metadata, session)
    except (KeyError, TypeError) as e:
        return JSONResponseError(f"Invalid data: {e}.")
    if album is None:
        return JSONResponseError("")

    ext = Path(cover_file.filename).suffix
    now = datetime.now()
    cover = Cover(added=now, uuid=uuid4(), extension=ext)
    session.add(cover)
    album.cover = cover
    session.add(album)
    try:
        cover_file.save((get_data_dir() / "covers" / str(cover.uuid)).with_suffix(ext))
        session.commit()
    except (FileNotFoundError, IOError) as e:
        return JSONResponseError(f"Could not save cover file: {e}")
    except IntegrityError as e:
        return JSONResponseError(str(e))
    return JSONResponse({"success": True})
