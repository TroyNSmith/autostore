"""Database connection."""

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from .models import *  # noqa: F403


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

    def __init__(self, path: str | Path, *, echo: bool = False) -> None:
        """
        Initialize database connection manager.

        Parameters
        ----------
        path
            Path to the SQLite database file.
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

    def close(self) -> None:
        """Close the database connection.

        Seems to be needed only for testing with in-memory databases.
        """
        self.engine.dispose()
