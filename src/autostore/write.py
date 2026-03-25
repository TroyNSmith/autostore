"""Write to database."""

from .database import Database
from .models import CalculationRow, EnergyRow, GeometryRow, StationaryPointRow


def energy(
    geo_row: GeometryRow, calc_row: CalculationRow, *, value: float, db: Database
) -> EnergyRow:
    """
    Write energy to database.

    Parameters
    ----------
    value
        Energy result.
    geo_row
        Associated GeometryRow object.
    calc_row
        Associated CalculationRow object.
    db
        Database connection manager.
    """
    with db.session() as session:
        ene_row = EnergyRow(value=value, calculation=calc_row, geometry=geo_row)

        session.add(ene_row)
        session.commit()
        session.refresh(ene_row, attribute_names=["geometry", "calculation"])

        return ene_row


def stationary_point(
    geo_row: GeometryRow, calc_row: CalculationRow, *, order: int, db: Database
) -> StationaryPointRow:
    """
    Write stationary point to database.

    Parameters
    ----------
    geo_row
        Associated GeometryRow object.
    calc_row
        Associated CalculationRow object.
    db
        Database connection manager.
    order
        Order of the stationary point (e.g., minimum = 0, transition = 1)
    """
    with db.session() as session:
        stp_row = StationaryPointRow(
            geometry=geo_row, calculation=calc_row, order=order
        )

        session.add(stp_row)
        session.commit()
        session.refresh(stp_row, attribute_names=["geometry", "calculation"])

        return stp_row
