"""SQLModel row definitions for autostorage's persistence schema."""

from datetime import datetime
from functools import cached_property
from typing import Any

import numpy as np
from automol import Geometry, Identity, geom
from automol.utils.types import FloatArray
from sqlmodel import (
    JSON,
    CheckConstraint,
    Column,
    Enum,
    Field,
    Index,
    Relationship,
    SQLModel,
    UniqueConstraint,
    func,
    text,
)
from sqlmodel.main import SQLModelConfig

from .utils.types import (
    CalcStatus,
    CalcType,
    CompressedArrayTypeDecorator,
    Role,
    _fk_field,
    _pk_field,
)

__all__ = [
    "CalculationGeometryLink",
    "CalculationRow",
    "CalculationTrajectoryLink",
    "EnergyRow",
    "GeometryRow",
    "GradientRow",
    "HessianRow",
    "IdentityExtraRow",
    "IdentityRow",
    "ModelRow",
    "SQLModel",
    "StageRow",
    "StationaryIdentityLink",
    "StationaryPointRow",
    "StationaryStageLink",
    "StepRow",
    "StepValidationLink",
    "TrajectoryGeometryLink",
    "TrajectoryRow",
    "ValidationRow",
    "_fk_field",
]


# Link tables
class TrajectoryGeometryLink(SQLModel, table=True):
    """Association table linking geometries to a trajectory.

    Attributes
    ----------
    geometry_id
        Foreign key to the linked geometry.
    trajectory_id
        Foreign key to the linked trajectory.
    index
        Position of the geometry within the trajectory.
    geometry
        The linked geometry.
    trajectory
        The linked trajectory.
    """

    __tablename__ = "trajectory_geometry_link"
    __table_args__ = (
        Index("ix_trajectory_geometry_link_trajectory_id", "trajectory_id"),
    )

    geometry_id: int | None = _fk_field("geometry.id", primary_key=True)
    trajectory_id: int | None = _fk_field("trajectory.id", primary_key=True)
    index: list[int] | None = Field(default=None, sa_column=Column(JSON))

    geometry: "GeometryRow" = Relationship(back_populates="trajectory_links")
    trajectory: "TrajectoryRow" = Relationship(back_populates="geometry_links")


class StationaryIdentityLink(SQLModel, table=True):
    """Association table linking stationary points to chemical identities.

    Attributes
    ----------
    stationary_id
        Foreign key to the linked stationary point.
    identity_id
        Foreign key to the linked identity.
    """

    __tablename__ = "stationary_identity_link"
    __table_args__ = (Index("ix_stationary_identity_link_identity_id", "identity_id"),)

    stationary_id: int | None = _fk_field("stationary_point.id", primary_key=True)
    identity_id: int | None = _fk_field("identity.id", primary_key=True)


class StationaryStageLink(SQLModel, table=True):
    """Association table linking stationary points to reaction stages.

    Attributes
    ----------
    stationary_id
        Foreign key to the linked stationary point.
    stage_id
        Foreign key to the linked reaction stage.
    stationary
        The linked stationary point.
    stage
        The linked reaction stage.
    """

    __tablename__ = "stationary_stage_link"
    __table_args__ = (Index("ix_stationary_stage_link_stage_id", "stage_id"),)

    stationary_id: int | None = _fk_field("stationary_point.id", primary_key=True)
    stage_id: int | None = _fk_field("stage.id", primary_key=True)


class StepValidationLink(SQLModel, table=True):
    """Association table linking validations to a step.

    Attributes
    ----------
    step_id
        Foreign key to the linked step.
    validation_id
        Foreign key to the linked validation.
    """

    __tablename__ = "step_validation_link"
    __table_args__ = (Index("ix_step_validation_link_validation_id", "validation_id"),)

    step_id: int | None = _fk_field("step.id", primary_key=True)
    validation_id: int | None = _fk_field("validation.id", primary_key=True)


class CalculationGeometryLink(SQLModel, table=True):
    """Association table linking geometries to a calculation.

    Attributes
    ----------
    geometry_id
        Foreign key to the linked geometry.
    calculation_id
        Foreign key to the linked calculation.
    role
        Role the geometry plays for this calculation (input/output).
    geometry
        The linked geometry.
    calculation
        The linked calculation.
    """

    __tablename__ = "calculation_geometry_link"
    __table_args__ = (
        # The composite primary key only serves lookups keyed by `geometry_id`
        # (its leading column); this adds a matching index for `calculation_id`.
        Index("ix_calculation_geometry_link_calculation_id", "calculation_id"),
    )

    geometry_id: int | None = _fk_field("geometry.id", primary_key=True)
    calculation_id: int | None = _fk_field("calculation.id", primary_key=True)
    role: Role = Field(
        sa_column=Column(Enum(Role, values_callable=lambda x: [e.value for e in x]))
    )

    geometry: "GeometryRow" = Relationship(back_populates="calculation_links")
    calculation: "CalculationRow" = Relationship(back_populates="geometry_links")


class CalculationTrajectoryLink(SQLModel, table=True):
    """Association table linking trajectories to a calculation.

    Attributes
    ----------
    trajectory_id
        Foreign key to the linked trajectory.
    calculation_id
        Foreign key to the linked calculation.
    role
        Role the trajectory plays for this calculation (input/output).
    trajectory
        The linked trajectory.
    calculation
        The linked calculation.
    """

    __tablename__ = "calculation_trajectory_link"
    __table_args__ = (
        Index("ix_calculation_trajectory_link_calculation_id", "calculation_id"),
    )

    trajectory_id: int | None = _fk_field("trajectory.id", primary_key=True)
    calculation_id: int | None = _fk_field("calculation.id", primary_key=True)
    role: Role = Field(
        sa_column=Column(Enum(Role, values_callable=lambda x: [e.value for e in x]))
    )

    trajectory: "TrajectoryRow" = Relationship(back_populates="calculation_links")
    calculation: "CalculationRow" = Relationship(back_populates="trajectory_links")


class GeometryRow(SQLModel, table=True):
    """Molecular geometry definition and metadata.

    Attributes
    ----------
    symbols
        Atomic symbols in order.
    coordinates
        Atomic coordinates in Angstrom.
    charge
        Total molecular charge.
    spin
        Number of unpaired electrons (2S).
    energies
        Energy results computed at this geometry.
    gradients
        Gradient results computed at this geometry.
    hessians
        Hessian results computed at this geometry.
    stationary_points
        Stationary points defined by this geometry.
    trajectory_links
        Raw link rows connecting this geometry to trajectories.
    calculation_links
        Raw link rows connecting this geometry to calculations.
    """

    __tablename__ = "geometry"
    model_config = SQLModelConfig(arbitrary_types_allowed=True)

    id: int | None = _pk_field()
    symbols: list[str] = Field(sa_column=Column(JSON))
    coordinates: FloatArray = Field(sa_column=Column(CompressedArrayTypeDecorator()))
    charge: int
    spin: int

    energies: list["EnergyRow"] = Relationship(back_populates="geometry")
    gradients: list["GradientRow"] = Relationship(back_populates="geometry")
    hessians: list["HessianRow"] = Relationship(back_populates="geometry")
    stationary_points: list["StationaryPointRow"] = Relationship(
        back_populates="geometry"
    )
    trajectory_links: list["TrajectoryGeometryLink"] = Relationship(
        back_populates="geometry"
    )
    calculation_links: list["CalculationGeometryLink"] = Relationship(
        back_populates="geometry"
    )

    def to_geometry(self) -> Geometry:
        """Convert to an automol Geometry instance."""
        return Geometry(
            symbols=self.symbols,
            coordinates=self.coordinates,
            charge=self.charge,
            spin=self.spin,
        )


# Result rows
class EnergyRow(SQLModel, table=True):
    """Energy result for a specific geometry and calculation.

    Attributes
    ----------
    geometry_id
        Foreign key to the geometry this energy was evaluated at.
    calculation_id
        Foreign key to the calculation that produced this energy.
    value
        Energy value in Hartree.
    geometry
        Geometry this energy was evaluated at.
    calculation
        Calculation that produced this energy.
    """

    __tablename__ = "energy"

    id: int | None = _pk_field()
    geometry_id: int | None = _fk_field("geometry.id")
    calculation_id: int | None = _fk_field("calculation.id")
    value: float

    calculation: "CalculationRow" = Relationship()
    geometry: "GeometryRow" = Relationship(back_populates="energies")


class GradientRow(SQLModel, table=True):
    """Energy gradient result for a specific geometry and calculation.

    Attributes
    ----------
    geometry_id
        Foreign key to the geometry this gradient was evaluated at.
    calculation_id
        Foreign key to the calculation that produced this gradient.
    value
        Flattened gradient vector in Hartree/Bohr.
    geometry
        Geometry this gradient was evaluated at.
    calculation
        Calculation that produced this gradient.
    """

    __tablename__ = "gradient"
    model_config = SQLModelConfig(arbitrary_types_allowed=True)

    id: int | None = _pk_field()
    geometry_id: int | None = _fk_field("geometry.id")
    calculation_id: int | None = _fk_field("calculation.id")
    value: FloatArray = Field(sa_column=Column(CompressedArrayTypeDecorator()))

    calculation: "CalculationRow" = Relationship()
    geometry: "GeometryRow" = Relationship(back_populates="gradients")


class HessianRow(SQLModel, table=True):
    """Hessian result for a specific geometry and calculation.

    Attributes
    ----------
    geometry_id
        Foreign key to the geometry this Hessian was evaluated at.
    calculation_id
        Foreign key to the calculation that produced this Hessian.
    value
        Hessian matrix in Hartree/Bohr^2.
    geometry
        Geometry this Hessian was evaluated at.
    calculation
        Calculation that produced this Hessian.
    """

    __tablename__ = "hessian"
    model_config = SQLModelConfig(arbitrary_types_allowed=True)

    id: int | None = _pk_field()
    geometry_id: int | None = _fk_field("geometry.id")
    calculation_id: int | None = _fk_field("calculation.id")

    value: np.ndarray = Field(
        sa_column=Column(CompressedArrayTypeDecorator(dtype=np.float32))
    )

    calculation: "CalculationRow" = Relationship()
    geometry: "GeometryRow" = Relationship(back_populates="hessians")

    @cached_property
    def harmonic_frequencies(self) -> tuple[float, ...]:
        """Harmonic frequencies derived from the Hessian.

        Cached per instance, since vibrational analysis re-diagonalizes the
        Hessian on every call and `.order` (used by `_recompute_geometry_
        stationary_validity` for every sibling Hessian of a geometry, on
        every relevant flush) depends on it. Invalidated on `value` update
        by `invalidate_hessian_frequency_cache` in `events.py`.
        """
        freqs, _ = geom.vibrational_analysis(
            geo=self.geometry.to_geometry(), hess=self.value
        )
        return freqs

    @property
    def order(self) -> int:
        """Hessian order."""
        return sum(1 for f in self.harmonic_frequencies if f < 0.0)


# Calculation rows
class ModelRow(SQLModel, table=True):
    """Calculation model specification.

    Attributes
    ----------
    program
        Quantum chemistry program used (psi4, ORCA, ...)
    program_version
        Quantum chemistry program version.
    method
        Computational method (B3LYP, MP2, ...)
    basis
        Orbital basis set.
    """

    __tablename__ = "model"
    __table_args__ = (
        UniqueConstraint(
            "program",
            "program_version",
            "method",
            "basis",
            name="unique_model",
        ),
        # `unique_model` doesn't catch duplicates when `program_version` or `basis`
        # is NULL, since SQL treats NULL as distinct from itself in unique
        # constraints. This expression index closes that gap at the DB level.
        Index(
            "unique_model_null_safe",
            "program",
            text("coalesce(program_version, '')"),
            "method",
            text("coalesce(basis, '')"),
            unique=True,
        ),
    )

    id: int | None = _pk_field()
    program: str
    program_version: str | None = None
    method: str
    basis: str | None = None


class CalculationRow(SQLModel, table=True):
    """Quantum chemistry calculation and its associated data.

    Attributes
    ----------
    model_id
        Foreign key to the model used for this calculation.
    calc_type
        Type of calculation performed.
    status
        Lifecycle status of this calculation.
    error_message
        Error message recorded for a failed calculation, if any.
    input_provenance
        Metadata describing how the input was generated.
    output_provenance
        Metadata describing how the output was produced.
    model
        Model used for this calculation.
    geometry_links
        Raw link rows connecting geometries to this calculation.
    trajectory_links
        Raw link rows connecting trajectories to this calculation.
    """

    __tablename__ = "calculation"

    id: int | None = _pk_field()
    model_id: int | None = _fk_field("model.id")
    calc_type: CalcType = Field(
        sa_column=Column(Enum(CalcType, values_callable=lambda x: [e.value for e in x]))
    )
    status: CalcStatus = Field(
        default=CalcStatus.PENDING,
        sa_column=Column(
            Enum(CalcStatus, values_callable=lambda x: [e.value for e in x])
        ),
    )
    input_provenance: dict[str, Any] | None = Field(
        default_factory=dict, sa_column=Column(JSON)
    )
    output_provenance: dict[str, Any] | None = Field(
        default_factory=dict, sa_column=Column(JSON)
    )
    created: datetime | None = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={"server_default": func.now()},
    )
    error_message: str | None = Field(default=None)

    model: "ModelRow" = Relationship()
    geometry_links: list["CalculationGeometryLink"] = Relationship(
        back_populates="calculation"
    )
    trajectory_links: list["CalculationTrajectoryLink"] = Relationship(
        back_populates="calculation"
    )

    @property
    def input_geometries(self) -> list["GeometryRow"]:
        """Geometries linked to this calculation with an INPUT role."""
        return [
            link.geometry for link in self.geometry_links if link.role == Role.INPUT
        ]

    @property
    def output_geometries(self) -> list["GeometryRow"]:
        """Geometries linked to this calculation with an OUTPUT role."""
        return [
            link.geometry for link in self.geometry_links if link.role == Role.OUTPUT
        ]

    @property
    def input_trajectories(self) -> list["TrajectoryRow"]:
        """Trajectories linked to this calculation with an INPUT role."""
        return [
            link.trajectory for link in self.trajectory_links if link.role == Role.INPUT
        ]

    @property
    def output_trajectories(self) -> list["TrajectoryRow"]:
        """Trajectories linked to this calculation with an OUTPUT role."""
        return [
            link.trajectory
            for link in self.trajectory_links
            if link.role == Role.OUTPUT
        ]


class ValidationRow(SQLModel, table=True):
    """Validation result for a specific step and calculation.

    Attributes
    ----------
    calculation_id
        Foreign key to the calculation that performed this validation.
    method
        Type of validation step (e.g., ``irc``)
    extras
        Additional metadata attached to this validation.
    calculation
        Calculation that performed this validation.
    step
        Reaction step this validation belongs to.
    """

    __tablename__ = "validation"

    id: int | None = _pk_field()
    calculation_id: int | None = _fk_field("calculation.id")

    method: str
    # Intentionally unbounded free-form JSON; add a size/schema guardrail if
    # this is ever populated from a less-trusted input path.
    extras: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    calculation: "CalculationRow" = Relationship()
    step: "StepRow" = Relationship(
        back_populates="validations", link_model=StepValidationLink
    )


# Stationary point rows
class StationaryPointRow(SQLModel, table=True):
    """A stationary point on a potential energy surface.

    Attributes
    ----------
    geometry_id
        Foreign key to the underlying molecular geometry.
    calculation_id
        Foreign key to the calculation that identified this point.
    order
        Hessian index (0 for minima, 1 for first-order saddle points).
    is_pseudo
        Whether this point is not a true stationary point (e.g. constrained).
    geometry
        Geometry defining the coordinates of this point.
    calculation
        Calculation that identified this point.
    identities
        Chemical identifiers (e.g. InChI, SMILES) for this point.
    stages
        Reaction stages this stationary point belongs to.
    """

    __tablename__ = "stationary_point"

    id: int | None = _pk_field()
    geometry_id: int | None = _fk_field("geometry.id")
    calculation_id: int | None = _fk_field("calculation.id")
    order: int = 0
    is_pseudo: bool = False

    geometry: "GeometryRow" = Relationship(back_populates="stationary_points")
    calculation: "CalculationRow" = Relationship()
    identities: list["IdentityRow"] = Relationship(
        back_populates="stationary_points", link_model=StationaryIdentityLink
    )
    stages: list["StageRow"] = Relationship(
        back_populates="stationaries", link_model=StationaryStageLink
    )

    created: datetime | None = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated: datetime | None = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )

    def identity(
        self,
        *,
        kind: str | None = None,
        algorithm: Any | None = None,  # noqa: ANN401
    ) -> "IdentityRow | None":
        """Return the first loaded identity matching kind and/or algorithm.

        Searches `self.identities` (the already-loaded relationship list),
        not the database.
        """
        return next(
            (
                i
                for i in self.identities
                if (kind is None or i.kind == kind)
                and (algorithm is None or i.algorithm == algorithm)
            ),
            None,
        )


class IdentityRow(SQLModel, Identity, table=True):
    """A chemical identifier associated with one or more stationary points.

    Attributes
    ----------
    kind
        Category of identifier (e.g. ``stereoisomer``, ``formula``).
    algorithm
        Method used to generate the identifier (e.g. ``rdkit inchi``, ``rdkit smiles``).
    value
        The resulting identifier string.
    stationary_points
        Stationary points sharing this identity.
    identity_extras
        Additional key-value metadata attached to this identity.
    """

    __tablename__ = "identity"
    __table_args__ = (
        UniqueConstraint("kind", "algorithm", "value", name="unique_identity"),
    )

    id: int | None = _pk_field()

    stationary_points: list["StationaryPointRow"] = Relationship(
        back_populates="identities", link_model=StationaryIdentityLink
    )
    identity_extras: list["IdentityExtraRow"] = Relationship(back_populates="identity")


class IdentityExtraRow(SQLModel, table=True):
    """Additional key-value metadata attached to a chemical identity.

    Attributes
    ----------
    identity_id
        Foreign key to the parent identity.
    attribute
        Name of the extra attribute.
    value
        Value of the extra attribute.
    identity
        The parent identity this extra belongs to.
    """

    __tablename__ = "identity_extras"

    id: int | None = _pk_field()
    identity_id: int | None = _fk_field("identity.id")

    attribute: str
    value: str

    identity: "IdentityRow" = Relationship(back_populates="identity_extras")


# Reaction rows
class StageRow(SQLModel, table=True):
    """A chemical state (reactant, product, or transition state) in a reaction.

    Attributes
    ----------
    is_ts
        Whether this stage represents a transition state.
    stationaries
        Stationary points that make up this stage.
    steps
        Reaction steps referencing this stage as `stage1`, `stage2`, or
        `stage_ts` (read-only; derived from `StepRow`'s foreign keys).
    """

    __tablename__ = "stage"

    id: int | None = _pk_field()
    is_ts: bool = False

    stationaries: list["StationaryPointRow"] = Relationship(
        back_populates="stages", link_model=StationaryStageLink
    )
    steps: list["StepRow"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "or_("
            "StageRow.id == StepRow.stage_id1, "
            "StageRow.id == StepRow.stage_id2, "
            "StageRow.id == StepRow.stage_id_ts"
            ")",
            "viewonly": True,
        }
    )


class StepRow(SQLModel, table=True):
    """An elementary reaction step connecting a reactant, transition state, and product.

    Attributes
    ----------
    stage_id1, stage_id2
        Foreign keys to the step's two non-TS stages (stored with
        `stage_id1 < stage_id2`).
    stage_id_ts
        Foreign key to the step's transition-state stage, or `None` for a
        barrierless step.
    is_barrierless
        Whether this step proceeds without a formal transition state.
    stage1, stage2
        The step's two non-TS stages.
    stage_ts
        The step's transition-state stage, or `None` if barrierless.
    validations
        Validation calculations performed on this step.
    """

    __tablename__ = "step"
    __table_args__ = (
        UniqueConstraint(
            "stage_id1", "stage_id2", "stage_id_ts", name="unq_step_stages"
        ),
        CheckConstraint("stage_id1 < stage_id2", name="chk_stage_order"),
        # `unq_step_stages` doesn't catch duplicate barrierless steps (stage_id_ts
        # NULL), since SQL never treats NULL as equal to itself in a unique
        # constraint. This expression index closes that gap at the DB level.
        Index(
            "unq_step_stages_null_safe",
            "stage_id1",
            "stage_id2",
            text("coalesce(stage_id_ts, 0)"),
            unique=True,
        ),
        # `stage_id1` is already covered as the leading column of the two indexes
        # above, but is indexed explicitly here too for symmetry/clarity.
        Index("ix_step_stage_id1", "stage_id1"),
        Index("ix_step_stage_id2", "stage_id2"),
        Index("ix_step_stage_id_ts", "stage_id_ts"),
    )

    id: int | None = _pk_field()
    stage_id1: int | None = _fk_field("stage.id", index=False)
    stage_id2: int | None = _fk_field("stage.id", index=False)
    stage_id_ts: int | None = _fk_field("stage.id", nullable=True, index=False)

    is_barrierless: bool = False

    validations: list["ValidationRow"] = Relationship(
        back_populates="step", link_model=StepValidationLink
    )

    stage1: "StageRow" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[StepRow.stage_id1]"}
    )
    stage2: "StageRow" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[StepRow.stage_id2]"}
    )
    stage_ts: "StageRow" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[StepRow.stage_id_ts]"}
    )


class TrajectoryRow(SQLModel, table=True):
    """Ordered sequence of geometries from a calculation trajectory.

    Attributes
    ----------
    geometry_links
        Raw link rows connecting geometries to this trajectory.
    calculation_links
        Raw link rows connecting calculations to this trajectory.
    """

    __tablename__ = "trajectory"

    id: int | None = _pk_field()

    geometry_links: list["TrajectoryGeometryLink"] = Relationship(
        back_populates="trajectory"
    )
    calculation_links: list["CalculationTrajectoryLink"] = Relationship(
        back_populates="trajectory"
    )
