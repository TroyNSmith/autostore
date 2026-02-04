"""Read values from database."""

from automol import Geometry, geometry_hash
from sqlmodel import select

from .calcn import Calculation, calculation_hash
from .database import Database
from .models import CalculationHashRow, CalculationRow, EnergyRow, GeometryRow


def energy(
    geo: Geometry, calc: Calculation, *, db: Database, hash_name: str = "minimal"
) -> float | None:
    """
    Read energy from database.

    Parameters
    ----------
    geo
        Geometry.
    calc
        Calculation metadata.
    db
        Database connection manager.
    hash_name
        Calculation hash type.

    Returns
    -------
        Energy in Hartree, or None if not found.
    """
    geo_hash = geometry_hash(geo)
    calc_hash = calculation_hash(calc, name=hash_name)
    with db.session() as session:
        ene_row = session.exec(
            select(EnergyRow)
            .join(GeometryRow)
            .join(CalculationRow)
            .join(CalculationHashRow)
            .where(
                GeometryRow.hash == geo_hash,
                CalculationHashRow.value == calc_hash,
                CalculationHashRow.name == hash_name,
            )
        ).first()
        if ene_row is not None:
            return ene_row.value
    return None
