"""QCIO Results interface."""

from qcio import DualProgramInput, ProgramInput, Results

from ..models import CalculationRow, GeometryRow
from . import structure


def res_to_rows(res: Results) -> tuple[CalculationRow, GeometryRow]:
    """
    Instantiate CalculationRow and GeometryRow from a qcio Results object.

    Parameters
    ----------
    res
        qcio Results object.

    Returns
    -------
        tuple[CalculationRow, GeometryRow]

    Raises
    ------
    NotImplementedError
        If instantiation from the given input data type is not implemented.
    """
    prog_input = res.input_data
    prov = res.provenance

    # Fields shared by all results
    data = {
        "files": prog_input.files,
        "scratch_dir": prov.scratch_dir,
        "wall_time": prov.wall_time,
        "hostname": prov.hostname,
        "hostcpus": prov.hostcpus,
        "hostmem": prov.hostmem,
        "extras": prog_input.extras,
    }

    # Dual vs Single program inputs
    if isinstance(prog_input, DualProgramInput):
        calc_row = CalculationRow(
            program=prog_input.subprogram,
            method=prog_input.subprogram_args.model.method,
            basis=prog_input.subprogram_args.model.basis,
            input=None,  # Could store input file text here if desired
            keywords=prog_input.subprogram_args.keywords,
            superprogram_keywords=prog_input.keywords,
            cmdline_args=prog_input.cmdline_args,
            calctype=prog_input.calctype,
            program_version=res.provenance.extras.get("versions", {}).get(
                prog_input.subprogram
            ),  # NOTE: This is a placeholder for getting the subversion
            superprogram=res.provenance.program,
            superprogram_version=res.provenance.program_version,
            **data,  # ty:ignore[invalid-argument-type]
        )

    elif isinstance(prog_input, ProgramInput):
        calc_row = CalculationRow(
            program=res.provenance.program,
            method=prog_input.model.method,
            basis=prog_input.model.basis,
            input=None,  # Could store input file text here if desired
            keywords=prog_input.keywords,
            cmdline_args=prog_input.cmdline_args,
            calctype=prog_input.calctype,
            program_version=res.provenance.program_version,
            **data,  # ty:ignore[invalid-argument-type]
        )

    else:
        msg = f"Instantiation from {type(prog_input)} not implemented."
        raise NotImplementedError(msg)

    if hasattr(res.data, "final_structure") and res.data.final_structure:
        struct = res.data.final_structure

    elif isinstance(res.input_data, ProgramInput):
        struct = res.input_data.structure

    else:
        msg = f"Instantiation from {type(res.input_data)} not yet implemented."
        raise NotImplementedError(msg)

    geo_row = structure.struc_to_row(struct)

    return (calc_row, geo_row)
