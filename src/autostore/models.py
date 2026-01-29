"""Models."""

from pathlib import Path
from typing import Optional

from automol import Geometry, geom
from automol.types import FloatArray
from pydantic import ConfigDict
from qcio import ProgramInput, Results
from sqlalchemy import event
from sqlalchemy.types import JSON, String
from sqlmodel import Column, Field, Relationship, SQLModel

from . import qc
from .types import FloatArrayTypeDecorator, PathTypeDecorator


class GeometryRow(SQLModel, table=True):
    """
    Molecular geometry table row.

    Parameters
    ----------
    id
        Primary key.
    symbols
        Atomic symbols in order (e.g., ``["H", "O", "H"]``).
        The length of ``symbols`` must match the number of atoms.
    coordinates
        Cartesian coordinates of the atoms in Angstroms.
        Shape is ``(len(symbols), 3)`` and the ordering corresponds to ``symbols``.
    charge
        Total molecular charge.
    spin
        Number of unpaired electrons, i.e. two times the spin quantum number (``2S``).
    hash
        Optional hash of the geometry for quick comparisons.

    energy
        Relationship to the associated energy record, if present.
    """

    __tablename__ = "geometry"

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int | None = Field(default=None, primary_key=True)
    symbols: list[str] = Field(sa_column=Column(JSON))
    coordinates: FloatArray = Field(sa_column=Column(FloatArrayTypeDecorator))
    charge: int = 0
    spin: int = 0
    hash: str = Field(sa_column=Column(String(64), index=True, nullable=True))
    # ^ Populated by event listener below

    energy: Optional["EnergyRow"] = Relationship(back_populates="geometry")

    @classmethod
    def from_results(cls, res: Results) -> "GeometryRow":
        """
        Instantiate a GeometryRow from a QCIO Results object.

        Parameters
        ----------
        res
            QCIO Results object.

        Returns
        -------
            GeometryRow instance.

        Raises
        ------
        NotImplementedError
            If instantiation from the given input data type is not implemented.
        """
        if isinstance(res.input_data, ProgramInput):
            geo = qc.structure.geometry(res.input_data.structure)
            return cls(
                symbols=geo.symbols,
                coordinates=geo.coordinates.tolist(),
                charge=geo.charge,
                spin=geo.spin,
            )

        msg = f"Instantiation from {type(res.input_data)} not yet implemented."
        raise NotImplementedError(msg)

    # Validate coordinates shape with a field validator:
    #    @field_validator("coordinates")
    #    @classmethod
    #    def validate_shape(cls, v):
    #        if not all(len(row) == 3 for row in v):
    #            raise ValueError("Coordinates must be shape (N, 3)")  # noqa: ERA001
    #        return v  # noqa: ERA001

    # Add formula field for indexing:
    #    formula: str = Field(sa_column=Column(String, nullable=False, index=True))  # noqa: E501, ERA001

    # Define symbols -> formula conversion function:
    #    def formula_from_symbols(symbols: list[str]) -> str

    # Attach SQLAlchemy event listener to auto-set formula on insert:
    #     from sqlalchemy import event  # noqa: ERA001
    #     @event.listens_for(GeometryRow, "before_insert")
    #     @event.listens_for(GeometryRow, "before_update")
    #     def populate_formula(mapper, connection, target: GeometryRow):
    #         target.formula = formula_from_symbols(target.symbols)  # noqa: ERA001
    # This will implement the symbol-formula sync at the ORM level, so that they
    # automatically stay in sync with any inserts or updates.


@event.listens_for(GeometryRow, "before_insert")
def populate_geometry_hash(mapper, connection, target: GeometryRow) -> None:  # noqa: ANN001, ARG001
    """Populate GeometryRow hash before inserts and updates."""
    geo = Geometry(
        symbols=target.symbols,
        coordinates=target.coordinates,
        charge=target.charge,
        spin=target.spin,
    )
    target.hash = geom.geometry_hash(geo)


class CalculationRow(SQLModel, table=True):
    """
    Calculation metadata table row.

    Parameters
    ----------
    id
        Primary key.
    program
        The quantum chemistry program used (e.g., ``"Psi4"``, ``"Gaussian"``).
    method
        Computational method (e.g., ``"B3LYP"``, ``"MP2"``).
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
        Type of calculation (e.g., ``"energy"``, ``"gradient"``, ``"hessian"``).
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
        Additional metadata for the calculation.

    energy
        Relationship to the associated energy record, if present.
    """

    __tablename__ = "calculation"

    id: int | None = Field(default=None, primary_key=True)
    # Input fields:
    program: str
    method: str
    basis: str | None = None
    input: str | None = None
    keywords: dict[str, str | dict | None] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )
    cmdline_args: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )
    files: dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )
    calctype: str | None = None
    program_version: str | None = None
    # Provenance fields:
    scratch_dir: Path | None = Field(default=None, sa_column=Column(PathTypeDecorator))
    wall_time: float | None = None
    hostname: str | None = None
    hostcpus: int | None = None
    hostmem: int | None = None
    extras: dict[str, str | dict | None] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )

    energy: Optional["EnergyRow"] = Relationship(back_populates="calculation")

    @classmethod
    def from_results(cls, res: Results) -> "CalculationRow":
        """
        Instantiate a CalculationRow from a QCIO Results object.

        Parameters
        ----------
        res
            QCIO Results object.

        Returns
        -------
            CalculationRow instance.

        Raises
        ------
        NotImplementedError
            If instantiation from the given input data type is not implemented.
        """
        if isinstance(res.input_data, ProgramInput):
            return cls(
                program=res.provenance.program,
                method=res.input_data.model.method,
                basis=res.input_data.model.basis,
                input=None,  # Could store input file text here if desired
                keywords=res.input_data.keywords,
                cmdline_args=res.input_data.cmdline_args,
                files=res.input_data.files,
                calctype=res.input_data.calctype,
                program_version=res.provenance.program_version,
                scratch_dir=res.provenance.scratch_dir,
                wall_time=res.provenance.wall_time,
                hostname=res.provenance.hostname,
                hostcpus=res.provenance.hostcpus,
                hostmem=res.provenance.hostmem,
                extras=res.input_data.extras,
            )

        msg = f"Instantiation from {type(res.input_data)} not yet implemented."
        raise NotImplementedError(msg)

    # Eventually add missing QCIO `ProgramArgs` fields:
    #   - keywords
    #   - cmdline_args
    #   - files
    # These could be used for programs like PySCF that do not use an input file.


class EnergyRow(SQLModel, table=True):
    """
    Energy table row.

    Parameters
    ----------
    geometry_id
        Foreign key referencing the geometry table; part of the composite primary key.
    calculation_id
        Foreign key referencing the calculation table; part of the composite
        primary key.
    value
        Energy in Hartree.

    calculation
        Relationship to the associated calculation record.
    geometry
        Relationship to the associated geometry record.
    """

    __tablename__ = "energy"

    geometry_id: int | None = Field(
        default=None, foreign_key="geometry.id", primary_key=True
    )
    calculation_id: int | None = Field(
        default=None, foreign_key="calculation.id", primary_key=True
    )
    value: float

    calculation: CalculationRow = Relationship(back_populates="energy")
    geometry: GeometryRow = Relationship(back_populates="energy")
