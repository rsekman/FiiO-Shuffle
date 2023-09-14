from datetime import datetime
import magic
from pathlib import Path
from random import randint
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from uuid import uuid4

from .db import with_db
from .models import Album, Cover, Offer
from .utils import get_data_dir, JSONResponse, JSONResponseError


@with_db
def get_random_album(db, session):
    n_albums = session.query(func.count(Album.id)).scalar()
    if n_albums == 0:
        return (0, None)
    id_max = session.query(func.max(Album.id)).scalar()
    album = None
    while album is None:
        r = randint(1, id_max)
        q = select(Album).options(joinedload(Album.cover)).where(Album.id == r)
        album = session.execute(q).scalar()

    return (n_albums, album)


@with_db
def process_offers(json, request, db, session):
    # We insert the offered albums into a temporary table so we can select the ones
    # that the client should upload with a simple SQL statement.
    # The database engine will optimise for us!
    try:
        temp_albs = [Offer(**a) for a in request.json["albums"]]
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
    out = [
        {
            "artist": a.artist,
            "title": a.title,
            "year": a.year,
        }
        for a in session.execute(q)
    ]

    return JSONResponse({"albums": out}, True)


def _album_from_data(data, session):
    now = int(datetime.now().timestamp())
    q = select(Album).where(
        (Album.artist == data["artist"])
        & (Album.title == data["title"])
        & (Album.year == data["year"])
    )
    album = session.execute(q).scalar()
    return album or Album(added=now, **data)


@with_db
def upload_cover(json, request, db, session):
    # Validate the cover before running any DB queries
    try:
        cover_file = request.files["cover"]
        buf = cover_file.read(2048)
        cover_file.seek(0)
        mime_type = magic.from_buffer(buf, mime=True)
        if not mime_type.startswith("image/"):
            raise ValueError(mime_type)
    except KeyError:
        return JSONResponseError("No cover file provided")
    except ValueError:
        return JSONResponseError(f"Cover is not an image, but of MIME type {mime_type}")

    if "data" not in json.keys():
        return JSONResponseError("No data provided!")
    try:
        album = _album_from_data(json["data"], session)
    except (KeyError, TypeError) as e:
        return JSONResponseError(f"Invalid data: {e}.")
    if album is None:
        return JSONResponseError("")

    ext = Path(cover_file.filename).suffix
    now = int(datetime.now().timestamp())
    cover = Cover(added=now, uuid=str(uuid4()), extension=ext)
    session.add(cover)
    album.cover = cover
    session.add(album)
    try:
        cover_file.save((get_data_dir() / "covers" / cover.uuid).with_suffix(ext))
        session.commit()
    except (FileNotFoundError, IOError) as e:
        return JSONResponseError(f"Could not save cover file: {e}")
    except IntegrityError as e:
        return JSONResponseError(str(e))
    return JSONResponse({"success": True})
