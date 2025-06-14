from functools import wraps
from json import loads

from flask import Flask, render_template, request, send_from_directory
import warnings
with warnings.catch_warnings(action="ignore"):
    from flask_assets import Bundle, Environment

from .config import config
from .controllers import (
    get_all_playlists,
    get_random_album,
    process_offers,
    process_playlists,
    upload_cover,
)
from .utils import JSONResponse, JSONResponseError, get_data_dir

data_dir = get_data_dir()
static_dir = data_dir / ".webstatic"

server = Flask(__name__)
assets = Environment(server)
assets.url = "assets"
assets.directory = str(static_dir)
css = Bundle("style.sass", filters="sass", output="style.css")
assets.register("css", css)


@server.route("/assets/<path:path>")
def send_static(path):
    return send_from_directory(str(get_data_dir() / ".webstatic"), path)


@server.route("/")
def index():
    album = get_random_album([])
    playlists = get_all_playlists()
    return render_template("index.html", album=album, playlists=playlists)


@server.route("/album", methods=["POST"])
def random_album():
    pls = request.json.get("playlists", [])
    try:
        album = get_random_album(pls)
    except Exception as e:
        return JSONResponseError(f"Error: {e}")
    if album is None:
        return JSONResponseError("No albums found")

    return JSONResponse({
        "artist": album.artist,
        "title": album.title,
        "year": album.year,
        "cover": str(album.cover.uuid) + album.cover.extension
    })


def needs_auth(f):
    @wraps(f)
    def g(*args, **kwargs):
        if request.is_json:
            _json = request.json
        else:
            try:
                _json = loads(request.files["metadata"].read())
                # Seek to the beginning so that the file object is transparent to the end user
                request.files["metadata"].seek(0)
            except (AttributeError, KeyError) as e:
                return JSONResponseError(f"Invalid request: {e}")

        try:
            _auth_key = _json["auth_key"]
        except KeyError:
            return JSONResponseError("No authentication token supplied")
        if _auth_key != config["auth_key"]:
            return JSONResponseError("Incorrect authentication key")

        return f(*args, **kwargs)

    return g


@server.route("/offer", methods=["POST"])
@needs_auth
def offer():
    return process_offers(request.json)


@server.route("/playlists", methods=["POST"])
@needs_auth
def playlists():
    return process_playlists(request.json)


@server.route("/upload", methods=["POST"])
@needs_auth
def upload():
    try:
        metadata = loads(request.files["metadata"].read())
        cover_file = request.files["cover"]
        return upload_cover(cover_file, metadata)
    except KeyError:
        return JSONResponseError(
            "Invalid request: no metadata provided",
        )


@server.route("/covers/<uuid:cover_id>.<string:extension>")
def send_cover(cover_id, extension):
    d = get_data_dir() / "covers"
    return send_from_directory(str(d), str(cover_id) + "." + extension)
