"""autostore tests."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from automol import Geometry
from qcdata import CalcType, ProgramOutput
from sqlalchemy import Select

from autostore import Calculation, Database, models, qc


@pytest.fixture
def database() -> Iterator[Database]:
    """In-memory database fixture."""
    db = Database(":memory:")
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def water() -> Geometry:
    """Water geometry fixture."""
    return Geometry(
        symbols=["O", "H", "H"],
        coordinates=[[0, 0, 0], [1, 0, 0], [0, 1, 0]],  # ty:ignore[invalid-argument-type]
    )


@pytest.fixture
def h2() -> Geometry:
    """Water geometry fixture."""
    return Geometry(
        symbols=["H", "H"],
        coordinates=[[0, 0, 0], [0, 0.74, 0]],  # ty:ignore[invalid-argument-type]
    )


@pytest.fixture
def xtb_calculation() -> Calculation:
    """XTB calculation fixture."""
    return Calculation(program="crest", method="gfnff")


@pytest.fixture
def water_xtb_energy_results() -> ProgramOutput:
    """Water energy calculation results fixture."""
    return ProgramOutput.model_validate(
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


@pytest.fixture
def h2_gfnff_stationary_results() -> ProgramOutput:
    """Water energy calculation results fixture."""
    with (Path(__file__).parent / "stationary.json").open(encoding="utf-8") as f:
        data = json.load(f)

    return ProgramOutput.model_validate(data)


def test_energy(
    water: Geometry,
    water_xtb_energy_results: ProgramOutput,
    database: Database,
) -> None:
    """Test writing and reading of the energy and corresponding database rows."""
    # Instantiate GeometryRow & write to database
    geom_row = models.GeometryRow(**water.model_dump())
    geom_id = database.write(row=geom_row)
    # Ensure id returned
    assert geom_id is not None

    # Instantiate CalculationRow & write to database
    calc_row = qc.prog_output.calc_row(water_xtb_energy_results)
    calc_id = database.write(row=calc_row)
    # Ensure id returned
    assert calc_id is not None

    # Instantiate CalculationGeometryLinkRow & write to database
    calc_geom_link = models.CalculationGeometryLink(
        geometry_id=geom_id, calculation_id=calc_id, role="input"
    )
    link_id = database.write(row=calc_geom_link)
    # Ensure id not returned
    assert link_id is None

    # Instantiate EnergyRow & write to database
    ene_row = models.EnergyRow(
        geometry_id=geom_id,
        calculation_id=calc_id,
        value=water_xtb_energy_results.data.energy,
    )
    ene_id = database.write(row=ene_row)
    # Ensure id returned
    assert ene_id is not None

    with database.session() as session:
        # Ensure CalculationRow was correctly written
        calc_row = session.get(models.CalculationRow, calc_id)
        assert calc_row is not None
        assert calc_row.calctype == CalcType.energy

        # Ensure GeometryRow was correctly written
        geom_row = session.get(models.GeometryRow, geom_id)
        assert geom_row is not None
        assert geom_row.hash == water.hash

        # Ensure Calculation and Geometry are linked
        session.refresh(calc_row, attribute_names=["geometries"])
        session.refresh(geom_row, attribute_names=["calculations"])
        assert calc_row.geometries[0].id == geom_id
        assert geom_row.calculations[0].id == calc_id

        # Ensure EnergyRow was correctly written
        ene_row = session.get(models.EnergyRow, ene_id)
        assert ene_row is not None
        assert ene_row.value == -5.062316802835694  # noqa: PLR2004


def test_stationary(
    h2: Geometry,
    h2_gfnff_stationary_results: ProgramOutput,
    database: Database,
) -> None:
    """Test writing and reading of the energy and corresponding database rows."""
    # Instantiate input GeometryRow & write to database
    inp_geom_row = models.GeometryRow(**h2.model_dump())
    inp_geom_id = database.write(row=inp_geom_row)
    assert inp_geom_id is not None

    # Instantiate CalculationRow & write to database
    calc_row = qc.prog_output.calc_row(h2_gfnff_stationary_results)
    calc_id = database.write(row=calc_row)
    assert calc_id is not None

    # Instantiate output GeometryRow & write to database
    out_geom_row = qc.prog_output.geom_row(h2_gfnff_stationary_results)
    out_geom_id = database.write(row=out_geom_row)
    assert out_geom_id is not None
    # Test for the database.query() method
    assert inp_geom_id not in database.query(
        model=models.GeometryRow, **out_geom_row.model_dump()
    )

    # Instantiate CalculationGeometryLinkRows & write to database
    calc_inp_link = models.CalculationGeometryLink(
        geometry_id=inp_geom_id, calculation_id=calc_id, role="input"
    )
    database.write(row=calc_inp_link)

    calc_out_link = models.CalculationGeometryLink(
        geometry_id=out_geom_id, calculation_id=calc_id, role="output"
    )
    database.write(row=calc_out_link)

    # Instantiate StationaryPointRow & write to database
    stp_row = models.StationaryPointRow(
        geometry_id=out_geom_id, calculation_id=calc_id, order=1
    )
    stp_id = database.write(row=stp_row)
    assert stp_id is not None
    # Test for the database.fetch() method
    assert stp_row == database.fetch(model=models.StationaryPointRow, row_id=stp_id)

    with database.session() as session:
        # Ensure geometry input and geometry output are unique
        statement = (
            Select(models.CalculationGeometryLink)
            .where(models.CalculationGeometryLink.calculation_id == calc_id)  # ty:ignore[invalid-argument-type]
            .where(models.CalculationGeometryLink.geometry_id == inp_geom_id)  # ty:ignore[invalid-argument-type]
        )
        calc_inp_link = session.exec(statement).first()[0]  # ty:ignore[no-matching-overload]
        assert calc_inp_link.role == "input"

        statement = (
            Select(models.CalculationGeometryLink)
            .where(models.CalculationGeometryLink.calculation_id == calc_id)  # ty:ignore[invalid-argument-type]
            .where(models.CalculationGeometryLink.geometry_id == out_geom_id)  # ty:ignore[invalid-argument-type]
        )
        calc_out_link = session.exec(statement).first()[0]  # ty:ignore[no-matching-overload]
        assert calc_out_link.role == "output"

        assert calc_inp_link != calc_out_link
