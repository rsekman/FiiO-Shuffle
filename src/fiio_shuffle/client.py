from collections import namedtuple
from itertools import batched
from json import dumps
from logging import error
import dbpl
from pathlib import Path
from requests import post
from requests.exceptions import ConnectionError, HTTPError, Timeout, TooManyRedirects
from sys import exit
from uuid import uuid4

from .config import config

UUID_KEY = "fiio_shuffle_uuid"

AlbumEntry = namedtuple(
    "Album", ["artist", "title", "year", "cover_uri", "timestamp", "playlist_uuid"]
)


def _find_playlists(root_dir):
    pls = []
    for f in root_dir.iterdir():
        if not (f.is_file() and f.suffix == ".dbpl"):
            continue
        pl = dbpl.Playlist(f)
        if "title" not in pl.meta:
            print(f"Playlist {f} does not have a title in its meta, skipping")
            continue
        if UUID_KEY not in pl.meta.keys():
            pl.meta[UUID_KEY] = str(uuid4())
            pl.save()
        pls.append(pl)
    return pls


def _find_albums_in_playlist(pl):
    print(f"Finding albums from {pl.meta['title']}...", end="", flush=True)
    albums = {}
    uuid = pl.meta[UUID_KEY]
    for track in pl.tracks:
        meta = track.meta
        try:
            cover_uri = Path(track.uri).parent / "cover.jpg"
            if not cover_uri.exists():
                continue
            artist=meta.get("album artist", None) or meta["artist"]
            title=meta["album"]
            year=int((meta.get("year", None) or meta["date"])[:4])
            key = (artist, title, year)
            if key in albums:
                continue
            entry = AlbumEntry(
                artist=artist,
                title=title,
                year=year,
                cover_uri=cover_uri,
                timestamp=int(cover_uri.stat().st_mtime),
                playlist_uuid=uuid,
            )
        except KeyError as e:
            print(f"{track.uri} does not contain key {e}, skipping")
            continue
        albums[key] = entry
    print(f" found {len(albums)} albums.")
    yield from albums.items()


def _construct_offer(data):
    data = [
        {k: v for k, v in d._asdict().items() if k not in ["cover_uri"]} for _, d in data
    ]
    out = {"auth_key": config["auth_key"], "albums": data}
    return out


def _make_key(a):
    return (a["artist"], a["title"], a["year"])


def _offer_and_upload(url, candidates):
    offer = _construct_offer(candidates)
    print(f"Offering {len(candidates)} candidates...", end=" ", flush=True)
    try:
        resp = post(url + "/offer", json=offer)
        resp.raise_for_status()
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        error(e.args)
        return
    except HTTPError as e:
        error(e)
        return
    json = resp.json()
    if not json.get("success", False):
        message = json.get("message", "No message provided.")
        error(f"Unsuccessful offer: {message}.")
        return
    albums = json.get("albums", [])
    print(f"{len(albums)} albums accepted.", end=" ")
    if len(albums):
        print("Uploading...")
    else:
        print("")
    candidates = {k:v for k, v in candidates }
    for a in albums:
        try:
            o = candidates[_make_key(a)]
        except KeyError:
            continue
        metadata = {"auth_key": config["auth_key"], "data": a}
        files = [
            ("metadata", ("metadata.json", dumps(metadata))),
            ("cover", ("cover.jpg", o.cover_uri.open("rb"))),
        ]
        print(f"Uploading {a['artist']} - {a['title']} ({a['year']})...", end="")
        try:
            r = post(url + "/upload", files=files)
            r.raise_for_status()
        except (ConnectionError, Timeout, TooManyRedirects, HTTPError) as e:
            error(e)
            print("")
        else:
            j = r.json()
            if j["success"]:
                print("Success.")
            else:
                print(f"Error: {j['error']}")


def _submit_playlists(url, pls):
    data = {"auth_key": config["auth_key"], "playlists": pls}
    try:
        resp = post(url + "/playlists", json=data)
        resp.raise_for_status()
        return resp.json()
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        error(e.args)
        return
    except HTTPError as e:
        error(e)
        return


def run_client(root, url):
    root_dir = Path(root)
    if not root_dir.exists():
        exit(f"Root directory {root} does not exist!")
    pls = _find_playlists(root_dir)
    pl_submissions = [
        {"title": pl.meta["title"], "uuid": pl.meta[UUID_KEY]} for pl in pls
    ]
    _submit_playlists(url, pl_submissions)
    print("Submitted playlists")
    for pl in pls:
        for candidate_batch in batched(
            _find_albums_in_playlist(pl), config["batch_size"]
        ):
            _offer_and_upload(url, candidate_batch)
