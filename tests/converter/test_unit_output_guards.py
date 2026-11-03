"""Output-writer guards: sanitized names, duplicate suppression, table allowlist.

WHAT
----
``JSONWriter`` writes ``<name>.<type>.json`` with sanitized segments and skips a
second write whose content is byte-identical; ``ParquetWriter`` refuses any table
outside ``ALLOWED_TABLES``.

WHY
----
An unsanitized ``NAME`` could escape the output directory, cross-type twins
(``att48`` as TSP and CVRP) shared one filename, re-runs rewrote identical files,
and the parquet ``COPY`` interpolated caller-supplied table names (``M2``,
``m17``).

EXPECTED
--------
- Hostile names stay inside ``output_dir`` and lose unsafe characters.
- Identical content is not rewritten; changed content is.
- A non-allowlisted table raises ``ValueError`` before any ``COPY`` runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pytest

from converter.output.json_writer import JSONWriter
from converter.output.parquet_writer import ALLOWED_TABLES, ParquetWriter


def _data(name: str = "dup", problem_type: str = "TSP") -> dict[str, Any]:
  """Minimal transformed payload accepted by ``JSONWriter``."""
  return {
    "problem_data": {"name": name, "type": problem_type},
    "tours": [],
    "metadata": {},
  }


def test_written_filename_carries_the_problem_type(tmp_path: Path) -> None:
  """WHAT: write a TSP problem with type organization.

  WHY: M2 — the type suffix keeps cross-type twins apart on disk.
  EXPECTED: ``<out>/tsp/dup.tsp.json``.
  """
  path: str = JSONWriter(output_dir=tmp_path).write_problem(_data())
  assert Path(path) == Path(tmp_path) / "tsp" / "dup.tsp.json"


def test_hostile_name_is_sanitized_into_a_single_segment(tmp_path: Path) -> None:
  """WHAT: a name containing traversal and punctuation.

  WHY: M2 — the output path must stay inside the output directory.
  EXPECTED: basename ``evil_name`` and a parent of ``<out>/tsp``.
  """
  path: Path = Path(JSONWriter(output_dir=tmp_path).write_problem(_data(name="../../evil name!")))
  assert path.name == "evil_name.tsp.json"
  assert path.parent == tmp_path / "tsp"
  assert path.resolve().is_relative_to(tmp_path.resolve())


def test_identical_content_is_not_rewritten(tmp_path: Path) -> None:
  """WHAT: two writes of the same payload with a sentinel injected in between.

  WHY: M2 — a duplicate run must not churn identical files.
  EXPECTED: the sentinel survives, proving the second write was skipped.
  """
  writer = JSONWriter(output_dir=tmp_path)
  path: Path = Path(writer.write_problem(_data()))
  path.write_text("sentinel", encoding="utf-8")

  assert writer.write_problem(_data()) == str(path)
  assert path.read_text(encoding="utf-8") == "sentinel"


def test_changed_content_is_rewritten(tmp_path: Path) -> None:
  """WHAT: a second write whose payload differs.

  WHY: M2 — skipping duplicates must not hide real updates.
  EXPECTED: the file content changes.
  """
  writer = JSONWriter(output_dir=tmp_path)
  first: Path = Path(writer.write_problem(_data()))
  original: str = first.read_text(encoding="utf-8")

  changed: dict[str, Any] = _data()
  changed["metadata"] = {"note": "changed"}
  writer.write_problem(changed)

  assert first.read_text(encoding="utf-8") != original


def test_parquet_export_rejects_non_allowlisted_table(tmp_path: Path) -> None:
  """WHAT: export a scratch table that is not part of the schema.

  WHY: m17 — the ``COPY <table>`` identifier must come from an allowlist.
  EXPECTED: ``ValueError`` and no parquet file written.
  """
  db_path: Path = tmp_path / "scratch.duckdb"
  with duckdb.connect(str(db_path)) as conn:
    conn.execute("CREATE TABLE scratch (value INTEGER)")

  writer = ParquetWriter(output_dir=str(tmp_path / "parquet"))
  with pytest.raises(ValueError, match="not allowed"):
    writer.export_from_database(str(db_path), tables=["scratch"])


def test_allowlist_covers_every_schema_table() -> None:
  """WHAT: the allowlist contents.

  WHY: m17 — the guard is useless if a real table is missing.
  EXPECTED: all schema tables are present and no extras are implied.
  """
  assert {
    "problems",
    "tsp_problems",
    "atsp_problems",
    "cvrp_problems",
    "hcp_problems",
    "sop_problems",
    "edge_weight_matrices",
    "file_tracking",
    "solutions",
  } == ALLOWED_TABLES
