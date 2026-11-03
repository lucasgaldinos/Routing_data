"""Idempotent upserts, per-problem batch isolation, and consumer read methods.

WHAT
----
``DatabaseManager`` write/read contracts introduced for ``routing_data``
``v0.2.0``:
- ``insert_problem`` updates an existing ``(name, type)`` in place (``B1``);
- ``insert_problems_batch`` isolates a failing problem in its own transaction
  (``B3``);
- ``load_problem_metadata`` / ``list_problem_metadata`` / ``load_solution``
  expose the schema-v2 joins to downstream loaders (``DP10-14``).

WHY
----
A re-run used to abort on the UNIQUE constraint and roll back the whole batch,
while a single refused row also rolled back every sibling. Consumers otherwise
had to re-implement the hub/type-table joins.

EXPECTED
--------
- Re-inserting the same ``(name, type)`` keeps the hub id, replaces the type
  row, and leaves one hub row.
- A mixed batch stores the valid problems and reports the refused one by name.
- The read methods return the loader-facing keys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import duckdb

from converter.database.operations import DatabaseManager

if TYPE_CHECKING:
  from pathlib import Path


def _worker_result(name: str, problem_type: str = "TSP", dimension: int = 3) -> dict[str, Any]:
  """Build a worker-shaped result accepted by ``insert_problems_batch``."""
  return {
    "success": True,
    "file_path": None,
    "problem_data": {
      "name": name,
      "type": problem_type,
      "dimension": dimension,
      "comment": None,
      "capacity": None,
      "edge_weight_type": "EUC_2D",
      "edge_weight_format": None,
    },
    "coords": [[float(index), 0.0] for index in range(dimension)],
    "display_coords": None,
    "demands": [],
    "depots": [],
    "edges": None,
    "fixed_edges": None,
    "edge_weight_data": None,
    "checksum": None,
  }


def _tsp_payload(
  name: str = "synthetic",
  dimension: int = 3,
  edge_weight_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
  """Build the merged payload ``insert_problem`` expects."""
  return {
    "name": name,
    "type": "TSP",
    "dimension": dimension,
    "comment": None,
    "capacity": None,
    "edge_weight_type": "EXPLICIT" if edge_weight_data else "EUC_2D",
    "edge_weight_format": "FULL_MATRIX" if edge_weight_data else None,
    "tsplib_name": None,
    "coords": None if edge_weight_data else [[0.0, 0.0] for _ in range(dimension)],
    "display_coords": None,
    "demands": [],
    "depots": [],
    "adjacency": None,
    "fixed_edges": None,
    "edge_weight_data": edge_weight_data,
    "file_path": None,
    "checksum": None,
  }


def test_reinserting_same_name_and_type_updates_in_place(tmp_path: Path) -> None:
  """WHAT: insert ``synthetic/TSP`` twice with different dimensions.

  WHY: B1 — a re-run must update, not crash on the UNIQUE constraint.
  EXPECTED: same hub id, one hub row, and the second dimension is stored.
  """
  db = DatabaseManager(str(tmp_path / "upsert.duckdb"))
  first_id: int = db.insert_problem(_tsp_payload(dimension=3))
  second_id: int = db.insert_problem(_tsp_payload(dimension=4))

  assert first_id == second_id
  with duckdb.connect(str(tmp_path / "upsert.duckdb"), read_only=True) as conn:
    assert conn.execute("SELECT COUNT(*) FROM problems").fetchone() == (1,)
    assert conn.execute("SELECT COUNT(*) FROM tsp_problems").fetchone() == (1,)
  assert db.load("synthetic", "TSP")["dimension"] == 4


def test_upsert_replaces_the_edge_weight_matrix(tmp_path: Path) -> None:
  """WHAT: re-insert an EXPLICIT problem with a larger matrix.

  WHY: B1 — stale satellite rows must not survive an update.
  EXPECTED: ``load_matrix`` returns the second matrix only.
  """
  db = DatabaseManager(str(tmp_path / "matrix.duckdb"))
  db.insert_problem(
    _tsp_payload(
      dimension=2,
      edge_weight_data={"matrix": [[0, 1], [1, 0]], "matrix_format": "FULL_MATRIX", "is_symmetric": True},
    )
  )
  db.insert_problem(
    _tsp_payload(
      dimension=3,
      edge_weight_data={
        "matrix": [[0, 1, 2], [1, 0, 3], [2, 3, 0]],
        "matrix_format": "FULL_MATRIX",
        "is_symmetric": True,
      },
    )
  )

  assert db.load_matrix("synthetic", "TSP") == [[0, 1, 2], [1, 0, 3], [2, 3, 0]]


def test_batch_isolates_a_refused_problem(tmp_path: Path) -> None:
  """WHAT: ``good1``, a ``TOUR`` payload, and ``good2`` in one batch.

  WHY: B3 — one refused type must not roll back valid siblings.
  EXPECTED: two inserted, one failure named ``bad``, and both good rows stored.
  """
  db = DatabaseManager(str(tmp_path / "batch.duckdb"))
  result: dict[str, Any] = db.insert_problems_batch(
    [
      _worker_result("good1"),
      _worker_result("bad", problem_type="TOUR"),
      _worker_result("good2"),
    ]
  )

  assert result["total_inserted"] == 2
  assert result["total_failed"] == 1
  assert result["failed"][0]["name"] == "bad"
  with duckdb.connect(str(tmp_path / "batch.duckdb"), read_only=True) as conn:
    stored = {row[0] for row in conn.execute("SELECT name FROM problems").fetchall()}
  assert stored == {"good1", "good2"}


def test_read_methods_expose_loader_metadata(tmp_path: Path) -> None:
  """WHAT: read back an inserted problem through the consumer methods.

  WHY: DP10-14 — loaders consume named shapes instead of raw joins.
  EXPECTED: metadata keys are present, the list contains the row, and the
  absent solution is ``None``.
  """
  db = DatabaseManager(str(tmp_path / "reads.duckdb"))
  problem_id: int = db.insert_problem(_tsp_payload(dimension=3))

  metadata: dict[str, Any] = db.load_problem_metadata(problem_id)
  assert metadata["problem_id"] == problem_id
  assert metadata["name"] == "synthetic"
  assert metadata["edge_type"] == "EUC_2D"
  assert metadata["raw_coords"] is not None

  listed: list[dict[str, Any]] = db.list_problem_metadata("TSP")
  assert [row["name"] for row in listed] == ["synthetic"]
  assert db.load_solution(problem_id) is None
