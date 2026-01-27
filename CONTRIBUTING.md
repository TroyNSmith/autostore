# Contributing to autostore

Thank you for your interest in contributing to **autostore**!
Contributions of all kinds are welcome, including bug reports,
documentation improvements, and new features.

This document outlines the basic development workflow and coding
conventions used in the project.

## Development workflow

To get set up:
1. Install [Pixi](https://pixi.prefix.dev/latest/installation/)
2. Fork the repository
3. Clone the repository and run `pixi run init` inside it
To contribute code, submit pull requests with clear descriptions of the changes.
For larger contributions, create an issue first to propose your idea.

## Coding standards

Coding standards are largely enforced by the pre-commit hooks, which perform
formatting and linting ([Ruff](https://github.com/charliermarsh/ruff)),
import linting ([Lint-Imports](https://import-linter.readthedocs.io/en/stable/)),
static type-checking ([Ty](https://github.com/astral-sh/ty)),
and testing ([PyTest](https://docs.pytest.org/en/latest/))
with code coverage reports [CodeCov](https://docs.codecov.com/docs).

Docstrings follow the
[NumPy docstring standard](https://numpydoc.readthedocs.io/en/latest/format.html#docstring-standard).

## Naming Conventions

This project clearly separates **domain models** (in-memory, scientific objects) from **persistence models** (database-backed SQLModel tables). These two layers serve different purposes and are named accordingly.

### Domain Models (Pydantic)

Domain models represent scientific concepts used directly in computation and analysis.

**Characteristics:**
- Implemented using Pydantic (`BaseModel`)
- Used in-memory
- May include validation, units, helper methods, or NumPy integration
- Independent of database concerns

**Naming rule:**
- Use the clean, concept-level name with **no suffix**

**Example:**
```python
class Geometry(BaseModel):
    ...
```

---

### Persistence Models (SQLModel)

Persistence models represent rows stored in a database table.

**Characteristics:**
- Implemented using SQLModel (`SQLModel, table=True`)
- Used for storage, querying, and relationships
- Optimized for serialization and database compatibility
- Considered part of the infrastructure layer

**Naming rule:**
- All SQLModel table classes **must use the `Row` suffix**
- This applies universally, even if no naming conflict currently exists

**Example:**
```python
class GeometryRow(SQLModel, table=True):
    __tablename__ = "geometry"
    ...
```

---

### Rationale

This convention is intentionally strict and uniform:

- Avoids ambiguity between domain objects and database-backed objects
- Prevents future naming conflicts as the domain layer evolves
- Makes imports self-describing and predictable
- Keeps scientific terminology clean and uncluttered
- Reflects how SQLModel instances are typically used (as rows)

**Good:**
```python
from automol.geom import Geometry
from automol.db import GeometryRow
```

**Avoid:**
```python
from automol.geom import Geometry
from automol.db import Geometry  # ambiguous
```

---

## Summary

| Layer | Purpose | Naming |
|------|--------|--------|
| Domain | In-memory scientific models | `Geometry`, `Reaction`, `Molecule` |
| Persistence | SQLModel database tables | `GeometryRow`, `ReactionRow`, `MoleculeRow` |

If you add a new SQLModel table, always use the `Row` suffix — even if there is no corresponding domain model yet.

---

## Questions

If you have questions about contributing or design decisions, feel free
to open an issue for discussion.
