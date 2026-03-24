"""Fetch rows from database."""

from sqlalchemy.orm import selectinload
from sqlmodel import select

from .database import Database
from .models import CalculationRow, IdentityRow, StationaryPointRow


def identity(algorithm: str, identifier: str, *, db: Database) -> IdentityRow | None:
    """Fetch the Identity record and preloads associated stationary points."""
    with db.session() as session:
        return session.exec(
            select(IdentityRow)
            .where(
                IdentityRow.algorithm == algorithm,
                IdentityRow.identifier == identifier,
            )
            .options(
                selectinload(IdentityRow.stationary_points)  # ty:ignore[invalid-argument-type]
                .selectinload(StationaryPointRow.calculation)  # ty:ignore[invalid-argument-type]
                .selectinload(CalculationRow.hashes),  # ty:ignore[invalid-argument-type]
                selectinload(IdentityRow.stationary_points).selectinload(  # ty:ignore[invalid-argument-type]
                    StationaryPointRow.geometry  # ty:ignore[invalid-argument-type]
                ),
            )
        ).first()
