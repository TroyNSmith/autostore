"""Database connection."""

from pathlib import Path
from typing import TypeVar

from sqlmodel import Session, SQLModel, create_engine, select

from .models import *  # noqa: F403

T = TypeVar("T", bound=SQLModel)


class Database:
    """
    Database connection manager.

    Attributes
    ----------
    path
        Path to SQLite database file.
    engine
        SQLAlchemy engine instance.
    """

    def __init__(self, path: str | Path = ":memory:", *, echo: bool = False) -> None:
        """
        Initialize database connection manager.

        Parameters
        ----------
        path
            Path to the SQLite database file. By default, operate in memory.
        echo, optional
            If True, SQL statements will be logged to the standard output.
            If False, no logging is performed.
        """
        self.path = Path(path)
        self.engine = create_engine(f"sqlite:///{self.path}", echo=echo)
        SQLModel.metadata.create_all(self.engine)

    def session(self) -> Session:
        """Create a new database session."""
        return Session(self.engine)

    def select_all(self, model: type[T]) -> list[T]:
        with self.session() as session:
            return session.exec(select(model)).all()  # ty:ignore[invalid-return-type]

    def close(self) -> None:
        """Close the database connection.

        Seems to be needed only for testing with in-memory databases.
        """
        self.engine.dispose()
