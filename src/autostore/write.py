"""Write to database."""

from qcio import Results

from .database import Database
from .models import CalculationRow, EnergyRow, GeometryRow


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
