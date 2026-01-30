"""autostore tests."""

from collections.abc import Iterator

import pytest
from qcio import Results
from sqlmodel import select

from autostore import Database, EnergyRow, write


@pytest.fixture
def database() -> Iterator[Database]:
    """In-memory database fixture."""
    db = Database(":memory:")
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def water_energy_results() -> Results:
    """Water energy calculation results fixture."""
    return Results.model_validate(
        {
            "input_data": {
                "structure": {
                    "symbols": ["O", "H", "H"],
                    "geometry": [
                        [0.0, 0.0, 0.0],
                        [1.8897261259082012, 0.0, 0.0],
                        [0.0, 1.8897261259082012, 0.0],
                    ],
                    "charge": 0,
                    "multiplicity": 1,
                },
                "model": {"method": "gfn2", "basis": None},
                "calctype": "energy",
            },
            "success": True,
            "data": {"energy": -5.062316802835694},
            "provenance": {"program": "crest", "program_version": "3.0.2"},
        }
    )


def test_energy(water_energy_results: Results, database: Database) -> None:
    """Stub test to ensure the test suite runs."""
    write.energy(water_energy_results, database)

    with database.session() as session:
        ene_rows = session.exec(select(EnergyRow)).all()
        for ene_row in ene_rows:
            print(repr(ene_row))  # noqa: T201


def test_energy_rows_are_related(
    water_energy_results: Results, database: Database
) -> None:
    """Ensure energy, geometry, and calculation rows are correctly related."""
    write.energy(water_energy_results, database)

    with database.session() as session:
        # --- energy row exists---
        energies = session.exec(select(EnergyRow)).all()
        assert len(energies) == 1

        energy = energies[0]
        assert energy.value == water_energy_results.data.energy

        # --- foreign keys populated ---
        assert energy.geometry_id is not None
        assert energy.calculation_id is not None

        # --- forward relationships ---
        assert energy.geometry is not None
        assert energy.calculation is not None

        # --- reverse relationships ---
        assert energy in energy.geometry.energy
        assert energy == energy.calculation.energy

        # --- linked data checks ---
        assert energy.geometry.symbols == ["O", "H", "H"]
        assert energy.calculation.method == "gfn2"
