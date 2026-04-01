"""Row models for data (energies, gradients, hessians).

Eventually, we may want to make this a submodule with a file for single-point
data and files for other types of data.
"""

from sqlmodel import Field, Relationship, SQLModel

from .calculation import CalculationRow
from .geometry import GeometryRow
from .stationary import StationaryPointRow


class EnergyRow(SQLModel, table=True):
    """
    Energy table row.

    Parameters
    ----------
    geometry_id
        Foreign key referencing the geometry table; part of the composite primary key.
    calculation_id
        Foreign key referencing the calculation table; part of the composite
        primary key.
    value
        Energy in Hartree.

    calculation
        Relationship to the associated calculation record.
    geometry
        Relationship to the associated geometry record.
    """

    __tablename__ = "energy"

    id: int | None = Field(default=None, primary_key=True)

    geometry_id: int | None = Field(
        default=None, foreign_key="geometry.id", ondelete="CASCADE"
    )
    calculation_id: int | None = Field(
        default=None, foreign_key="calculation.id", ondelete="CASCADE"
    )

    value: float

    calculation: CalculationRow = Relationship(back_populates="energies")
    geometry: GeometryRow = Relationship(back_populates="energies")
    stationary_point: StationaryPointRow = Relationship(back_populates="energy")
