"""Example: inspect the ``ParseResult`` contract on real corpus files.

Prints, per file, the type and shape of every key returned by
:meth:`FormatParser.parse_file`, so the payload can be inspected without a
debugger.

Run from the repository root:

    uv run python examples/inspect_parse_result.py
    uv run python examples/inspect_parse_result.py --corpus /path/to/datasets_raw
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from tsplib_parser.parser import FormatParser

if TYPE_CHECKING:
  from tsplib_parser.types import ParseResult, ProblemData

SAMPLE_FILES: tuple[str, ...] = (
  "tsp/gr17.tsp",
  "vrp/eil22.vrp",
  "tour/kroD100.opt.tour",
  "hcp/alb1000.hcp",
)


def describe(value: object) -> str:
  """Describe one payload value shape without printing the whole value."""
  if isinstance(value, Mapping):
    return f"{type(value).__name__} keys={sorted(str(key) for key in value)}"
  if isinstance(value, Sequence) and not isinstance(value, str | bytes):
    first = type(value[0]).__name__ if value else "empty"
    return f"{type(value).__name__} len={len(value)} first={first}"
  return f"{type(value).__name__} = {value!r}"


def inspect(relative: str, corpus: Path) -> ParseResult:
  """Parse ``relative`` under ``corpus`` and print its key shapes."""
  result = FormatParser().parse_file(corpus / relative)
  print(f"--- {relative} ---")
  for key, value in result.items():
    print(f"  {key:15} {describe(value)}")
  return result


def main() -> None:
  """Inspect every sample file named in :data:`SAMPLE_FILES`."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
    "--corpus",
    type=Path,
    default=Path("datasets_raw/problems"),
    help="Directory holding the sample files (default: datasets_raw/problems)",
  )
  args = parser.parse_args()

  problems: list[ParseResult] = [inspect(relative, args.corpus) for relative in SAMPLE_FILES]
  first_problem_data: ProblemData = problems[0]["problem_data"]
  print("problem_data keys:", sorted(first_problem_data))


if __name__ == "__main__":
  main()
