"""Database connection."""

from pathlib import Path
from typing import cast

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, SQLModel, create_engine, select

from .models import *  # noqa: F403
from .types import RowID, RowIDs, SQLModelT


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

    def add(self, *, row: SQLModelT) -> RowID | None:
        """
        Add row to database.

        Parameters
        ----------
        row
            Instance of a database model class.

        Returns
        -------
            id corresponding to entry in model table or None if row does not assign id.

        Raises
        ------
        SQLAlchemyError
            Database row failed to write.
        """
        try:
            with self.session() as session:
                session.add(row)
                session.commit()
                session.refresh(row)
                # Some rows do not have id so we must return None
                return getattr(row, "id", None)

        except (SQLAlchemyError, IntegrityError) as e:
            msg = f"Failed to add {row = }. Try using Database.get_or_add() instead."
            raise RuntimeError(msg) from e

    def delete(self, *, model: type[SQLModelT], row_id: RowID) -> None:
        """
        Delete a row from the database based on row id.

        Parameters
        ----------
        model
            Database model class, e.g. CalculationRow or GeometryRow.
        row_id
            id corresponding to entry in model table.

        Raises
        ------
        LookupError
            Row ID is not found in model table.
        RuntimeError
            Database row failed to delete.
        """
        try:
            with self.session() as session:
                # Reuse the logic of finding the row first
                row = session.get(model, row_id)

                if row is None:
                    msg = f"Unable to find {model.__tablename__} row with ID {row_id}."
                    raise LookupError(msg)

                session.delete(row)
                session.commit()

        except SQLAlchemyError as e:
            msg = f"Failed to delete {model.__tablename__} with ID {row_id}."
            raise RuntimeError(msg) from e

    def get(self, *, model: type[SQLModelT], row_id: RowID) -> SQLModelT:
        """
        Get a row from the database based on row id.

        Parameters
        ----------
        model
            Database model class, e.g. CalculationRow or GeometryRow.
        row_id
            id corresponding to entry in model table.

        Returns
        -------
            Instance of a database "model".

        Raises
        ------
        LookupError
            Row ID is not found in model table.
        TypeError
            Return type is not a database model.
        """
        with self.session() as session:
            row = session.get(model, row_id)

            if row is None:
                msg = f"Unable to find {model.__tablename__} row with ID {row_id}."
                raise LookupError(msg)

            if not isinstance(row, model):
                msg = f"{row = }, {model = }"
                raise TypeError(msg)

            return row

    def query_or_add(self, *, row: SQLModelT) -> RowIDs:
        """
        Query existing rows based on Class keywords. If None, adds row to database.

        Parameters
        ----------
        row
            Instance of a database model class.

        Returns
        -------
            id corresponding to entry in model table or None if row does not assign id.

        Raises
        ------
        SQLAlchemyError
            Database row failed to write.
        """
        # Don't include id or null fields in query
        unique_data = {
            k: v for k, v in row.model_dump().items() if v is not None and k != "id"
        }
        row_ids = self.query(model=row.__class__, **unique_data)

        if row_ids == []:
            return [self.add(row=row)]

        if len(row_ids) > 0:
            return row_ids

        msg = f"Failed to query or add {row = }."
        raise RuntimeError(msg)

    def query(
        self, *, model: type[SQLModelT], **attributes: float | str | None
    ) -> RowIDs:
        """
        Query existing rows based on Class keywords.

        Parameters
        ----------
        model
            Database model class, e.g. CalculationRow or GeometryRow.
        **attributes
            Database model class attributes, e.g. id = 1 or energy = -0.568.

        Returns
        -------
            ids corresponding to entries in model table.
        """
        with self.session() as session:
            statement = select(model)

            # Append Select constructs to statement
            for key, value in attributes.items():
                if hasattr(model, key):
                    # Skip NULL fields
                    if value is None or key == "id":
                        continue
                    statement = statement.where(getattr(model, key) == value)

            ids = [getattr(row, "id", None) for row in session.exec(statement).all()]

            return cast("RowIDs", ids)

    def close(self) -> None:
        """Close the database connection.

        Seems to be needed only for testing with in-memory databases.
        """
        self.engine.dispose()
