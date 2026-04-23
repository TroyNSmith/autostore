"""Test for models module."""

import numpy as np
from automol import Geometry
from automol.geom import geometry_hash

from autostore import (
    Calculation,
    CalculationRow,
    Database,
    GeometryRow,
)
from autostore.models import IdentityRow


def test__calculation_calculation_row_equivalence(
    calc: Calculation, calc_row: CalculationRow
) -> None:
    """Test data persistence for Calculation -> CalculationRow."""
    assert calc.program == calc_row.program
    assert calc.program_keywords == calc_row.program_keywords
    assert calc.super_program == calc_row.super_program
    assert calc.super_keywords == calc_row.super_keywords
    assert calc.cmdline_args == calc_row.cmdline_args
    assert calc.calc_type == calc_row.calc_type
    assert calc.method == calc_row.method
    assert calc.basis == calc_row.basis


def test__calculation_program_input_roundtrip(
    calc_row: CalculationRow, geo_row: GeometryRow
) -> None:
    """Test data persistence in CalculationRow -> ProgramInput -> Geometry roundtrip."""
    prog_inp = calc_row.program_input(input_geo=geo_row)
    calc_row_round_trip = CalculationRow.from_program_input(
        prog_inp=prog_inp, program=calc_row.program
    )
    assert calc_row_round_trip.program == calc_row.program
    assert calc_row_round_trip.program_keywords == calc_row.program_keywords
    assert calc_row_round_trip.super_program == calc_row.super_program
    assert calc_row_round_trip.super_keywords == calc_row.super_keywords
    assert calc_row_round_trip.cmdline_args == calc_row.cmdline_args
    assert calc_row_round_trip.calc_type == calc_row.calc_type
    assert calc_row_round_trip.method == calc_row.method
    assert calc_row_round_trip.basis == calc_row.basis


def test__calculation_dual_program_input_roundtrip(
    dual_calc_row: CalculationRow, geo_row: GeometryRow
) -> None:
    """Test data persistence in CalculationRow -> ProgramInput -> Geometry roundtrip."""
    prog_inp = dual_calc_row.program_input(input_geo=geo_row)
    calc_row_round_trip = CalculationRow.from_program_input(
        prog_inp=prog_inp,
        program=dual_calc_row.super_program,  # ty:ignore[invalid-argument-type]
    )
    assert calc_row_round_trip.program == dual_calc_row.program
    assert calc_row_round_trip.program_keywords == dual_calc_row.program_keywords
    assert calc_row_round_trip.super_program == dual_calc_row.super_program
    assert calc_row_round_trip.super_keywords == dual_calc_row.super_keywords
    assert calc_row_round_trip.cmdline_args == dual_calc_row.cmdline_args
    assert calc_row_round_trip.calc_type == dual_calc_row.calc_type
    assert calc_row_round_trip.method == dual_calc_row.method
    assert calc_row_round_trip.basis == dual_calc_row.basis


def test__geometry_geometry_row_equivalence(geo: Geometry) -> None:
    """Test data persistence for Geometry -> GeometryRow."""
    geo_row = GeometryRow.from_geometry(geo=geo)
    assert np.array_equal(a1=geo_row.symbols, a2=geo.symbols)
    assert np.allclose(a=geo_row.coordinates, b=geo.coordinates)
    assert geo_row.charge == geo.charge
    assert geo_row.spin == geo_row.spin


def test__geometry_structure_roundtrip(geo_row: GeometryRow) -> None:
    """Test data persistence in Geometry -> Structure -> Geometry roundtrip."""
    struc = geo_row.structure()
    geo_row_round_trip = GeometryRow.from_structure(struc=struc)
    assert np.array_equal(a1=geo_row.symbols, a2=geo_row_round_trip.symbols)
    assert np.allclose(a=geo_row.coordinates, b=geo_row_round_trip.coordinates)
    assert geo_row.charge == geo_row_round_trip.charge
    assert geo_row.spin == geo_row_round_trip.spin
    assert geo_row.hash == geometry_hash(geo=geo_row_round_trip)


def test__stationary_point_inchi(filled_database: Database) -> None:
    """Test InChI identity tagging upon StationaryRow addition."""
    idnty_rows = filled_database.query(model=IdentityRow, algorithm="InChI")
    assert idnty_rows[0] is not None
    idnty_row = filled_database.get(model=IdentityRow, row_id=idnty_rows[0])
    assert idnty_row.value is not None
