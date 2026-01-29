"""Calculation specification data."""

from pydantic import BaseModel, Field

from .util import CalculationDict, hash_from_dict, project_keywords


class Calculation(BaseModel):
    """
    Calculation specification.

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
    extras
        Additional metadata for the calculation.
    """

    program: str
    method: str
    basis: str | None = None
    input: str | None = None
    keywords: dict[str, str | dict | None] = Field(default_factory=dict)
    cmdline_args: list[str] = Field(default_factory=list)
    files: dict[str, str] = Field(default_factory=dict)
    calctype: str | None = None
    program_version: str | None = None
    extras: dict[str, str | dict | None] = Field(default_factory=dict)


def projected_hash(calc: Calculation, template: Calculation | CalculationDict) -> str:
    """
    Project calculation onto template and generate hash.

    Parameters
    ----------
    calc
        Calculation specification object.
    template
        Calculation specification object template.

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
        Calculation specification object.
    template
        Calculation specification object template.

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
