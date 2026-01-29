"""Row models for data (energies, gradients, hessians).

Eventually, we may want to make this a submodule with a file for single-point
data and files for other types of data.
"""

from sqlmodel import Field, Relationship, SQLModel

from .calculation import CalculationRow
from .geometry import GeometryRow


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

    geometry_id: int | None = Field(
        default=None, foreign_key="geometry.id", primary_key=True
    )
    calculation_id: int | None = Field(
        default=None, foreign_key="calculation.id", primary_key=True
    )
    value: float

    calculation: CalculationRow = Relationship(back_populates="energy")
    geometry: GeometryRow = Relationship(back_populates="energy")
