---
title: "Knowledge — routing_data v0.2.0 data-integrity invariants"
description: >
  Reusable rules for the DuckDB schema-v2 write path, explicit-matrix integer
  contract, JSON/Parquet output guards, and the consumer read surface.
created: 2026-11-03
related_files:
  - [walkthrough_10-11_v0.2.0.md](../task-resolutions/walkthrough_10-11_v0.2.0.md)
tags:
  - notes/knowledge
  - architecture/database
  - analysis/data-integrity
---

# Knowledge — `routing_data` `v0.2.0`

## 1. DuckDB has no savepoints

`SAVEPOINT`, `ROLLBACK TO SAVEPOINT` and `RELEASE SAVEPOINT` raise `ParserException` on the
pinned DuckDB. Per-row isolation must therefore be a transaction boundary:

```python
with duckdb.connect(str(db_path)) as conn:
  for payload in payloads:
    conn.execute("BEGIN TRANSACTION")
    try:
      upsert(conn, payload)
      conn.execute("COMMIT")
    except Exception as exc:
      conn.execute("ROLLBACK")      # this problem only
      failed.append({"name": payload["name"], "error": str(exc)})
```

Evidence: `src/converter/database/operations.py` (`insert_problems_batch`), regression
`tests/converter/test_unit_database_upsert.py::test_batch_isolates_a_refused_problem`.

## 2. Upsert keeps the hub id

`UNIQUE (name, type)` makes `(name, type)` the identity. Updating means: keep `problems.id`,
refresh `updated_at`, delete the owning type-table row and `edge_weight_matrices` row, then
re-insert both inside the same transaction. Deleting the hub instead would break
`solutions.problem_id`.

## 3. `INTEGER[][]` needs TSPLIB95 `nint`

The parser accepts fractional explicit weights; the column is integer. Round with
`int(math.floor(x + 0.5))`, never `int(x)` (truncation) or `round()` (banker's rounding).

## 4. Nested list lengths in DuckDB

`array_length(col, 2)` is not implemented for `LIST[]` columns. Use `len(col)` for the outer
length and `len(col[1])` for the inner row length.

## 5. Output-file contract

- JSON filename: `<sanitized name>.<sanitized type lowercased>.json`; sanitization is
  `Path(value).name` then `[^A-Za-z0-9._-]+ -> _`, then strip `._-`.
- Identical `(name, type)` content is skipped under a `threading.Lock`; different content
  overwrites.
- Parquet `COPY` identifiers must come from `ALLOWED_TABLES`; never interpolate a caller string.

## 6. Consumer read surface (`DP10-14`)

| Method | Returns |
| --- | --- |
| `list_problem_metadata(type)` | hub + owning type-table columns, ordered by dimension/name, plus `edge_type` |
| `load_problem_metadata(problem_id)` | loader-facing keys (`raw_coords`, `raw_demands`, `source_file`, …) |
| `load_matrix_metadata(problem_id)` | `matrix_format`, `is_symmetric`, `matrix` or `None` |
| `load_solution(problem_id)` | `kind`, `quality`, `cost`, `routes`, … or `None` |

## 7. Validation that can fail

`DatabaseManager.integrity_failures()` returns one dict per violating row across seven checks;
`converter validate` prints them and exits 1. Matrix/dimension equality is enforced only for
TSP/ATSP because CVRP may legitimately store a customer-only matrix.
