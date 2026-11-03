"""JSON output writer for TSPLIB converter."""

import json
import logging
import re
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..core.transformer import ProblemNormalizer

#: Characters allowed in an output name segment. Everything else (path
#: separators, traversal sequences, control characters) becomes ``_`` so a
#: hostile or malformed ``NAME`` can never escape the output directory (``M2``).
_UNSAFE_SEGMENT = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_segment(value: Any, fallback: str) -> str:
  """Return a filesystem-safe single path segment derived from ``value``.

  Uses only the basename, replaces every non-allowlisted run of characters
  with ``_``, and falls back when nothing usable remains. The result can never
  contain ``/``, ``\\`` or ``..``, so it cannot leave the output directory.
  """
  text: str = Path(str(value)).name.strip()
  cleaned: str = _UNSAFE_SEGMENT.sub("_", text).strip("._-")
  return cleaned or fallback


def _problem_filename(problem_name: Any, problem_type: Any) -> str:
  """Return ``<name>.<type>.json`` with both segments sanitized.

  The type suffix keeps cross-type twins (``att48`` as TSP and as CVRP)
  distinct on disk, mirroring the database's ``UNIQUE(name, type)`` (``M2``).
  """
  safe_name: str = _sanitize_segment(problem_name, "unknown")
  safe_type: str = _sanitize_segment(problem_type, "unknown").lower()
  return f"{safe_name}.{safe_type}.json"


class JSONWriter:
  """
  JSON output writer for TSPLIB converter.

  Features:
  - Flattened JSON structure generation
  - Directory organization by problem type
  - Sanitized ``<name>.<type>.json`` filenames
  - Duplicate suppression for identical ``(name, type)`` content
  - Pretty printing support
  """

  def __init__(
    self,
    output_dir: str | Path = "./datasets/json",
    pretty: bool = True,
    logger: logging.Logger | None = None,
  ) -> None:
    """
    Initialize JSON writer.

    Args:
        output_dir: Base directory for JSON output
        pretty: Whether to pretty-print JSON
        logger: Optional logger instance
    """
    self.output_dir = Path(output_dir)
    self.pretty = pretty
    self.logger = logger or logging.getLogger(__name__)
    self.transformer = ProblemNormalizer(logger=self.logger)
    # Content already written for each (name, type), guarded by a lock because
    # the CLI fans write_problem out over a thread pool (``M2``).
    self._written_content: dict[tuple[str, str], str] = {}
    self._lock = threading.Lock()

    # Create output directory
    self.output_dir.mkdir(parents=True, exist_ok=True)

  def write_problem(self, data: Mapping[str, Any], organize_by_type: bool = True) -> str:
    """
    Write problem data to JSON file.

    The file name is ``<sanitized name>.<sanitized type>.json``. A second write
    with the same ``(name, type)`` and byte-identical content is skipped; a
    write whose content differs replaces the file (idempotent re-runs stay
    cheap without hiding real updates).

    Args:
        data: Problem data dictionary
        organize_by_type: Whether to organize files by problem type

    Returns:
        Path to written (or already current) JSON file
    """
    problem_data: Mapping[str, Any] = data.get("problem_data", {}) or {}
    raw_name: Any = problem_data.get("name", "unknown")
    raw_type: Any = problem_data.get("type", "unknown")
    problem_name: str = _sanitize_segment(raw_name, "unknown")
    problem_type: str = _sanitize_segment(raw_type, "unknown")

    filename: str = _problem_filename(problem_name, problem_type)
    if organize_by_type:
      type_dir = self.output_dir / problem_type.lower()
      type_dir.mkdir(parents=True, exist_ok=True)
      output_path = type_dir / filename
    else:
      output_path = self.output_dir / filename

    # Use transformer to create consistent JSON structure (no duplication)
    json_data: dict[str, Any] = self.transformer.to_json_format(data)
    if self.pretty:
      serialized: str = json.dumps(json_data, indent=2, default=str)
    else:
      serialized = json.dumps(json_data, default=str)

    key: tuple[str, str] = (problem_name, problem_type)
    with self._lock:
      if self._written_content.get(key) == serialized and output_path.exists():
        self.logger.debug(f"Skipping duplicate JSON write: {output_path}")
        return str(output_path)
      self._written_content[key] = serialized

    # Write JSON file
    try:
      output_path.write_text(serialized, encoding="utf-8")

      self.logger.info(f"Wrote JSON file: {output_path}")
      return str(output_path)

    except Exception as e:
      self.logger.error(f"Failed to write JSON file {output_path}: {e}")
      raise

  def write_batch(self, data_list: list[Mapping[str, Any]], organize_by_type: bool = True) -> list[str]:
    """
    Write multiple problems to JSON files.

    Args:
        data_list: List of problem data dictionaries
        organize_by_type: Whether to organize by type

    Returns:
        List of paths to written JSON files
    """
    paths = []

    for data in data_list:
      try:
        path = self.write_problem(data, organize_by_type)
        paths.append(path)
      except Exception as e:
        self.logger.error(f"Failed to write problem: {e}")

    return paths

  def get_output_path(self, problem_name: str, problem_type: str | None = None, organize_by_type: bool = True) -> str:
    """
    Get output path for a problem without writing.

    Args:
        problem_name: Name of problem
        problem_type: Type of problem
        organize_by_type: Whether to organize by type

    Returns:
        Expected output path as string
    """
    safe_name = _sanitize_segment(problem_name, "unknown")
    safe_type: str | None = _sanitize_segment(problem_type, "unknown") if problem_type else None
    filename: str = _problem_filename(safe_name, safe_type or "unknown")
    if organize_by_type and safe_type:
      type_dir = self.output_dir / safe_type.lower()
      output_path = type_dir / filename
    else:
      output_path = self.output_dir / filename

    return str(output_path)
