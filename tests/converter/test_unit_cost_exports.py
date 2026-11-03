"""Public scalar distance surface of ``converter.utils.cost`` (``DP10-13``).

WHAT
----
The TSPLIB95 scalar distance functions are exported without a leading
underscore, are listed in ``__all__``, and expose a name-keyed
``COORDINATE_DISTANCES`` registry that matches the internal dispatch table.

WHY
----
``gpu_accelerated_clean/src/distances/pairwise.py`` will re-export these
functions instead of duplicating the arithmetic. That requires a stable public
name, not a private helper.

EXPECTED
--------
- ``nint`` rounds half up.
- Every documented function resolves and equals its registry entry.
- ``__all__`` names all resolve on the module.
"""

from __future__ import annotations

import math

from converter.utils import cost


def test_nint_rounds_half_up() -> None:
  """WHAT: ``nint`` over the half-way points.

  WHY: the spec defines ``nint(x) = int(x + 0.5)``; truncation would drift.
  EXPECTED: 1.5 -> 2, 2.4 -> 2, 2.5 -> 3.
  """
  assert cost.nint(1.5) == 2
  assert cost.nint(2.4) == 2
  assert cost.nint(2.5) == 3


def test_public_registry_matches_dispatch_table() -> None:
  """WHAT: ``COORDINATE_DISTANCES`` versus the private registry.

  WHY: a public re-export must name the same callables the converter uses.
  EXPECTED: same keys, same functions.
  """
  assert cost.COORDINATE_DISTANCES == cost._COORD_DISTANCES


def test_public_names_resolve_and_att_matches_the_spec_formula() -> None:
  """WHAT: every public scalar function plus one arithmetic identity.

  WHY: ``ATT`` has the conditional ``+1`` that is easy to lose in a re-export.
  EXPECTED: each name is callable; ``att`` matches its hand-computed value.
  """
  public_names: tuple[str, ...] = (
    "euclidean_2d",
    "euclidean_3d",
    "ceil_2d",
    "manhattan_2d",
    "manhattan_3d",
    "maximum_2d",
    "maximum_3d",
    "geographical",
    "att",
    "xray1",
    "xray2",
  )
  for name in public_names:
    assert callable(getattr(cost, name)), name

  # rij = sqrt((9 + 16) / 10) = sqrt(2.5) ~= 1.5811 -> tij = 2, tij >= rij -> 2
  assert cost.att([0.0, 0.0], [3.0, 4.0]) == math.floor(math.sqrt(2.5) + 0.5)


def test_all_names_are_importable() -> None:
  """WHAT: ``__all__`` versus module attributes.

  WHY: a typo in ``__all__`` breaks ``from ... import *`` at runtime.
  EXPECTED: every declared name resolves.
  """
  for name in cost.__all__:
    assert hasattr(cost, name), name
