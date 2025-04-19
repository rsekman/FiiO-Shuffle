from logging import error
from os import makedirs
from sys import exit

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .config import config
from .models import Base
from .utils import get_data_dir


class Database:
    def __init__(self, echo=False):
        # db_path needs to be absolute so we known the right number of slashes to use on the next line
        # see https://docs.sqlalchemy.org/en/13/core/engines.html#sqlite
        db_path = (get_data_dir() / "fiio_shuffle.sqlite3").resolve()
        try:
            makedirs(db_path.parent, exist_ok=True)
        except IOError as e:
            error(f"Could not create DB directory {db_path.parent}: {e}")
            exit()
        try:
            self.engine = create_engine(f"sqlite:///{db_path}", echo=echo)
            Base.metadata.create_all(self.engine)
        except Exception as e:
            error(f"Could not initialise ORM models: {e}")
            exit()

    def session(self):
        return Session(self.engine)


def get_db():
    return Database(echo=config.get("debug", False))


def with_db(f):
    def g(*args, **kwargs):
        db = get_db()
        with db.session() as session:
            return f(*args, db=db, session=session, **kwargs)

    return g
