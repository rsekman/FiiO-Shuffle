from itertools import islice
from json import dumps
from logging import error
import mutagen
from pathlib import Path
from requests import post
from requests.exceptions import ConnectionError, HTTPError, Timeout, TooManyRedirects
from sys import exit

from .config import config


def _find_music(d):
    c = d / "cover.jpg"
    for f in d.iterdir():
        if f.is_dir():
            yield from _find_music(f)
        elif c.exists():
            m = mutagen.File(f, easy=True)
            if m is None:
                continue
            artist = m.get("albumartist", None) or m["artist"]
            yield ((artist[0], m["album"][0], int(m["date"][0][:4])), c)
            return


def _construct_offer(data):
    out = {"auth_key": config["auth_key"]}
    out["albums"] = [
        {
            "artist": k[0],
            "title": k[1],
            "year": k[2],
            "timestamp": int(v.stat().st_mtime),
        }
        for (k, v) in data.items()
    ]
    return out


def _make_key(a):
    return (a["artist"], a["title"], a["year"])


def _batched(iterable, n):
    # implements itertools.batched before Python 3.12
    # see 3.12 docs
    if n < 1:
        raise ValueError("n must be at least 1")
    it = iter(iterable)
    while batch := dict(islice(it, n)):
        yield batch


def _offer_and_upload(url, candidates):
    offer = _construct_offer(candidates)
    print(f"Offering {len(candidates)} candidates...", end=" ")
    try:
        resp = post(url + "/offer", json=offer)
        resp.raise_for_status()
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        error(e.args)
    except HTTPError as e:
        error(e)
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
    for a in albums:
        try:
            o = candidates[_make_key(a)]
        except KeyError:
            continue
        metadata = {"auth_key": config["auth_key"], "data": a}
        files = [
            ("metadata", ("metadata.json", dumps(metadata))),
            ("cover", ("cover.jpg", o.open("rb"))),
        ]
        print(f"Uploading {a['artist']} - {a['title']} ({a['year']})...", end="")
        try:
            r = post(url + "/upload", files=files)
            r.raise_for_status()
        except (ConnectionError, Timeout, TooManyRedirects, HTTPError) as e:
            error(e)
            print("")
        else:
            print("Success.")


def run_client(root, url):
    root_dir = Path(root)
    if not root_dir.exists():
        exit(f"Root directory {root} does not exist!")
    candidates = {k: v for k, v in _find_music(root_dir)}
    for candidate_batch in _batched(candidates.items(), config["batch_size"]):
        _offer_and_upload(url, candidate_batch)
