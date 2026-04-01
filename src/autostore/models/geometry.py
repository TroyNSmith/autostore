"""Geometry row model and associated models."""

from typing import TYPE_CHECKING

import automol
from automol import Geometry, geom
from automol.types import FloatArray
from pydantic import ConfigDict
from sqlalchemy import event
from sqlalchemy.types import JSON, String
from sqlmodel import Column, Field, Relationship, SQLModel

from ..types import FloatArrayTypeDecorator

if TYPE_CHECKING:
    from .data import EnergyRow
    from .stationary import StationaryPointRow


class GeometryRow(SQLModel, table=True):
    """
    Molecular geometry table row.

    Parameters
    ----------
    id
        Primary key.
    symbols
        Atomic symbols in order (e.g., ``["H", "O", "H"]``).
        The length of ``symbols`` must match the number of atoms.
    coordinates
        Cartesian coordinates of the atoms in Angstroms.
        Shape is ``(len(symbols), 3)`` and the ordering corresponds to ``symbols``.
    charge
        Total molecular charge.
    spin
        Number of unpaired electrons, i.e. two times the spin quantum number (``2S``).
    hash
        Optional hash of the geometry for quick comparisons.
    energy
        Relationship to the associated energy record, if present.
    """

    __tablename__ = "geometry"

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int | None = Field(default=None, primary_key=True)
    symbols: list[str] = Field(sa_column=Column(JSON))
    coordinates: FloatArray = Field(sa_column=Column(FloatArrayTypeDecorator))
    charge: int = 0
    spin: int = 0
    hash: str = Field(
        sa_column=Column(String(64), index=True, nullable=True, unique=True)
    )
    # ^ Populated by event listener below

    energies: list["EnergyRow"] = Relationship(
        back_populates="geometry", cascade_delete=True
    )
    stationary_point: "StationaryPointRow" = Relationship(back_populates="geometry")

    # Validate coordinates shape with a field validator:
    #    @field_validator("coordinates")
    #    @classmethod
    #    def validate_shape(cls, v):
    #        if not all(len(row) == 3 for row in v):
    #            raise ValueError("Coordinates must be shape (N, 3)")  # noqa: ERA001
    #        return v  # noqa: ERA001

    # Add formula field for indexing:
    #    formula: str = Field(sa_column=Column(String, nullable=False, index=True))  # noqa: E501, ERA001

    # Define symbols -> formula conversion function:
    #    def formula_from_symbols(symbols: list[str]) -> str

    # Attach SQLAlchemy event listener to auto-set formula on insert:
    #     from sqlalchemy import event  # noqa: ERA001
    #     @event.listens_for(GeometryRow, "before_insert")
    #     @event.listens_for(GeometryRow, "before_update")
    #     def populate_formula(mapper, connection, target: GeometryRow):
    #         target.formula = formula_from_symbols(target.symbols)  # noqa: ERA001
    # This will implement the symbol-formula sync at the ORM level, so that they
    # automatically stay in sync with any inserts or updates.


def automol_geometry(geo_row: GeometryRow) -> Geometry:
    """
    Instantiate automol Geometry from GeometryRow.

    Parameters
    ----------
    geo_row
        AutoStore GeometryRow object.

    Returns
    -------
        Geometry
    """
    return Geometry(
        symbols=geo_row.symbols,
        coordinates=geo_row.coordinates,
        charge=geo_row.charge,
        spin=geo_row.spin,
    )


def from_automol_geometry(geo: Geometry) -> GeometryRow:
    """
    Instantiate GeometryRow from automol Geometry.

    Parameters
    ----------
    geo
        AutoMol Geometry object.

    Returns
    -------
        GeometryRow
    """
    return GeometryRow(
        symbols=geo.symbols,
        coordinates=geo.coordinates,
        charge=geo.charge,
        spin=geo.spin,
    )


def from_smiles(smi: str) -> GeometryRow:
    """
    Instantiate automol Geometry from GeometryRow.

    Parameters
    ----------
    smi
        SMILES string.

    Returns
    -------
        GeometryRow
    """
    geo = automol.geom.from_smiles(smi)
    return from_automol_geometry(geo)


def inchi(geo_row: GeometryRow) -> str:
    """
    Provide InChI string from AutoMol Geometry.

    Parameters
    ----------
    geo_row
        AutoStore GeometryRow object.

    Returns
    -------
        InChI string.
    """
    geo = automol_geometry(geo_row)
    return automol.geom.inchi(geo)


# Listeners
@event.listens_for(GeometryRow, "before_insert")
def populate_geometry_hash(mapper, connection, target: GeometryRow) -> None:  # noqa: ANN001, ARG001
    """Populate GeometryRow hash before inserts and updates."""
    geo = Geometry(
        symbols=target.symbols,
        coordinates=target.coordinates,
        charge=target.charge,
        spin=target.spin,
    )
    target.hash = geom.geometry_hash(geo)
