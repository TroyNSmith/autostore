"""Stationary row model and associated models and functions."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel, select

if TYPE_CHECKING:
    from .calculation import CalculationRow
    from .data import EnergyRow
    from .geometry import GeometryRow

from sqlalchemy import event
from sqlmodel import Session

from . import geometry


class StationaryIdentityLink(SQLModel, table=True):
    """
    Stationary point to identity link row.

    Parameters
    ----------
    stationary_id
        Foreign key to the associated molecular structure; part of the
        composite primary key.
    identity_id
        Foreign key to the calculation producing the stationary point; part of
        the composite primary key.
    """

    __tablename__ = "stationary_identity_link"

    stationary_id: int = Field(foreign_key="stationary_point.id", primary_key=True)
    identity_id: int = Field(foreign_key="identity.id", primary_key=True)


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
        Order of the stationary point (e.g., minimum = 0, transition = 1)

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
    energy_id: int | None = Field(default=None, foreign_key="energy.id")

    order: int | None = Field(default=-1)

    geometry: "GeometryRow" = Relationship(back_populates="stationary_point")
    calculation: "CalculationRow" = Relationship(back_populates="stationary_points")
    energy: "EnergyRow" = Relationship(back_populates="stationary_point")

    identities: list["IdentityRow"] = Relationship(
        back_populates="stationary_points", link_model=StationaryIdentityLink
    )


class IdentityRow(SQLModel, table=True):
    """
    Stationary point identity row.

    Parameters
    ----------
    id
        Primary key.
    type
        The category this identity falls within (e.g., "stereoisomer").
    algorithm
        Method used to determine this identity (e.g., "InChI").
    identifier
        Value produced by the identity algorithm.
    """

    __tablename__ = "identity"

    id: int | None = Field(default=None, primary_key=True)

    type: str
    algorithm: str
    identifier: str

    stationary_points: list["StationaryPointRow"] = Relationship(
        back_populates="identities", link_model=StationaryIdentityLink
    )


@event.listens_for(StationaryPointRow, "after_insert")
def generate_stationary_inchi(mapper, connection, target: StationaryPointRow) -> None:  # noqa: ANN001, ARG001
    """Automatically generates InChI identity after a StationaryPointRow is inserted."""
    session = Session(bind=connection)

    try:
        # NOTE: If target.geometry isn't loaded, we need to fetch it
        stp_row = target
        geo_row = stp_row.geometry
        inchi_string = geometry.inchi(geo_row)

        statement = select(IdentityRow).where(
            IdentityRow.algorithm == "InChI", IdentityRow.identifier == inchi_string
        )
        id_row = session.exec(statement).first()

        if id_row is None:
            id_row = IdentityRow(
                type="stereoisomer",
                algorithm="InChI",
                identifier=inchi_string,
            )
            session.add(id_row)
            session.flush()

        link = StationaryIdentityLink(stationary_id=stp_row.id, identity_id=id_row.id)
        session.add(link)

        session.commit()

    except Exception as e:
        session.rollback()
        msg = f"Failed to generate InChI {target.id}"
        raise RuntimeError(msg) from e
