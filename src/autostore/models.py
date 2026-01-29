"""Models."""

from typing import Optional

from automol import Geometry, geom
from automol.types import FloatArray
from pydantic import ConfigDict
from qcio import ProgramInput, Results
from sqlalchemy import event
from sqlalchemy.types import JSON, String
from sqlmodel import Column, Field, Relationship, SQLModel

from . import qc
from .types import FloatArrayTypeDecorator

# ====================
# Calculation Loop
# ====================

# ===== Core entities
# NOTE: Organized depth-first (i.e. most independent tables first)

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

class CalculationRow(SQLModel, table=True):
    """
    Calculation table row.

    Parameters
    ----------
    id
        Primary key.
    program
        The quantum chemistry program used (e.g., "Psi4", "Gaussian").
    version
        The version of the program used.
    method
        Computational method (e.g., "B3LYP", "MP2").
    basis
        Basis set, if applicable.
    input
        Input file for the calculation, if applicable.

    energy
        Relationship to the associated energy record, if present.

    Notes
    -----
    Additional fields such as keywords, cmdline_args, and files may be added in
    the future to support programs that do not use an input file.
    """

    __tablename__ = "calculation"

    id: int | None = Field(default=None, primary_key=True)
    program: str
    version: str
    method: str
    basis: str | None = None
    input: str | None = None

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
                version=res.provenance.program_version,
                method=res.input_data.model.method,
                basis=res.input_data.model.basis,
            )

        msg = f"Instantiation from {type(res.input_data)} not yet implemented."
        raise NotImplementedError(msg)

    # Eventually add missing QCIO `ProgramArgs` fields:
    #   - keywords
    #   - cmdline_args
    #   - files
    # These could be used for programs like PySCF that do not use an input file.

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

# Events
# NOTE: Clearer to organize entities separate from events

@event.listens_for(GeometryRow, "before_insert")
def populate_geometry_hash(mapper, connection, target: GeometryRow) -> None:  # noqa: ANN001, ARG001
    """Populate GeometryRow hash before inserts and updates."""
    geo = Geometry(
        symbols=target.symbols,
        coordinates=target.coordinates,
        charge=target.charge,
        spin=target.spin,
    )
    target.hash = geom.hash(geo)

# ====================
# Stationary Loop
# ====================

# ===== Core entities
# NOTE: Organized depth-first (i.e. most independent tables first)

class StationaryPointIdentityMetadataRow(SQLModel, table=True):
    """
    Stores key-value metadata for stationary point identities.

    Parameters
    ----------
    id
        Primary key.
    identity_id
        Foreign key to the associated stationary point identity.
    attribute
        Name of the metadata attribute.
    value
        Value of the metadata attribute.
    identity
        Parent stationary point identity.

    Notes
    -----
    Metadata is stored as key-value pairs to support extensible
    identity annotations without scheme updates.
    """

    __tablename__ = "stationary_point_identity_metadata"

    id: int | None = Field(default=None, primary_key=True)

    identity_id: int = Field(foreign_key="stationary_point_identity.id")
    attribute: str
    value: str

    identity: "StationaryPointIdentity" = Relationship(
        back_populates="identity_metadata"
    )

class StationaryPointIdentitySchemeRow(SQLModel, table=True):
    """
    Stationary point identity schema.

    Parameters
    ----------
    id
        Primary key.
    type
        High-level identity type (e.g., amchi, custom).
    algorithm
        Algorithm used to generate the identity (e.g., rdkit, automol).
    variant
        Variant of the identity definition.
    defines_identifier
        Whether this scheme defines the canonical identity of a stationary point.
    identities
        Stationary point identities associated with this scheme.

    Notes
    -----
    Identity schemes define how stationary point identities are generated and interpreted.
    """

    __tablename__ = "stationary_point_identity_scheme"

    id: int | None = Field(default=None, primary_key=True)

    type: str
    algorithm: str
    variant: str 
    defines_identifier: bool

    identities: list["StationaryPointIdentity"] = Relationship(back_populates="scheme")
    # NOTE: stationary point identity scheme constructed as one-to-many with stationary point identity
    # to broaden querying abilities in the future

class StationaryPointIdentityRow(SQLModel, table=True):
    """
    Represents an identity assigned to a stationary point.
    
    Parameters
    ----------
    id
        Primary key.
    scheme_id
        Foreign key to the identity scheme used.
    stationary_point_id
        Foreign key to the associated stationary point.
    scheme
        Identity scheme defining this identity.
    stationary_point
        Stationary point this identity belongs to.
    identity_metadata
        Optional metadata entries associated with this identity.

    Notes
    -----
    A stationary point may have multiple identities generated using different schemes.
    """

    __tablename__ = "stationary_point_identity"

    id: int | None = Field(default=None, primary_key=True)

    scheme_id: int = Field(foreign_key="stationary_point_identity_scheme.id")
    stationary_point_id: int = Field(foreign_key="stationary_point.id")

    scheme: "StationaryPointIdentitySchemeRow" = Relationship(back_populates="identities")
    stationary_point: "StationaryPointRow" = Relationship(back_populates="identities")

    identity_metadata: list["StationaryPointIdentityMetadataRow"] | None = Relationship(
        back_populates="identity", cascade_delete=True
    )

class StationaryPointIdentityLink(SQLModel, table=True):
    """
    Link table between stationary points and identities.

    Parameters
    ----------
    id
        Primary key.
    stationary_point_id
        Foreign key to a stationary point.
    stationary_point_identity_id
        Foreign key to a stationary point identity.

    Notes
    -----
    Enables many-to-many relationships between stationary points and identities.
    """

    __tablename__ = "stationary_point_identity_link"

    stationary_point_id: int = Field(foreign_key="stationary_point.id", primary_key=True)
    stationary_point_identity_id: int = Field(foreign_key="stationary_point_identity.id", primary_key=True)

class StationaryPointRow(SQLModel, table=True):
    """
    Stores information about stationary points.

    Parameters
    ----------
    id
        Primary key.
    structure_id
        Foreign key to the associated molecular structure.
    calculation_id
        Foreign key to the calculation producing the stationary point.
    order
        Order of the stationary point (e.g., minimum, transition state).
    structure
        Associated molecular geometry.
    calculation
        Associated calculation record.
    stages
        Reaction stages associated with this stationary point.
    identities
        Identities assigned to this stationary point.

    Notes
    -----
    Stages is set as a placeholder for now.
    """

    __tablename__ = "stationary_point"

    id: int | None = Field(default=None, primary_key=True)

    structure_id: int = Field(foreign_key="structure.id")
    calculation_id: int = Field(foreign_key="calculation.id")

    order: int

    structure: "Geometry" = Relationship(back_populates="stationary_points")
    calculation: "Calculation" = Relationship(back_populates="stationary_points")

    # stages: list["Stage"] = Relationship(
    #     back_populates="stationary_points", link_model=StationaryPointStageLink
    # )

    identities: list["StationaryPointIdentityRow"] = Relationship(
        back_populates="stationary_point", link_model=StationaryPointIdentityLink
    )