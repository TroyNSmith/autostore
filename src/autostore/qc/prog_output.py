"""qc ProgramOutput interface."""

from qcdata import DualProgramInput, ProgramInput, ProgramOutput

from ..models import CalculationRow, GeometryRow
from . import structure


def calculation_row(res: ProgramOutput) -> CalculationRow:
    """
    Instantiate CalculationRow from ProgramOutput.

    Parameters
    ----------
    res
        qc ProgramOutput object.

    Returns
    -------
        CalculationRow

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
        "input": None,  # Could store input file text here if desired
    }

    # Dual vs Single program inputs
    if isinstance(prog_input, DualProgramInput):
        calc_data = {
            **data,
            "program": prog_input.subprogram,
            "method": prog_input.subprogram_args.model.method,
            "basis": prog_input.subprogram_args.model.basis,
            "keywords": prog_input.subprogram_args.keywords,
            "superprogram_keywords": prog_input.keywords,
            "cmdline_args": prog_input.cmdline_args,
            "calctype": prog_input.calctype,
            "program_version": prov.extras.get("versions", {}).get(
                prog_input.subprogram
            ),
            "superprogram": prov.program,
            "superprogram_version": prov.program_version,
        }
    elif isinstance(prog_input, ProgramInput):
        calc_data = {
            **data,
            "program": prov.program,
            "method": prog_input.model.method,
            "basis": prog_input.model.basis,
            "keywords": prog_input.keywords,
            "cmdline_args": prog_input.cmdline_args,
            "calctype": prog_input.calctype,
            "program_version": prov.program_version,
        }
    else:
        msg = f"Instantiation from {type(prog_input)} not implemented."
        raise NotImplementedError(msg)

    # Validate and return
    return CalculationRow.model_validate(calc_data)


def geometry_row(res: ProgramOutput) -> GeometryRow:
    """
    Instantiate GeometryRow from ProgramOutput.

    Parameters
    ----------
    res
        qc ProgramOutput object.

    Returns
    -------
        GeometryRow

    Raises
    ------
    NotImplementedError
        If instantiation from the given input data type is not implemented.
    """
    if hasattr(res.data, "final_structure") and res.data.final_structure:
        struct = res.data.final_structure

    elif isinstance(res.input_data, ProgramInput):
        struct = res.input_data.structure

    else:
        msg = f"Instantiation from {type(res.input_data)} not yet implemented."
        raise NotImplementedError(msg)

    return structure.geometry_row(struct)
