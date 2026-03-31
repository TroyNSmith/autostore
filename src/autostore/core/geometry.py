"""Functions and events for GeometryRow object."""

import automol
from automol import Geometry, geom
from sqlalchemy import event

from ..models import GeometryRow


def row_to_geometry(geo_row: GeometryRow) -> Geometry:
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


def row_from_geometry(geo: Geometry) -> GeometryRow:
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


def row_from_smiles(smi: str) -> GeometryRow:
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
    geo = automol.geom.geo_from_smiles(smi)
    return row_from_geometry(geo)


def row_to_inchi(geo_row: GeometryRow) -> str:
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
    geo = row_to_geometry(geo_row)
    return automol.geom.geo_to_inchi(geo)


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
