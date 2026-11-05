"""Example: parse the first problem file of every corpus folder.

Walks a fixed list of corpus sub-folders, parses the first non-solution file of
each one, and prints a one-line summary. Cordeau MDVRP folders go through
:class:`CordeauParser`, everything else through :class:`FormatParser`.

Run from the repository root:

    uv run python examples/scan_corpus_folders.py
    uv run python examples/scan_corpus_folders.py --corpus /path/to/datasets_raw
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tsplib_parser.cordeau.cordeau_parser import CordeauParser
from tsplib_parser.parser import FormatParser

PROBLEM_FOLDERS: tuple[str, ...] = (
  "problems/tsp",
  "problems/atsp",
  "problems/sop",
  "problems/hcp",
  "problems/vrp",
  "problems/tour",
  "cvrplib/Holmberger",
  "cvrplib/VRP-set-D",
  "cvrplib/Vrp-Set-Li",
  "cvrplib/Vrp-Set-Solomon",
  "cvrplib/vrp-XXL",
  "umalaga/mdvrp/C-mdvrp",
)

CORDEAU_FOLDER_SUFFIX = "C-mdvrp"
SOLUTION_SUFFIXES = frozenset({".sol", ".res"})


def first_problem(directory: Path) -> Path | None:
  """Return the first non-solution file in ``directory``, or ``None``."""
  if not directory.is_dir():
    return None
  for candidate in sorted(directory.iterdir()):
    if candidate.is_file() and candidate.suffix not in SOLUTION_SUFFIXES:
      return candidate
  return None


def describe_cordeau(path: Path) -> str:
  """Summarize a Cordeau MDVRP file."""
  problem = CordeauParser().parse_file(path)
  return f"Cordeau type={problem.type_name} dim={problem.dimension} depots={problem.num_depots}"


def describe_tsplib(path: Path) -> str:
  """Summarize a TSPLIB95 / TSPLIB-extended file."""
  result = FormatParser().parse_file(path)
  data = result["problem_data"]
  return (
    f"type={data['type']} dim={data['dimension']} "
    f"coords={len(result['coords'])} demands={len(result['demands'])} "
    f"depots={len(result['depots'])} tours={len(result['tours'])} "
    f"ewt={data['edge_weight_type']}"
  )


def main() -> None:
  """Parse one file per corpus folder and print a summary line."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
    "--corpus",
    type=Path,
    default=Path("datasets_raw"),
    help="Root of the raw corpus (default: datasets_raw)",
  )
  args = parser.parse_args()

  corpus: Path = args.corpus
  for folder in PROBLEM_FOLDERS:
    target = first_problem(corpus / folder)
    if target is None:
      print(f"{folder:32} EMPTY")
      continue
    try:
      summary = describe_cordeau(target) if folder.endswith(CORDEAU_FOLDER_SUFFIX) else describe_tsplib(target)
    except Exception as exc:  # intentional: the example reports every failure
      print(f"{folder:32} {target.name:16} FAIL {type(exc).__name__}: {exc}")
      continue
    print(f"{folder:32} {target.name:16} OK  {summary}")


if __name__ == "__main__":
  main()
