"""Example: inspect the edges reported for an ``ADJ_LIST`` instance.

``FormatParser.parse_file`` needs a path, so this example writes an inline
TSPLIB95 ``ADJ_LIST`` instance to a temporary ``.tsp`` file, parses it, and
prints the 0-based edge pairs the parser reports.

Run from the repository root:

    uv run python examples/inspect_adjacency_edges.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from tsplib_parser.parser import FormatParser

if TYPE_CHECKING:
  from tsplib_parser.types import ParseResult

ADJ_LIST_INSTANCE = """NAME : adj
TYPE : TSP
DIMENSION : 4
EDGE_WEIGHT_TYPE : EXPLICIT
EDGE_WEIGHT_FORMAT : FULL_MATRIX
EDGE_DATA_FORMAT : ADJ_LIST
EDGE_DATA_SECTION
1 2 3 -1
2 1 -1
3 1 -1
4 -1
-1
EDGE_WEIGHT_SECTION
0 1 1 9
1 0 9 9
1 9 0 9
9 9 9 0
EOF
"""


def parse_inline_instance(text: str) -> ParseResult:
  """Parse ``text`` through :class:`FormatParser` via a temporary file."""
  with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / "adj.tsp"
    target.write_text(text, encoding="utf-8")
    return FormatParser().parse_file(target)


def main() -> None:
  """Parse the inline instance and print its adjacency edges."""
  result = parse_inline_instance(ADJ_LIST_INSTANCE)
  print("edge_data_format:", result["problem_data"]["edge_data_format"])
  print("top-level edges:", result["edges"])


if __name__ == "__main__":
  main()
