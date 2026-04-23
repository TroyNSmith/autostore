"""Calculation row model and associated models and functions."""

from pathlib import Path
from typing import Any

import numpy as np
import pint
from automol import Geometry, geom
from automol.types import FloatArray
from pydantic import ConfigDict
from qcdata import (
    DualProgramInput,
    Model,
    ProgramInput,
    ProgramOutput,
    Structure,
)
from sqlalchemy import event
from sqlalchemy.types import JSON, String
from sqlmodel import Column, Field, Relationship, Session, SQLModel, select

from .calcn import Calculation, calculation_hash, hash_registry
from .types import (
    FloatArrayTypeDecorator,
    PathTypeDecorator,
    Role,
    RowID,
)


# --- Link Models -------------------------------
class CalculationGeometryLink(SQLModel, table=True):
    """
    Link CalculationRows to GeometryRows.

    Attributes
    ----------
    geometry_id
        Foreign key to the linked geometry.
    calculation_id
        Foreign key to the linked geometry.
    role
        Role of the geometry in the calculation.

    Linked Row
    ------------
    calculation
        Corresponding CalculationRow.
    geometry
        Corresponding role GeometryRow.
    """

    # - SQL Metadata --------
    __tablename__ = "calculation_geometry_link"
    model_config = ConfigDict(use_enum_values=True)
    # - Row id --------------
    # - Foreign keys --------
    geometry_id: RowID = Field(
        foreign_key="geometry.id",
        primary_key=True,
        ondelete="CASCADE",
        description="Foreign key to the linked geometry.",
    )
    calculation_id: RowID = Field(
        foreign_key="calculation.id",
        primary_key=True,
        ondelete="CASCADE",
        description="Foreign key to the linked geometry.",
    )
    # - Attributes ----------
    role: Role = Field(description="Role of the geometry in the calculation.")
    # - Linked row ----------
    # - Linked rows ---------


class StationaryIdentityLink(SQLModel, table=True):
    """
    Link StationaryPointRow to IdentityRow.

    Attributes
    ----------
    stationary_id
        Foreign key to the linked stationary point.
    identity_id
        Foreign key to the linked identity.
    """

    # - SQL Metadata --------
    __tablename__ = "stationary_identity_link"
    # - Row id --------------
    # - Foreign keys --------
    stationary_id: RowID = Field(
        foreign_key="stationary_point.id",
        primary_key=True,
        ondelete="CASCADE",
        description="Foreign key to the linked stationary point.",
    )
    identity_id: RowID = Field(
        foreign_key="identity.id",
        primary_key=True,
        ondelete="CASCADE",
        description="Foreign key to the linked identity.",
    )
    # - Attributes ----------
    # - Linked row ----------
    # - Linked rows ---------


class StationaryStageLink(SQLModel, table=True):
    """
    Link StationaryPointRows to StageRows.

    Attributes
    ----------
    stationary_id
        Foreign key to the linked stationary point.
    stage_id
        Foreign key to the linked reaction stage.
    """

    # - SQL Metadata --------
    __tablename__ = "stationary_stage_link"
    # - Row id --------------
    # - Foreign keys --------
    stationary_id: RowID = Field(
        foreign_key="stationary_point.id",
        primary_key=True,
        ondelete="CASCADE",
        description="Foreign key to the linked stationary point.",
    )
    stage_id: RowID = Field(
        foreign_key="stage.id",
        primary_key=True,
        ondelete="CASCADE",
        description="Foreign key to the linked reaction stage.",
    )
    # - Attributes ----------
    # - Linked row ----------
    # - Linked rows ---------


# --- Calculation Models ------------------------
class CalculationRow(Calculation, SQLModel, table=True):
    """CalculationRow input parameters and metadata.

    Attributes
    ----------
    # - Program Input -------
    program
        Quantum chemistry program used (psi4, ORCA, ...)
    program_keywords
        (Optional) Quantum chemistry program keywords.
    super_program
        (Optional) Geometry optimizer program (geomeTRIC, ...).
    super_keywords
        (Optional) Geometry optimizer keywords.
    cmdline_args
        (Optional) Command line arguments.
    input
        (Optional) Input file. [ PLACEHOLDER ]
    files
        (Optional) Additional input files. [ PLACEHOLDER ]
    # - Methods -------------
    calc_type
        Calculation type (energy, optimization, ...)
    method
        Computational method (B3LYP, MP2, ...)
    basis
        (Optional) Basis set.

    Linked Row
    ----------
    provenance
        Linked ProvenanceRow.

    Linked Rows
    -------------
    geometries
        List of linked GeometryRows.
    geometry_links
        List of linked CalculationGeometryLinks.
    energies
        List of linked energies.
    hashes
        List of linked hashes.
    stationary_points
        List of linked stationary points.

    Methods
    -------
    from_calculation
        Convert Calculation to CalculationRow.
    calculation
        Convert CalculationRow to Calculation.
    program_input
        Convert CalculationRow to qcio program_input.
    """

    # - SQL Metadata --------
    __tablename__ = "calculation"
    # - Row id --------------
    id: RowID | None = Field(default=None, primary_key=True)
    # - Foreign keys --------
    # - Attributes ----------
    # Have to redeclare these fields for sql type verification.
    program_keywords: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )
    super_keywords: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    cmdline_args: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    # - Linked row ----------
    provenance: "ProvenanceRow" = Relationship(back_populates="calculation")
    # - Linked rows ---------
    geometries: list["GeometryRow"] = Relationship(
        back_populates="calculations", link_model=CalculationGeometryLink
    )
    energies: list["EnergyRow"] = Relationship(
        back_populates="calculation", cascade_delete=True
    )
    hashes: list["CalculationHashRow"] = Relationship(
        back_populates="calculation", cascade_delete=True
    )
    stationary_points: list["StationaryPointRow"] = Relationship(
        back_populates="calculation"
    )

    # - Methods -------------
    @staticmethod
    def from_calculation(calc: Calculation) -> "CalculationRow":
        """
        Instantiate CalculationRow from Calculation.

        Returns
        -------
        CalculationRow
        """
        return CalculationRow(**calc.model_dump())

    def calculation(self) -> Calculation:
        """
        Instantiate Calculation from CalculationRow.

        Returns
        -------
        Calculation
        """
        return Calculation(**self.model_dump())

    @staticmethod
    def from_program_input(
        *, prog_inp: ProgramInput | DualProgramInput, program: str
    ) -> "CalculationRow":
        """
        Instantiate CalculationRow from qc ProgramInput or DualProgramInput.

        Parameters
        ----------
        prog_inp
            The input object (single or dual program).
        program
            The program used to run calculation.

        Returns
        -------
        CalculationRow
            The validated calculation row.
        """
        if isinstance(prog_inp, DualProgramInput):
            data = {
                "program": prog_inp.subprogram,
                "program_keywords": prog_inp.subprogram_args.keywords,
                "super_program": program,
                "super_keywords": prog_inp.keywords,
                "cmdline_args": prog_inp.subprogram_args.cmdline_args,
                "calc_type": prog_inp.calctype.value,
                "method": prog_inp.subprogram_args.model.method,
                "basis": prog_inp.subprogram_args.model.basis,
            }

        else:
            data = {
                "program": program,
                "program_keywords": prog_inp.keywords,
                "cmdline_args": prog_inp.cmdline_args,
                "calc_type": prog_inp.calctype.value,
                "method": prog_inp.model.method,
                "basis": prog_inp.model.basis,
            }

        return CalculationRow.model_validate(data)

    def program_input(
        self, *, input_geo: "GeometryRow"
    ) -> DualProgramInput | ProgramInput:
        """
        Generate qcdata ProgramInput from Calculation and input Geometry.

        Parameters
        ----------
        input_geo
            Input GeometryRow.

        Returns
        -------
        qc DualProgramInput/ProgramInput
        """
        if self.super_program:
            return DualProgramInput.model_validate(
                {
                    "calctype": self.calc_type,
                    "structure": input_geo.structure(),
                    "keywords": self.super_keywords,
                    "subprogram": self.program,
                    "subprogram_args": {
                        "model": Model(method=self.method, basis=self.basis),
                        "keywords": self.program_keywords,
                        "cmdline_args": self.cmdline_args,
                    },
                }
            )

        return ProgramInput.model_validate(
            {
                "calctype": self.calc_type,
                "structure": input_geo.structure(),
                "model": Model(method=self.method, basis=self.basis),
                "keywords": self.program_keywords,
                "cmdline_args": self.cmdline_args,
            }
        )

    @staticmethod
    def from_program_output(prog_out: ProgramOutput) -> "CalculationRow":
        """
        Instantiate CalculationRow from qc ProgramOutput.

        **Automatically instantiates and relates ProvenanceRow.

        Parameters
        ----------
        prog_out
            qccompute ProgramOutput.

        Returns
        -------
        CalculationRow
            Validated calculation row.
        """
        prog_inp = prog_out.input_data
        provenance = prog_out.provenance

        if isinstance(prog_inp, DualProgramInput):
            data = {
                "program": prog_inp.subprogram,
                "program_keywords": prog_inp.subprogram_args.keywords,
                "super_program": provenance.program,
                "super_keywords": prog_inp.keywords,
                "cmdline_args": prog_inp.subprogram_args.cmdline_args,
                "calc_type": prog_inp.calctype.value,
                "method": prog_inp.subprogram_args.model.method,
                "basis": prog_inp.subprogram_args.model.basis,
            }

        else:
            data = {
                "program": provenance.program,
                "program_keywords": prog_inp.keywords,
                "cmdline_args": prog_inp.cmdline_args,
                "calc_type": prog_inp.calctype.value,
                "method": prog_inp.model.method,
                "basis": prog_inp.model.basis,
            }

        calc_row = CalculationRow.model_validate(data)
        calc_row.provenance = ProvenanceRow.from_program_output(prog_out)
        return calc_row


class ProvenanceRow(SQLModel, table=True):
    """
    CalculationRow output parameters and metadata.

    Parameters
    ----------
    program_version
        (Optional) Program version.
    super_version
        (Optional) Superprogram version, if applicable.
    input
        (Optional) Input file.
    files
        (Optional) Additional input files.
    scratch_dir
        (Optional) Working directory.
    wall_time
        (Optional) Compute wall time.
    host_name
        (Optional) Name of host machine.
    host_cpus
        (Optional) Number of CPUs on host machine.
    host_mem
        (Optional) Amount of memory on host machine.
    extras
        (Optional) Additional calculation metadata.
    """

    # - SQL Metadata --------
    __tablename__ = "provenance"
    # - Row id --------------
    # - Foreign keys --------
    calculation_id: RowID | None = Field(
        primary_key=True,
        default=None,
        foreign_key="calculation.id",
        index=True,
        nullable=False,
        ondelete="CASCADE",
    )
    # - Attributes ----------
    program_version: str | None = Field(default=None)
    super_version: str | None = Field(default=None)
    input: str | None = Field(default=None)
    files: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    scratch_dir: Path | None = Field(default=None, sa_column=Column(PathTypeDecorator))
    wall_time: float | None = Field(default=None)
    host_name: str | None = Field(default=None)
    host_cpus: int | None = Field(default=None)
    host_mem: int | None = Field(default=None)
    extras: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    # - Linked row ----------
    calculation: CalculationRow = Relationship(back_populates="provenance")
    # - Linked rows ---------

    @staticmethod
    def from_program_output(prog_out: ProgramOutput) -> "ProvenanceRow":
        """
        Instantiate ProvenanceRow from qc ProgramOutput.

        Parameters
        ----------
        prog_out
            qccompute ProgramOutput.

        Returns
        -------
        ProvenanceRow
            Validated provenance row.
        """
        prog_inp = prog_out.input_data
        provenance = prog_out.provenance
        data = prog_out.data

        if isinstance(prog_inp, DualProgramInput):
            traj_prov = [t.provenance for t in data.trajectory]
            data = {
                "program_version": traj_prov[0].program_version,
                "super_version": provenance.program_version,
                "input": None,  # Could be used to store .inp (or equivalent) files
                "files": {
                    "program": prog_inp.subprogram_args.files,
                    "super_program": prog_inp.files,
                },
                "scratch_dir": provenance.scratch_dir,
                "wall_time": provenance.wall_time,
                "host_name": provenance.hostname,
                "host_cpus": provenance.hostcpus,
                "host_mem": provenance.hostmem,
                "extras": {
                    "super_program": prog_inp.extras,
                    "program": prog_inp.subprogram_args.extras,
                },
            }

        else:
            data = {
                "program_version": provenance.program_version,
                "input": None,  # Could be used to store .inp (or equivalent) files
                "files": {"program": prog_inp.files},
                "scratch_dir": provenance.scratch_dir,
                "wall_time": provenance.wall_time,
                "host_name": provenance.hostname,
                "host_cpus": provenance.hostcpus,
                "host_mem": provenance.hostmem,
                "extras": {"program": prog_inp.extras},
            }

        return ProvenanceRow.model_validate(data)


class CalculationHashRow(SQLModel, table=True):
    """
    Hash value for a calculation for identification and deduplication.

    Attributes
    ----------
    calculation_id
        Foreign key to the parent CalculationRow.
    name
        Type of hash (e.g., 'minimal', 'full').
    value
        The 64-character hash string.

    Linked Row
    ------------
    calculation
        The parent CalculationRow.
    """

    # - SQL Metadata --------
    __tablename__ = "calculation_hash"
    # - Row id --------------
    id: RowID | None = Field(default=None, primary_key=True)
    # - Foreign keys --------
    calculation_id: RowID = Field(
        foreign_key="calculation.id", index=True, nullable=False, ondelete="CASCADE"
    )
    # - Attributes ----------
    name: str = Field(index=True)
    value: str = Field(sa_column=Column(String(64), index=True, nullable=False))
    # - Linked row ----------
    calculation: CalculationRow = Relationship(back_populates="hashes")
    # - Linked rows ---------


# --- Geometry Models ---------------------------
class GeometryRow(Geometry, SQLModel, table=True):
    """
    Molecular geometry definition and metadata.

    Attributes
    ----------
    symbols
        List of atomic symbols in order.
    coordinates
        Atomic coordinates in Angstrom.
    charge
        Total molecular charge.
    spin
        Number of unpaired electrons (2S).
    hash
        Unique hash of the geometry for indexing.

    Linked Row
    -------------
    stationary_point
        StationaryPointRow associated with this geometry.

    Linked Rows
    -------------
    calculations
        List of CalculationRows that used or produced this geometry.
    energies
        List of calculated energies for this geometry.

    Methods
    -------
    to_qc_structure
        Convert GeometryRow to a qc Structure object.
    from_qc_structure
        (Static) Create a GeometryRow from a qc Structure object.
    """

    # - SQL Metadata --------
    __tablename__ = "geometry"
    model_config = ConfigDict(arbitrary_types_allowed=True)
    # - Row id --------------
    id: RowID | None = Field(default=None, primary_key=True)
    # - Foreign keys --------
    # - Attributes ----------
    symbols: list[str] = Field(sa_column=Column(JSON))
    coordinates: FloatArray = Field(sa_column=Column(FloatArrayTypeDecorator))
    charge: int = Field(default=0)
    spin: int = Field(default=0)
    hash: str | None = Field(
        default=None,
        sa_column=Column(String(64), index=True, nullable=True, unique=True),
    )
    # ^ Populated by event listener
    # - Linked row ----------
    stationary_point: "StationaryPointRow" = Relationship(back_populates="geometry")
    # - Linked rows ---------
    calculations: list["CalculationRow"] = Relationship(
        back_populates="geometries", link_model=CalculationGeometryLink
    )
    energies: list["EnergyRow"] = Relationship(
        back_populates="geometry", cascade_delete=True
    )

    # - Methods -------------
    @staticmethod
    def from_geometry(geo: Geometry) -> "GeometryRow":
        """
        Instantiate GeometryRow from Geometry.

        Returns
        -------
        GeometryRow
        """
        return GeometryRow(**geo.model_dump())

    def geometry(self) -> Geometry:
        """
        Instantiate Geometry from GeometryRow.

        Returns
        -------
        Geometry
        """
        return Geometry(**self.model_dump())

    @staticmethod
    def from_structure(*, struc: Structure) -> "GeometryRow":
        """
        Instantiate GeometryRow from qcdata Structure.

        Parameters
        ----------
        struc
            The qcdata Structure to convert.

        Returns
        -------
        GeometryRow
            GeometryRow in Angstrom.
        """
        return GeometryRow(
            symbols=struc.symbols,
            coordinates=struc.geometry * pint.Quantity("bohr").m_as("angstrom"),
            charge=struc.charge,
            spin=struc.multiplicity - 1,
        )

    def structure(self) -> Structure:
        """
        Instantiate qcdata Structure from GeometryRow.

        Returns
        -------
        Structure
            qcdata Structure in Bohr.
        """
        return Structure(
            symbols=self.symbols,
            geometry=np.array(self.coordinates)
            * pint.Quantity("angstrom").m_as("bohr"),
            charge=self.charge,
            multiplicity=self.spin + 1,
        )


# --- Data Models -------------------------------
class EnergyRow(SQLModel, table=True):
    """
    Results of an energy calculation for a specific geometry.

    Attributes
    ----------
    geometry_id
        Foreign key to the specific geometry.
    calculation_id
        Foreign key to the calculation that produced this energy.
    value
        Energy value in Hartree.

    Linked Row
    -----------
    geometry
        GeometryRow defining the point's coordinates.
    calculation
        Parent CalculationRow.
    """

    # - SQL Metadata --------
    __tablename__ = "energy"
    # - Row id --------------
    id: RowID | None = Field(default=None, primary_key=True)
    # - Foreign keys --------
    geometry_id: RowID | None = Field(
        default=None, foreign_key="geometry.id", ondelete="CASCADE"
    )
    calculation_id: RowID | None = Field(
        default=None, foreign_key="calculation.id", ondelete="CASCADE"
    )
    # - Attributes ----------
    value: float
    # - Linked row ----------
    calculation: CalculationRow = Relationship(back_populates="energies")
    geometry: GeometryRow = Relationship(back_populates="energies")
    # - Linked rows ---------


# --- Stationary Models -------------------------
class StationaryPointRow(SQLModel, table=True):
    """
    Definition of a stationary point on a potential energy surface.

    Attributes
    ----------
    geometry_id
        Foreign key to the underlying molecular geometry.
    calculation_id
        Foreign key to the calculation identifying this point.
    order
        Hessian index (0 for minima, 1 for saddle points).
    is_pseudo
        Flag for points that are not true stationary points (e.g., constrained).

    Linked Row
    ----------
    geometry
        GeometryRow defining the point's coordinates.
    calculation
        Parent CalculationRow.
    Linked Rows
    -----------
    identities
        List of chemical identifiers (InChI, etc.).
    metrics
        Comparison metrics (conformer analysis).
    stages
        Reaction stages this stationary point belongs to.
    """

    # - SQL Metadata --------
    __tablename__ = "stationary_point"
    # - Row id --------------
    id: RowID | None = Field(default=None, primary_key=True)
    # - Foreign keys --------
    geometry_id: RowID = Field(foreign_key="geometry.id", ondelete="CASCADE")
    calculation_id: RowID = Field(foreign_key="calculation.id", ondelete="CASCADE")
    # - Attributes ----------
    order: int
    is_pseudo: bool
    # - Linked row ----------
    geometry: "GeometryRow" = Relationship(back_populates="stationary_point")
    calculation: "CalculationRow" = Relationship(back_populates="stationary_points")
    # - Linked rows ---------
    identities: list["IdentityRow"] = Relationship(
        back_populates="stationary_points", link_model=StationaryIdentityLink
    )
    metrics: list["MetricRow"] = Relationship(
        back_populates="stationary_point",
    )
    stages: list["StageRow"] = Relationship(
        back_populates="stationary_points", link_model=StationaryStageLink
    )


class IdentityRow(SQLModel, table=True):
    """
    Chemical identifiers for stationary points.

    Attributes
    ----------
    type
        Category of identity (e.g., 'stereoisomer', 'formula').
    algorithm
        The method used (e.g., 'InChI', 'SMILES').
    value
        The resulting string identifier.

    Linked Tables
    -------------
    stationary_points
        Stationary points sharing this identity.
    """

    # - SQL Metadata --------
    __tablename__ = "identity"
    # - Row id --------------
    id: RowID | None = Field(default=None, primary_key=True)
    # - Foreign keys --------
    # - Attributes ----------
    type: str = Field(description="Category of the identity (stereoisomer, ...)")
    algorithm: str = Field(description="Method used to determine identity (InChI, ...)")
    value: str = Field(description="Value of the identity algorithm.")
    # - Linked row ----------
    # - Linked rows ---------
    stationary_points: list["StationaryPointRow"] = Relationship(
        back_populates="identities", link_model=StationaryIdentityLink
    )


class MetricRow(SQLModel, table=True):
    """
    Metrics used for comparing and filtering conformers or stationary points.

    Attributes
    ----------
    stationary_id
        Foreign key to the associated stationary point.
    type
        Type of metric (e.g., 'Inertia Tensor').
    algorithm
        Algorithm used (e.g., 'Kabsch').
    value
        The calculated metric value.

    Linked Row
    ----------
    stationary_point
        The parent StationaryPointRow.
    """

    # - SQL Metadata --------
    __tablename__ = "metric"
    # - Row id --------------
    id: RowID | None = Field(default=None, primary_key=True)
    # - Foreign keys --------
    stationary_id: RowID = Field(
        foreign_key="stationary_point.id",
        index=True,
        description="Foreign key to the linked stationary point.",
    )
    # - Attributes ----------
    type: str = Field(description="Category of the metric (Inertia Tensor, ...)")
    algorithm: str = Field(description="Method used to determine metric (Kabsch, ...)")
    value: str = Field(description="Value of the metric algorithm.")
    # - Linked row ----------
    stationary_point: "StationaryPointRow" = Relationship(back_populates="metrics")
    # - Linked rows ---------


# --- Stage Models ------------------------------
class StageRow(SQLModel, table=True):
    """
    A specific chemical state (reactant, product, or TS) in a reaction.

    Attributes
    ----------
    is_ts
        Whether this stage represents a transition state.

    Linked Row
    ----------
    steps_1, steps_2
        Connection to StepRows where this stage is a reactant or product.
    steps_ts
        Connection to StepRows where this stage is the transition state.
    Linked Rows
    -----------
    stationary_points
        Geometries mapped to this reaction stage.
    """

    # - SQL Metadata --------
    __tablename__ = "stage"
    # - Row id --------------
    id: RowID | None = Field(default=None, primary_key=True)
    # - Foreign keys --------
    # - Attributes ----------
    is_ts: bool = Field(description="Stage represents transition state.")
    # - Linked row ----------
    steps_1: list["StepRow"] = Relationship(
        back_populates="stage1",
        sa_relationship_kwargs={"foreign_keys": "[StepRow.stage_id1]"},
    )
    steps_2: list["StepRow"] = Relationship(
        back_populates="stage2",
        sa_relationship_kwargs={"foreign_keys": "[StepRow.stage_id2]"},
    )
    steps_ts: list["StepRow"] = Relationship(
        back_populates="stage_ts",
        sa_relationship_kwargs={"foreign_keys": "[StepRow.stage_id_ts]"},
    )
    # - Linked rows ---------
    stationary_points: list["StationaryPointRow"] = Relationship(
        back_populates="stages", link_model=StationaryStageLink
    )


# --- Stage Models ------------------------------
class StepRow(SQLModel, table=True):
    """
    An elementary reaction step connecting multiple stages.

    Attributes
    ----------
    stage_id1
        Foreign key to the first reactant/product stage.
    stage_id2
        Foreign key to the second reactant/product stage.
    stage_id_ts
        Foreign key to the transition state stage.
    is_barrierless
        Flag for reactions without a formal transition state.

    Linked Row
    ----------
    stage1, stage2, stage_ts
        The specific StageRows linked by this step.
    """

    # - SQL Metadata --------
    __tablename__ = "step"
    # - Row id --------------
    id: RowID | None = Field(default=None, primary_key=True)
    # - Foreign keys --------
    stage_id1: RowID = Field(
        foreign_key="stage.id",
        index=True,
        description="Foreign key to the 1st reaction stage.",
    )
    stage_id2: RowID = Field(
        foreign_key="stage.id",
        index=True,
        description="Foreign key to the 2nd reaction stage.",
    )
    stage_id_ts: RowID = Field(
        foreign_key="stage.id",
        index=True,
        description="Foreign key to the TS reaction stage.",
    )
    # - Attributes ----------
    is_barrierless: bool = Field(
        description="Reaction step does not involve a TS stage."
    )
    # - Linked row ----------
    stage1: "StageRow" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[StepRow.stage_id1]"}
    )
    stage2: "StageRow" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[StepRow.stage_id2]"}
    )
    stage_ts: "StageRow" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[StepRow.stage_id_ts]"}
    )
    # - Linked rows ---------


# --- Listeners ---------------------------------
@event.listens_for(GeometryRow, "before_insert")
def populate_geometry_hash(mapper, connection, target: GeometryRow) -> None:  # noqa: ANN001, ARG001
    """Populate GeometryRow hash before inserts and updates."""
    if target.hash is None:
        target.hash = geom.geometry_hash(target)


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
                    calculation_id=row.id,
                    name=name,
                    value=value,
                )
            )


@event.listens_for(StationaryPointRow, "after_insert")
def stationary_inchi(mapper, connection, target: StationaryPointRow) -> None:  # noqa: ANN001, ARG001
    """Automatically tags InChI and default metrics after inserting StationaryPoint."""
    session = Session(bind=connection)

    if target.id is None:
        msg = f"{target = } not assigned an id."
        raise LookupError(msg)

    try:
        # NOTE: If target.geometry isn't loaded, we need to fetch it
        geom_stmt = select(GeometryRow).where(GeometryRow.id == target.geometry_id)
        geom_row = session.exec(geom_stmt).first()

        if not geom_row:
            msg = (
                f"{target.geometry_id} does not correspond to an entry in the database."
            )
            raise LookupError(msg)  # noqa: TRY301

        inchi_string = geom.inchi(geom_row)

        inchi_stmt = select(IdentityRow).where(
            IdentityRow.algorithm == "InChI", IdentityRow.value == inchi_string
        )
        id_row = session.exec(inchi_stmt).first()

        if id_row is None:
            id_row = IdentityRow(
                type="stereoisomer",
                algorithm="InChI",
                value=inchi_string,
            )
            session.add(id_row)
            session.flush()

        if id_row.id is None:
            msg = f"{id_row = } not assigned an id."
            raise LookupError(msg)  # noqa: TRY301

        link = StationaryIdentityLink(stationary_id=target.id, identity_id=id_row.id)
        session.add(link)

        session.commit()

    except Exception as e:
        session.rollback()
        msg = f"Failed to generate InChI {target.id}"
        raise RuntimeError(msg) from e
