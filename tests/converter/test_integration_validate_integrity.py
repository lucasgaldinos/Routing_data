"""``converter validate`` runs real integrity checks and fails on violations.

WHAT
----
The CLI ``validate`` command must exercise SQL checks over the schema-v2 tables
(``M11``) and exit 1 when any check reports a violation.

WHY
----
The command previously only printed statistics, so it could never fail. This
suite proves the exit code is coupled to actual integrity, not to file presence.

EXPECTED
--------
- A consistent database validates with exit code 0.
- A deleted EXPLICIT matrix row and a coordinate/dimension mismatch each exit 1
  with the corresponding check named in the output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import duckdb

from converter.cli.commands import cli
from converter.database.operations import DatabaseManager

if TYPE_CHECKING:
  from pathlib import Path

  from click.testing import CliRunner


def _tsp_payload(
  name: str,
  *,
  dimension: int,
  coords: list[list[float]] | None,
  matrix: list[list[int]] | None = None,
) -> dict[str, Any]:
  """Build a merged TSP payload, optionally EXPLICIT."""
  return {
    "name": name,
    "type": "TSP",
    "dimension": dimension,
    "comment": None,
    "capacity": None,
    "edge_weight_type": "EXPLICIT" if matrix else "EUC_2D",
    "edge_weight_format": "FULL_MATRIX" if matrix else None,
    "tsplib_name": None,
    "coords": coords,
    "display_coords": None,
    "demands": [],
    "depots": [],
    "adjacency": None,
    "fixed_edges": None,
    "edge_weight_data": ({"matrix": matrix, "matrix_format": "FULL_MATRIX", "is_symmetric": True} if matrix else None),
    "file_path": None,
    "checksum": None,
  }


def test_consistent_database_validates(cli_runner: CliRunner, tmp_path: Path) -> None:
  """WHAT: a database with one EXPLICIT and one coordinate problem.

  WHY: the new checks must not flag a valid database.
  EXPECTED: exit code 0 and the success message.
  """
  db_path: Path = tmp_path / "valid.duckdb"
  db = DatabaseManager(str(db_path))
  db.insert_problem(_tsp_payload("explicit", dimension=2, coords=None, matrix=[[0, 1], [1, 0]]))
  db.insert_problem(_tsp_payload("coords", dimension=2, coords=[[0.0, 0.0], [1.0, 1.0]]))

  result = cli_runner.invoke(cli, ["validate", "--database", str(db_path)])

  assert result.exit_code == 0, result.output
  assert "validation successful" in result.output.lower()


def test_missing_explicit_matrix_fails_validation(cli_runner: CliRunner, tmp_path: Path) -> None:
  """WHAT: delete the matrix row of an EXPLICIT problem.

  WHY: an EXPLICIT problem without its matrix is unreadable.
  EXPECTED: exit code 1 and the matrix check named in the output.
  """
  db_path: Path = tmp_path / "missing_matrix.duckdb"
  DatabaseManager(str(db_path)).insert_problem(
    _tsp_payload("explicit", dimension=2, coords=None, matrix=[[0, 1], [1, 0]])
  )
  with duckdb.connect(str(db_path)) as conn:
    conn.execute("DELETE FROM edge_weight_matrices")

  result = cli_runner.invoke(cli, ["validate", "--database", str(db_path)])

  assert result.exit_code == 1
  assert "edge-weight matrix" in result.output


def test_coordinate_dimension_mismatch_fails_validation(cli_runner: CliRunner, tmp_path: Path) -> None:
  """WHAT: a TSP row whose ``coords`` array is shorter than ``dimension``.

  WHY: a mismatched array silently breaks distance computation downstream.
  EXPECTED: exit code 1 and the coordinate check named in the output.
  """
  db_path: Path = tmp_path / "bad_coords.duckdb"
  DatabaseManager(str(db_path)).insert_problem(_tsp_payload("bad_coords", dimension=3, coords=[[0.0, 0.0], [1.0, 1.0]]))

  result = cli_runner.invoke(cli, ["validate", "--database", str(db_path)])

  assert result.exit_code == 1
  assert "coordinate" in result.output.lower()
