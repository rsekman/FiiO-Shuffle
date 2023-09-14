from flask import Flask
from flask import request, render_template, send_from_directory
from flask_assets import Environment, Bundle
from functools import wraps
from json import loads

from .controllers import get_random_album, process_offers, upload_cover
from .config import config
from .utils import get_data_dir, JSONResponseError

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
    album = get_random_album()
    return render_template("index.html.jinja", album=album[1])


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
    return process_offers(request.json, request)


@server.route("/upload", methods=["POST"])
@needs_auth
def upload():
    try:
        json = loads(request.files["metadata"].read())
        return upload_cover(json, request)
    except KeyError:
        return JSONResponseError(
            "Invalid request: no metadata provided",
        )


@server.route("/covers/<uuid:cover_id>.<string:extension>")
def send_cover(cover_id, extension):
    d = get_data_dir() / "covers"
    return send_from_directory(str(d), str(cover_id) + "." + extension)
