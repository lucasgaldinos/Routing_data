---
title: "Walkthrough — Task 10.11: routing_data v0.2.0 release"
description: >
  Execution record for Batch 2 / Task 10.11: packaging, upsert and batch
  isolation, explicit-matrix rounding and failure contract, symmetry detection,
  real database validation, output-writer guards, public distance exports, and
  the v0.2.0 tag.
created: 2026-11-03
related_files:
  - [knowledge_routing_data-v0.2.0-release.md](../knowledge-base/knowledge_routing_data-v0.2.0-release.md)
  - [TODO.md](../../../TODO.md)
tags:
  - notes/walkthrough
  - release/v0.2.0
  - analysis/data-integrity
---

# Walkthrough — Task 10.11 (`routing_data` `v0.2.0`)

## Objective

Close the `routing_data` findings that block `gpu_accelerated_clean` from consuming the
package as a library: non-idempotent writes, all-or-nothing batches, silent explicit-matrix
failure, format-guessed symmetry, a validation command that cannot fail, unsafe output
names, unbounded parquet identifiers, private distance math, and stale packaging metadata.

## Decisions taken

| Decision | Why |
| --- | --- |
| Per-problem transaction instead of SAVEPOINT | DuckDB rejects `SAVEPOINT` (`syntax error at or near "SAVEPOINT"`, verified on the project `.venv`), so the isolation boundary is one transaction per problem. |
| Upsert keeps the hub id | `solutions.problem_id` references `problems(id)`; replacing the hub would cascade or orphan solution rows. |
| `DataTransformer = ProblemNormalizer` alias | `TODO.md` D6 locks a class-only rename with the smallest ripple; the alias lets downstream code migrate on its own schedule. |
| JSON dedupe only for byte-identical content | Skipping all repeats would hide real updates; the existing overwrite test still passes. |
| Matrix dimension check skips CVRP | CVRP may store a customer-only matrix (`M8` accepted compromise), so requiring `len(matrix) == dimension` would flag valid data. |

## Failure / correction log

1. First integrity implementation used `array_length(matrix, 2)`. DuckDB raises
   `NotImplemented Error: array_length for lists with dimensions other than 1 not implemented`.
   Fixed by using `len(matrix)` / `len(matrix[1])`.
2. `ruff` S608 rejected f-string and concatenated SQL built from the fixed `_TYPE_TABLES`
   allowlist. Converted every dynamic query to a module-level template + `.replace()`.
3. The rename originally left `dict[str, Any]` callers in `api.py` / `worker_functions.py`;
   mypy rejected `NormalizedProblemData` assigned to `dict[str, Any]`. Callers were annotated
   with the `TypedDict` and `Mapping` signatures.

## Verification evidence

```bash
.venv/bin/python -m ruff check src tests   # All checks passed
.venv/bin/python -m mypy src               # Success: no issues found in 38 source files
.venv/bin/python -m pytest tests -q        # 425 passed, 1 xfailed
uv lock --check                            # lockfile resolved (routing-data 0.2.0)
```

Pre-change observations that now fail (each has a regression test):

| Observation | Regression test |
| --- | --- |
| Re-insert aborts on `UNIQUE(name, type)` | `test_reinserting_same_name_and_type_updates_in_place` |
| One refused row rolls back siblings | `test_batch_isolates_a_refused_problem` |
| `1.5` explicit weight stored as `1` | `test_fractional_explicit_weights_use_tsplib95_nint` |
| EXPLICIT conversion failure warns and continues | `test_explicit_conversion_failure_raises_transform_error` |
| `validate` exits 0 on a broken database | `test_missing_explicit_matrix_fails_validation` |
| `NAME` escapes the output directory | `test_hostile_name_is_sanitized_into_a_single_segment` |
| Arbitrary table exported via `COPY` | `test_parquet_export_rejects_non_allowlisted_table` |

## Affected files

- `pyproject.toml`, `uv.lock` — version `0.2.0`, `duckdb>=1.4.0`.
- `src/converter/database/operations.py` — `_upsert_problem_row`, per-problem batch loop,
  `load_problem_metadata`, `list_problem_metadata`, `load_matrix_metadata`, `load_solution`,
  `integrity_failures`.
- `src/converter/core/transformer.py` — `ProblemNormalizer`, `NormalizedProblemData`, `_nint`,
  `TransformError` on EXPLICIT failure.
- `src/tsplib_parser/parser.py` — `_check_symmetry` builds the matrix for `FULL_MATRIX`.
- `src/converter/cli/commands.py` — version from package, `validate` wired to
  `integrity_failures`.
- `src/converter/output/json_writer.py`, `output/parquet_writer.py` — naming guards,
  duplicate suppression, `ALLOWED_TABLES`.
- `src/converter/utils/cost.py` — public scalar exports and `COORDINATE_DISTANCES`.
- `src/converter/{api,__init__}.py`, `utils/{worker_functions,parallel,update,exceptions}.py`,
  `core/solutions.py` — rename migration and mypy debt.
- Deleted `convert_vrp.py`, `converter_cli.py`.
- Tests: five new files plus four updated expectations.

## Release

- Commit `7a46960`, annotated tag `v0.2.0`, pushed `main` and `v0.2.0` to `origin`.
