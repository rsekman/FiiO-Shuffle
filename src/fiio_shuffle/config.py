from importlib.resources import files
from json import dump, load, JSONDecodeError
from logging import error, warning
from os import umask
from secrets import token_hex
from sys import exit

from .utils import get_config_dir, deep_update


class Config:
    def __init__(self):
        config_file = get_config_dir() / "config.json"

        # Load default configuration
        with files("fiio_shuffle").joinpath("config.json").open() as f:
            self._config = load(f)

        try:
            with config_file.open() as f:
                cfg = load(f)
                self._config = deep_update(self._config, cfg)
        except (IOError, FileNotFoundError) as e:
            warning(
                f"Could not read config from {config_file}: {e}; falling back on default."
            )
        except JSONDecodeError as e:
            error(f"Malformed JSON in {config_file}: {e}")
            exit()

        if "auth_key" not in self._config.keys():
            warning(
                f"No authentication key in {config_file}. Generating one for you..."
            )
            token = token_hex()
            warning(f"Your authentication key is: {token}. Saving to {config_file}...")
            self._config["auth_key"] = token
            d = config_file.parent
            if not d.exists():
                from os import makedirs

                try:
                    makedirs(d, exist_ok=True)
                except IOError as e:
                    error(f"Could not create directiory {d}: {e}")
                    exit()
            um = umask(0o177)
            with config_file.open("w") as f:
                dump(self._config, f, indent=4)
            umask(um)

    def __getitem__(self, key):
        return self._config[key]

    def get(self, key, default=None):
        return self._config.get(key, default)


config = Config()
