"""Fetch rows from database."""

from automol import Geometry, geometry_hash
from sqlalchemy import Sequence
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select

from .calcn import Calculation, calculation_hash
from .database import Database
from .models import (
    CalculationHashRow,
    CalculationRow,
    EnergyRow,
    GeometryRow,
    IdentityRow,
    StationaryPointRow,
)


def energy(
    geo: Geometry, calc: Calculation, *, hash_name: str = "minimal", db: Database
) -> EnergyRow | None:
    """
    Fetch EnergyRow and pre-load linked models.

    Parameters
    ----------
    geo
        Geometry.
    calc
        Calculation metadata.
    hash_name
        Calculation hash type.
    db
        Database connection manager.

    Returns
    -------
        EnergyRow.

    Linked Model Attributes
    -----------------------
        EnergyRow.calculation
        EnergyRow.geometry
    """
    geo_hash = geometry_hash(geo)
    calc_hash = calculation_hash(calc, name=hash_name)

    with db.session() as session:
        statement = (
            select(EnergyRow)
            .join(GeometryRow)
            .join(CalculationRow)
            .join(CalculationHashRow)
            .where(
                GeometryRow.hash == geo_hash,
                CalculationHashRow.value == calc_hash,
                CalculationHashRow.name == hash_name,
            )
            .options(
                # Pre-load calculation
                joinedload(EnergyRow.calculation),  # ty:ignore[invalid-argument-type]
                # Pre-load geometry
                joinedload(EnergyRow.geometry),  # ty:ignore[invalid-argument-type]
            )
        )
        return session.exec(statement).first()


def geometry(geo_hash: str, *, db: Database) -> GeometryRow | None:
    """
    Fetch GeometryRow and pre-load linked models.

    Parameters
    ----------
    geo_hash
        Geometry hash.
    db
        Database connection manager.

    Returns
    -------
        GeometryRow.

    Linked Model Attributes
    -----------------------
        GeometryRow.stationary_point
        GeometryRow.energies
    """
    with db.session() as session:
        statement = (
            select(GeometryRow)
            .where(GeometryRow.hash == geo_hash)
            .options(
                selectinload(GeometryRow.stationary_point),  # ty:ignore[invalid-argument-type]
                selectinload(GeometryRow.energies),  # ty:ignore[invalid-argument-type]
            )
        )
        return session.exec(statement).first()


def identity(algorithm: str, identifier: str, *, db: Database) -> IdentityRow | None:
    """
    Fetch IdentityRow and pre-load linked models.

    Parameters
    ----------
    algorithm
        Method used to label identity (e.g. "InChI").
    identifier
        Unique identity produced by algorithm.
    db
        Database connection manager.

    Returns
    -------
        IdentityRow.

    Linked Model Attributes
    -----------------------
        IdentityRow.stationary_points
    """
    with db.session() as session:
        statement = (
            select(IdentityRow)
            .where(
                IdentityRow.algorithm == algorithm,
                IdentityRow.identifier == identifier,
            )
            .options(
                selectinload(IdentityRow.stationary_points)  # ty:ignore[invalid-argument-type]
            )
        )
        return session.exec(statement).first()


def stationary_point(
    algorithm: str,
    identifier: str,
    calc_hash: str,
    *,
    hash_name: str = "minimal",
    db: Database,
) -> Sequence[StationaryPointRow] | None:
    """
    Fetch StationaryPointRow and pre-load linked models.

    Parameters
    ----------
    algorithm
        Method used to label identity (e.g. "InChI").
    identifier
        Unique identity produced by algorithm.
    hash_name
        Type of calculation hash to compare against (e.g. "minimal" or "full").
    db
        Database connection manager.

    Returns
    -------
        IdentityRow.

    Linked Model Attributes
    -----------------------
        StationaryPointRow.geometry
        StationaryPointRow.calculation
        StationaryPointRow.energy
        StationaryPointRow.identities
    """
    with db.session() as session:
        statement = (
            select(StationaryPointRow)
            .join(StationaryPointRow.identities)  # ty:ignore[invalid-argument-type]
            .join(StationaryPointRow.calculation)  # ty:ignore[invalid-argument-type]
            .join(CalculationRow.hashes)  # ty:ignore[invalid-argument-type]
            .where(
                IdentityRow.algorithm == algorithm,
                IdentityRow.identifier == identifier,
                CalculationHashRow.name == hash_name,
                CalculationHashRow.value == calc_hash,
            )
            # Initializes geometry, calculation, energy, and identities linked fields
            .options(
                selectinload(StationaryPointRow.geometry),  # ty:ignore[invalid-argument-type]
                selectinload(StationaryPointRow.calculation),  # ty:ignore[invalid-argument-type]
                selectinload(StationaryPointRow.energy),  # ty:ignore[invalid-argument-type]
                selectinload(StationaryPointRow.identities),  # ty:ignore[invalid-argument-type]
            )
        )
        return session.exec(statement).all()
