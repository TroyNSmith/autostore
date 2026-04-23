# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]
- Separated Provenance fields from Calculation fields and created new ProvenanceRow to store the separated data.
- Removed standalone qc module; integrated specific functions as methods on Row objects (specifically CalculationRow, ProvenanceRow, and GeometryRow).
- Updated ModelRow attributes to follow snake_case guidelines.
- CalculationRow.calc_type: str -> str | None to reduce redundancy at user-level. calc_type should be set by lower-level methods.
- Modified calcn.core.project to avoid accidentally modifying the original Calculation instance.
- Modified calcn.core.hash_full to reflect refactoring of CalculationRow attributes.
- Database.query updated to skip NULL values and ids; method now always returns a list[RowID | None].
- Convenience methods on GeometryRow for converting to/from Geometry & Structure.
- StationaryPointRow now cascade deletes on deletion of linked GeometryRow / CalculationRow
- Updated RowIDs type to list[RowID | None] for flexibility of Database methods.
- Reworked all of the tests to facilitate debugging.


## [0.0.5] - 2026-04-09
### Added
- Added superprogram fields to CalculationRow.
- Updated qc interfaces to reflect update from qcio -> qcdata
- Database row models moved from models/* to models.py
- Added Database methods for adding, getting, and querying rows from database
- CalculationGeometryLink table to associate Calculation with input/output Geometries
  - Calculation Geometries can be accessed by CalculationRow.geometries
  - Geometry Calculations can be accessed by GeometryRow.calculations
- Placeholder MetricRow for storing identifying properties




## [0.0.4] - 2026-04-01

## [0.0.3] - 2026-01-29
### Added
- Geometry hash field populated by event listener
- Calculation object with hash registry
- Calculation hash table populated by event listener
- Interconversion of Calculation and QCIO ProgramInput objects
- Read energy from database

### Fixed
- Specify Calculation-Energy and Geometry-Energy as many-to-one relationships
- Uniqueness constraint in CalculationHashRow

## [0.0.2] - 2026-01-28
### Added
- `qc` submodule for interconversion with `QCIO` objects

### Fixed
- Fix coordinate units (Angstrom) in geometry table

## [0.0.1] - 2026-01-28
### Added
- Write energy to database
