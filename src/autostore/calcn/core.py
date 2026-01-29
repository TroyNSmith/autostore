"""Calculation metadata."""

from pathlib import Path

from pydantic import BaseModel, Field

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
