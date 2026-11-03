"""Explicit-matrix normalization contracts for ``ProblemNormalizer``.

WHAT
----
Two invariants of ``ProblemNormalizer.transform_problem``:
- fractional explicit weights are rounded with TSPLIB95 ``nint``
  (``int(floor(x + 0.5))``) because ``edge_weight_matrices.matrix`` is
  ``INTEGER[][]`` (``M3`` / ``DP10-12``);
- an ``EDGE_WEIGHT_TYPE: EXPLICIT`` problem whose weights cannot be converted
  raises ``TransformError`` so the worker discards it instead of storing a row
  without its only distance data (``M4``).

WHY
----
``int()`` truncates and reads back a different distance than the file declares;
warning-and-continuing on a broken EXPLICIT matrix produced readable hub rows
that no distance consumer can load. Both defects are silent at write time.

EXPECTED
--------
- ``1.5`` stores as ``2`` and ``2.5`` stores as ``3``.
- An unsupported EXPLICIT format raises instead of returning a matrix-less row.
- The same conversion failure is tolerated for a non-EXPLICIT weight type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest

from converter.core.transformer import NormalizedProblemData, ProblemNormalizer
from converter.utils.exceptions import TransformError

if TYPE_CHECKING:
  from tsplib_parser.types import ParseResult


def _parse_result(
  *,
  edge_weights: list[list[float]] | None,
  edge_weight_format: str = "FULL_MATRIX",
  edge_weight_type: str = "EXPLICIT",
) -> ParseResult:
  """Build a minimal ``ParseResult`` carrying an explicit weight payload."""
  problem_data: dict[str, Any] = {
    "name": "synthetic",
    "type": "TSP",
    "comment": None,
    "dimension": len(edge_weights or []),
    "capacity": None,
    "node_coord_type": None,
    "edge_weight_type": edge_weight_type,
    "display_data_type": None,
    "edge_weight_format": edge_weight_format,
    "edge_data_format": None,
  }
  if edge_weights is not None:
    problem_data["edge_weights"] = edge_weights
  payload: dict[str, Any] = {
    "problem_data": problem_data,
    "coords": [],
    "display_coords": [],
    "demands": [],
    "depots": [],
    "edges": [],
    "fixed_edges": [],
    "tours": [],
    "metadata": {
      "file_path": "synthetic.tsp",
      "file_name": "synthetic.tsp",
      "file_size": 0,
      "has_coordinates": False,
      "has_demands": False,
      "has_depots": False,
      "has_tours": False,
      "has_edges": False,
      "has_fixed_edges": False,
      "is_symmetric": True,
      "weight_source": "explicit_matrix",
      "problem_source": None,
    },
  }
  # The fixture is structurally a ParseResult; the cast documents that intent.
  return cast("ParseResult", payload)


def test_fractional_explicit_weights_use_tsplib95_nint() -> None:
  """WHAT: explicit weights ``1.5`` and ``2.5``.

  WHY: M3 — the INTEGER[][] column must receive the spec's rounded value.
  EXPECTED: ``1.5 -> 2`` and ``2.5 -> 3`` (half-up), not truncation.
  """
  normalized: NormalizedProblemData = ProblemNormalizer().transform_problem(
    _parse_result(edge_weights=[[0.0, 1.5], [2.5, 0.0]])
  )
  assert normalized["edge_weight_matrix"] == [[0, 2], [3, 0]]


def test_explicit_conversion_failure_raises_transform_error() -> None:
  """WHAT: an EXPLICIT problem with an unknown ``EDGE_WEIGHT_FORMAT``.

  WHY: M4 — a matrix-less EXPLICIT row is unreadable downstream.
  EXPECTED: ``TransformError`` naming the crash, not a warning.
  """
  with pytest.raises(TransformError, match="EXPLICIT"):
    ProblemNormalizer().transform_problem(
      _parse_result(edge_weights=[[0.0, 1.0], [1.0, 0.0]], edge_weight_format="BOGUS")
    )


def test_non_explicit_conversion_failure_is_tolerated() -> None:
  """WHAT: the same bad format on a non-EXPLICIT weight type.

  WHY: only EXPLICIT problems depend on the matrix for their distances.
  EXPECTED: no raise, and no ``edge_weight_matrix`` key in the payload.
  """
  normalized: NormalizedProblemData = ProblemNormalizer().transform_problem(
    _parse_result(edge_weights=[[0.0, 1.0], [1.0, 0.0]], edge_weight_format="BOGUS", edge_weight_type="EUC_2D")
  )
  assert "edge_weight_matrix" not in normalized
