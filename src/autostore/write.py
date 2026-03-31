"""Write to database."""

from .database import Database
from .models import CalculationRow, EnergyRow, GeometryRow, StationaryPointRow


def calculation(*, calc_row: CalculationRow, db: Database) -> None:
    """
    Write CalculationRow to database.

    Parameters
    ----------
    calc_row
        CalculationRow object.
    db
        Database connection manager.
    """
    with db.session() as session:
        session.add(calc_row)
        session.commit()


def geometry(*, geo_row: GeometryRow, db: Database) -> None:
    """
    Write GeometryRow to database.

    Parameters
    ----------
    res
        qcio Results object
    db
        Database connection manager.
    """
    with db.session() as session:
        session.add(geo_row)
        session.commit()


def energy(
    value: float, *, calc_row: CalculationRow, geo_row: GeometryRow, db: Database
) -> EnergyRow:
    """
    Write energy value to database.

    Parameters
    ----------
    value
        Energy result.
    calc_row
        Associated CalculationRow object.
    geo_row
        Associated GeometryRow object.
    db
        Database connection manager.

    Returns
    -------
    EnergyRow
        EnergyRow entry with linked GeometryRow and CalculationRow models.
    """
    with db.session() as session:
        ene_row = EnergyRow(value=value, calculation=calc_row, geometry=geo_row)

        session.add(ene_row)
        session.commit()
        session.refresh(ene_row, attribute_names=["calculation", "geometry"])

        return ene_row


def stationary_point(
    order: int, *, calc_row: CalculationRow, geo_row: GeometryRow, db: Database
) -> StationaryPointRow:
    """
    Write stationary point to database.

    Parameters
    ----------
    order
        Order of the stationary point (e.g., minimum = 0, transition = 1)
    calc_row
        Associated CalculationRow object.
    geo_row
        Associated GeometryRow object.
    db
        Database connection manager.

    Returns
    -------
    StationaryPointRow
        StationaryPointRow entry with linked GeometryRow and CalculationRow models.
    """
    with db.session() as session:
        stp_row = StationaryPointRow(
            order=order, geometry=geo_row, calculation=calc_row
        )

        session.add(stp_row)
        session.commit()
        session.refresh(stp_row, attribute_names=["calculation", "geometry"])

        return stp_row
