"""Functions and events for CalculationRow object."""

from sqlalchemy import event
from sqlmodel import Session

from ..calcn import calculation_hash, hash_registry
from ..models import CalculationHashRow, CalculationRow


@event.listens_for(Session, "after_flush")
def populate_calculation_hashes(session, flush_context) -> None:  # noqa: ANN001, ARG001
    """Populate the 'minimal' hash for newly added CalculationRow objects."""
    available = set(hash_registry.available())

    for row in session.new:
        if not isinstance(row, CalculationRow):
            continue

        existing = {h.name for h in row.hashes}
        missing = available - existing
        if not missing:
            continue

        calc = row

        for name in missing:
            value = calculation_hash(calc, name=name)

            session.add(
                CalculationHashRow(
                    calculation=row,
                    name=name,
                    value=value,
                )
            )
