"""Calculation metadata."""

from pathlib import Path

from automol import Geometry
from pydantic import BaseModel, Field
from qcio import CalcType, Model, ProgramInput

from .. import qc
from .util import CalculationDict, hash_from_dict, project_keywords


class Calculation(BaseModel):
    """
    Calculation metadata.

    Parameters
    ----------
    program
        The quantum chemistry program used (e.g., "Psi4", "Gaussian").
    method
        Computational method (e.g., "B3LYP", "MP2").
    basis
        Basis set, if applicable.
    input
        Input file for the calculation, if applicable.
    keywords
        QCIO keywords for the calculation.
    cmdline_args
        Command line arguments for the calculation.
    files
        Additional files required for the calculation.
    calctype
        Type of calculation (e.g., "energy", "gradient", "hessian").
    program_version
        Version of the quantum chemistry program.
    scratch_dir
        Working directory.
    wall_time
        Wall time.
    hostname
        Name of host machine.
    hostcpus
        Number of CPUs on host machine.
    hostmem
        Amount of memory on host machine.
    extras
        Additional metadata.
    """

    # Input fields:
    program: str
    method: str
    basis: str | None = None
    input: str | None = None
    keywords: dict[str, str | dict | None] = Field(default_factory=dict)
    cmdline_args: list[str] = Field(default_factory=list)
    files: dict[str, str] = Field(default_factory=dict)
    calctype: str | None = None
    program_version: str | None = None
    # Provenance fields:
    scratch_dir: Path | None = None
    wall_time: float | None = None
    hostname: str | None = None
    hostcpus: int | None = None
    hostmem: int | None = None
    # Extra metadata:
    extras: dict[str, str | dict | None] = Field(default_factory=dict)

    def to_qcio_program_input(self, geo: Geometry, calctype: CalcType) -> ProgramInput:
        """Convert to QCIO ProgramInput object."""
        model = Model(method=self.method, basis=self.basis)
        return ProgramInput(
            calctype=calctype,
            structure=qc.structure.from_geometry(geo),
            model=model,
            keywords=self.keywords,
            cmdline_args=self.cmdline_args,
            files=self.files,  # ty:ignore[invalid-argument-type]
            extras=self.extras,
        )

    @classmethod
    def from_qcio_program_input(
        cls, prog_input: ProgramInput, prog: str
    ) -> "Calculation":
        """Create Calculation metadata from QCIO ProgramInput object."""
        return cls(
            program=prog,
            method=prog_input.model.method,
            basis=prog_input.model.basis,
            keywords=prog_input.keywords,
            cmdline_args=prog_input.cmdline_args,
            files=prog_input.files,  # ty:ignore[invalid-argument-type]
            calctype=prog_input.calctype.value,
            extras=prog_input.extras,
        )


def projected_hash(calc: Calculation, template: Calculation | CalculationDict) -> str:
    """
    Project calculation onto template and generate hash.

    Parameters
    ----------
    calc
        Calculation metadata.
    template
        Calculation metadata template.

    Returns
    -------
        Hash string.
    """
    calc_dct = project(calc, template)
    return hash_from_dict(calc_dct)


def project(
    calc: Calculation, template: Calculation | CalculationDict
) -> CalculationDict:
    """
    Project calculation onto template.

    Parameters
    ----------
    calc
        Calculation metadata.
    template
        Calculation metadata template.

    Returns
    -------
        Projected calculation dictionary.
    """
    # Dump template to dictionary
    template = (
        template.model_dump(exclude_unset=True)
        if isinstance(template, Calculation)
        else template
    )
    # Include only keywords and extras from template
    if "keywords" in template:
        calc.keywords = project_keywords(
            calc.keywords, template=template.get("keywords", {})
        )
    if "extras" in template:
        calc.extras = project_keywords(calc.extras, template=template.get("extras", {}))
    # Include only fields from template
    return calc.model_dump(exclude_none=True, include=set(template.keys()))
