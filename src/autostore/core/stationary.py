"""Functions and events for CalculationRow object."""

from sqlalchemy import event
from sqlmodel import Session

from ..models import IdentityRow, StationaryIdentityLink, StationaryPointRow
from . import geometry


@event.listens_for(StationaryPointRow, "after_insert")
def generate_stationary_inchi(mapper, connection, target: StationaryPointRow) -> None:  # noqa: ANN001, ARG001
    """Automatically generates InChI identity after a StationaryPointRow is inserted."""
    session = Session(bind=connection)

    try:
        # NOTE: If target.geometry isn't loaded, we need to fetch it
        geo_row = target.geometry
        inchi_string = geometry.row_to_inchi(geo_row)

        identity: IdentityRow | None = (
            session.query(IdentityRow)
            .filter_by(algorithm="InChI", identifier=inchi_string)
            .first()
        )

        if not identity:
            identity = IdentityRow(
                type="stereoisomer",
                algorithm="InChI",
                identifier=inchi_string,
            )
            session.add(identity)
            session.flush()

        link_exists = (
            session.query(StationaryIdentityLink)
            .filter_by(stationary_id=target.id, identity_id=identity.id)
            .first()
        )

        if not link_exists:
            new_link = StationaryIdentityLink(
                stationary_id=target.id, identity_id=identity.id
            )
            session.add(new_link)

        session.commit()

    except Exception as e:
        session.rollback()
        msg = f"Failed to generate InChI {target.id}"
        raise RuntimeError(msg) from e

    finally:
        session.close()
