"""Parquet output writer for TSPLIB converter.

Exports routing problem data to Apache Parquet format for efficient
columnar storage and analysis with ML frameworks.
"""

import logging
from pathlib import Path
from typing import Any

import duckdb

#: Tables this writer may export. The export builds a ``COPY <table> TO ...``
#: statement, so the identifier is constrained to this allowlist instead of
#: interpolating whatever an external caller passes (``m17``).
ALLOWED_TABLES: frozenset[str] = frozenset(
  {
    "problems",
    "tsp_problems",
    "atsp_problems",
    "cvrp_problems",
    "hcp_problems",
    "sop_problems",
    "edge_weight_matrices",
    "file_tracking",
    "solutions",
  }
)


def _assert_allowed_table(table: str) -> str:
  """Return ``table`` when it is in :data:`ALLOWED_TABLES`, else raise."""
  if table not in ALLOWED_TABLES:
    raise ValueError(f"Table not allowed for parquet export: {table!r}")
  return table


class ParquetWriter:
  """
  Parquet output writer for TSPLIB converter.

  Features:
  - Export tables to Parquet columnar format
  - Efficient for data science and ML workflows
  - Compression support (snappy, gzip, zstd)
  - Single-file or multi-file export modes

  Example:
      >>> writer = ParquetWriter(output_dir="datasets/parquet")
      >>> writer.export_from_database("db/routing.duckdb")
      >>> # Creates one file per table, e.g. problems.parquet,
      >>> # tsp_problems.parquet, cvrp_problems.parquet, edge_weight_matrices.parquet
  """

  def __init__(
    self, output_dir: str = "./datasets/parquet", compression: str = "snappy", logger: logging.Logger | None = None
  ) -> None:
    """
    Initialize Parquet writer.

    Args:
        output_dir: Base directory for Parquet output
        compression: Compression codec ('snappy', 'gzip', 'zstd', 'uncompressed')
        logger: Optional logger instance
    """
    self.output_dir = Path(output_dir)
    self.compression = compression
    self.logger = logger or logging.getLogger(__name__)

    # Create output directory
    self.output_dir.mkdir(parents=True, exist_ok=True)
    self.logger.info(f"Parquet writer initialized: {self.output_dir}")

  def export_from_database(
    self, db_path: str, tables: list[str] | None = None, single_file: bool = False
  ) -> dict[str, str]:
    """
    Export tables from DuckDB database to Parquet files.

    Args:
        db_path: Path to DuckDB database file
        tables: List of table names to export (None = all tables)
        single_file: If True, export all tables to single multi-table Parquet

    Returns:
        Dict mapping table names to output file paths

    Raises:
        FileNotFoundError: If database file doesn't exist
        ValueError: If a requested table does not exist or is not an allowlisted
            schema table (:data:`ALLOWED_TABLES`)

    Example:
        >>> writer = ParquetWriter()
        >>> files = writer.export_from_database("db/routing.duckdb", tables=["problems", "solutions"])
        >>> print(files)
        {'problems': 'datasets/parquet/problems.parquet', ...}
    """
    db_file = Path(db_path)
    if not db_file.exists():
      raise FileNotFoundError(f"Database not found: {db_file}")

    conn = duckdb.connect(str(db_file), read_only=True)

    try:
      # Get available tables
      available_tables: list[str] = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]

      # Determine tables to export. Only whitelisted schema tables are exposed;
      # anything else in the database (scratch tables, views) is ignored.
      if tables is None:
        export_tables: list[str] = [table for table in available_tables if table in ALLOWED_TABLES]
      else:
        # Validate requested tables: they must exist and be allowlisted.
        invalid = set(tables) - set(available_tables)
        if invalid:
          raise ValueError(f"Tables not found: {invalid}")
        export_tables = [_assert_allowed_table(table) for table in tables]

      self.logger.info(f"Exporting {len(export_tables)} tables to Parquet")

      if single_file:
        return self._export_single_file(conn, export_tables)
      else:
        return self._export_multi_file(conn, export_tables)

    finally:
      conn.close()

  def _export_multi_file(self, conn: duckdb.DuckDBPyConnection, tables: list[str]) -> dict[str, str]:
    """Export each table to a separate Parquet file (allowlisted identifiers only)."""
    output_files: dict[str, str] = {}

    for table in tables:
      safe_table: str = _assert_allowed_table(table)
      output_path: Path = self.output_dir / f"{safe_table}.parquet"

      # DuckDB native Parquet export. ``safe_table`` is an identifier from the
      # ALLOWED_TABLES allowlist, never caller-controlled text.
      query = f"""
                COPY {safe_table}
                TO '{output_path}'
                (FORMAT PARQUET, COMPRESSION '{self.compression}')
            """

      self.logger.debug(f"Exporting table '{table}' to {output_path}")
      conn.execute(query)

      # Get file size for logging
      size_mb = output_path.stat().st_size / (1024 * 1024)
      self.logger.info(f"✓ Exported {table}: {size_mb:.2f} MB ({output_path.name})")

      output_files[table] = str(output_path)

    return output_files

  def _export_single_file(self, conn: duckdb.DuckDBPyConnection, tables: list[str]) -> dict[str, str]:
    """
    Export all tables to single Parquet file with table metadata.

    Note: Uses nested structure with table name as column.
    Useful for archival but less convenient for direct analysis.
    """
    # Create a unified structure
    # This is a simplified approach - for production you might want
    # to use a proper multi-table format like Iceberg

    self.logger.warning(
      "Single-file export creates separate files with '_all' suffix. "
      "For true single-file storage, consider using database file directly."
    )

    # For now, just export to separate files with common prefix
    output_files: dict[str, str] = {}
    for table in tables:
      safe_table: str = _assert_allowed_table(table)
      table_output = self.output_dir / f"routing_data_{safe_table}.parquet"

      query = f"""
                COPY {safe_table}
                TO '{table_output}'
                (FORMAT PARQUET, COMPRESSION '{self.compression}')
            """

      conn.execute(query)
      output_files[table] = str(table_output)

      size_mb = table_output.stat().st_size / (1024 * 1024)
      self.logger.info(f"✓ Exported {table}: {size_mb:.2f} MB")

    return output_files

  def export_table(self, db_path: str, table_name: str, output_filename: str | None = None) -> str:
    """
    Export single table to Parquet file.

    Args:
        db_path: Path to DuckDB database file
        table_name: Name of table to export
        output_filename: Custom output filename (default: {table_name}.parquet)

    Returns:
        Path to created Parquet file

    Example:
        >>> writer = ParquetWriter()
        >>> path = writer.export_table("db/routing.duckdb", "problems", output_filename="tsp_problems.parquet")
    """
    if output_filename is None:
      output_filename = f"{table_name}.parquet"
    # Basename only: a custom name must not be able to leave the output dir.
    output_filename = Path(output_filename).name

    files = self.export_from_database(db_path, tables=[table_name])

    # Rename if custom filename provided
    if output_filename != f"{table_name}.parquet":
      old_path = Path(files[table_name])
      new_path = self.output_dir / output_filename
      old_path.rename(new_path)
      return str(new_path)

    return files[table_name]

  def get_parquet_info(self, parquet_file: str) -> dict[str, Any]:
    """
    Get metadata information about a Parquet file.

    Args:
        parquet_file: Path to Parquet file

    Returns:
        Dict with file metadata (row_count, columns, size_mb, etc.)

    Example:
        >>> writer = ParquetWriter()
        >>> info = writer.get_parquet_info("datasets/parquet/problems.parquet")
        >>> print(f"Rows: {info['row_count']}, Columns: {info['column_count']}")
    """
    parquet_path = Path(parquet_file)

    if not parquet_path.exists():
      raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

    conn = duckdb.connect(":memory:")

    try:
      # Get schema / row count from the Parquet file. The file path is a
      # value (never user-controlled query structure), substituted into a
      # fixed template.
      describe_sql = "DESCRIBE SELECT * FROM '{parquet_path}'".replace("{parquet_path}", str(parquet_path))
      count_sql = "SELECT COUNT(*) FROM '{parquet_path}'".replace("{parquet_path}", str(parquet_path))
      schema = conn.execute(describe_sql).fetchall()

      # Get row count
      row: tuple[Any, ...] | None = conn.execute(count_sql).fetchone()
      if row is None:
        raise ValueError(f"Unable to read row count from {parquet_path}")
      row_count = row[0]

      # Get file size
      size_mb = parquet_path.stat().st_size / (1024 * 1024)

      return {
        "file_path": str(parquet_path),
        "row_count": row_count,
        "column_count": len(schema),
        "columns": [{"name": col[0], "type": col[1]} for col in schema],
        "size_mb": round(size_mb, 2),
        "compression": self.compression,
      }

    finally:
      conn.close()


def export_database_to_parquet(
  db_path: str,
  output_dir: str = "./datasets/parquet",
  compression: str = "snappy",
  logger: logging.Logger | None = None,
) -> dict[str, str]:
  """
  Convenience function to export entire database to Parquet files.

  Args:
      db_path: Path to DuckDB database file
      output_dir: Output directory for Parquet files
      compression: Compression codec to use
      logger: Optional logger instance

  Returns:
      Dict mapping table names to output file paths

  Example:
      >>> from converter.output.parquet_writer import export_database_to_parquet
      >>> files = export_database_to_parquet("db/routing.duckdb")
      >>> print(f"Exported {len(files)} tables")
  """
  writer = ParquetWriter(output_dir=output_dir, compression=compression, logger=logger)
  return writer.export_from_database(db_path)
