"""Fetch rows from database."""

from automol import Geometry, geometry_hash
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
        EnergyRow.calculation.hashes
        EnergyRow.geometry
        EnergyRow.geometry.stationary_point
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
                # Pre-load calculation and child hashes
                joinedload(EnergyRow.calculation).selectinload(CalculationRow.hashes),  # ty:ignore[invalid-argument-type]
                # Pre-load geometry and child stationary point
                joinedload(EnergyRow.geometry).selectinload(  # ty:ignore[invalid-argument-type]
                    GeometryRow.stationary_point  # ty:ignore[invalid-argument-type]
                ),
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
        GeometryRow.energies.calculation
    """
    with db.session() as session:
        statement = (
            select(GeometryRow)
            .where(GeometryRow.hash == geo_hash)
            .options(
                selectinload(GeometryRow.stationary_point),  # ty:ignore[invalid-argument-type]
                selectinload(GeometryRow.energies).joinedload(EnergyRow.calculation),  # ty:ignore[invalid-argument-type]
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
        IdentityRow.calculation
        IdentityRow.calculation.hashes
        IdentityRow.geometry
    """
    with db.session() as session:
        statement = (
            select(IdentityRow)
            .where(
                IdentityRow.algorithm == algorithm,
                IdentityRow.identifier == identifier,
            )
            .options(
                selectinload(IdentityRow.stationary_points).options(  # ty:ignore[invalid-argument-type]
                    joinedload(StationaryPointRow.calculation).selectinload(  # ty:ignore[invalid-argument-type]
                        CalculationRow.hashes  # ty:ignore[invalid-argument-type]
                    ),
                    joinedload(StationaryPointRow.geometry),  # ty:ignore[invalid-argument-type]
                )
            )
        )
        return session.exec(statement).first()
