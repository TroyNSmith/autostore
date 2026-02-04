"""Stationary row model and associated models and functions."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .calculation import CalculationRow
    from .geometry import GeometryRow


class StationaryPointRow(SQLModel, table=True):
    """
    Stationary point table row.

    Stores information about optimized geometries.

    Parameters
    ----------
    id
        Primary key.
    geometry_id
        Foreign key to the associated molecular geometry.
    calculation_id
        Foreign key to the calculation producing the stationary point.
    order
        Order of the stationary point (e.g., minimum = 0, transition = 1, unassigned = -1)

    Linked Models
    -------------
    geometry
        Corresponding molecular geometry row.
    calculation
        Corresponding calculation row.
    stages
        Reaction stages associated with this stationary point.
    identities
        Identities associated with this stationary point.
    """

    __tablename__ = "stationary_point"

    id: int | None = Field(default=None, primary_key=True)

    geometry_id: int = Field(foreign_key="geometry.id")
    calculation_id: int = Field(foreign_key="calculation.id")

    order: int | None = Field(default=-1)

    geometry: "GeometryRow" = Relationship(back_populates="stationary_point")
    calculation: "CalculationRow" = Relationship(back_populates="stationary_point")
