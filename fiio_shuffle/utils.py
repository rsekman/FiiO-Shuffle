from os import environ
from pathlib import Path
from flask import Response
from json import dumps


def get_data_dir():
    try:
        xdg_data_home = Path(environ["XDG_DATA_HOME"])
    except KeyError:
        xdg_data_home = Path(environ["HOME"]) / ".local/share"
    return xdg_data_home / "FiiO-shuffle"


def get_config_dir():
    try:
        xdg_data_home = Path(environ["XDG_CONFIG_HOME"])
    except KeyError:
        xdg_data_home = Path(environ["HOME"]) / ".local/share"
    return xdg_data_home / "FiiO-shuffle"


def JSONResponse(j, success=None):
    if success is not None:
        out = {"success": success}
        out |= j
    else:
        out = j
    return Response(dumps(out), mimetype="application/json")


def JSONResponseError(message):
    return JSONResponse({"message": message}, False)


def deep_update(mapping, *updating_mappings):
    # Copied from pydantic.utils
    # https://github.com/pydantic/pydantic/blob/main/pydantic/_internal/_utils.py
    updated_mapping = mapping.copy()
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if (
                k in updated_mapping
                and isinstance(updated_mapping[k], dict)
                and isinstance(v, dict)
            ):
                updated_mapping[k] = deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping
