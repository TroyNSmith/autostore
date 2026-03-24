"""Write to database."""

from qcio import Results

from .database import Database
from .models import CalculationRow, EnergyRow, GeometryRow, StationaryPointRow


def energy(res: Results, db: Database) -> None:
    """
    Write energy to database.

    Parameters
    ----------
    res
        Calculation results.
    db
        Database connection manager.
    """
    with db.session() as session:
        geo_row = GeometryRow.from_results(res)
        calc_row = CalculationRow.from_results(res)
        ene_row = EnergyRow(
            value=res.data.energy, calculation=calc_row, geometry=geo_row
        )

        session.add(ene_row)
        session.commit()


def stationary_point(res: Results, db: Database, *, order: int) -> StationaryPointRow:
    """
    Write stationary point to database.

    Parameters
    ----------
    res
        Calculation results.
    db
        Database connection manager.
    order
        Order of the stationary point (e.g., minimum = 0, transition = 1)

    """
    with db.session() as session:
        geo_row = GeometryRow.from_results(res)
        calc_row = CalculationRow.from_results(res)

        stp_row = StationaryPointRow(
            geometry=geo_row, calculation=calc_row, order=order
        )

        session.add(stp_row)
        session.commit()

        session.refresh(stp_row, attribute_names=["geometry", "calculation"])

        return stp_row
