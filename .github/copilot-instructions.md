# TSPLIB95 ETL Converter - AI Coding Agent Instructions

## Project Overview

3-phase ETL pipeline converting academic routing problems (TSPLIB95 format) to JSON + DuckDB. Processes TSP, VRP, ATSP, HCP, SOP, TOUR instances with parallel processing and change detection.

**Key Insight**: TSPLIB95 uses 1-based indexing; we convert to 0-based during transformation. This is critical for all node/edge operations.

## Architecture: The 3-Layer Pattern

```text
src/format/          → Phase 1: Parse TSPLIB95 (vendored library + extensions)
src/converter/core/  → Phase 2: Transform & normalize data
src/converter/database/ + output/ → Phase 3: Dual output (DuckDB + JSON)
```

**Critical Flow**: `FormatParser.parse_file()` → `DataTransformer.transform_problem()` → `DatabaseManager.insert_problem()` + `JSONWriter.write_problem()`

### Why This Matters

- **src/format/** is vendored legacy code (1152+ type warnings acceptable). Use `FormatParser` wrapper, NOT `StandardProblem` directly.
- **Index conversion** happens in `transformer.py::_convert_to_zero_based()`. Test any node/edge code with both indexing systems.
- **Edge precomputation** only for EXPLICIT distance types (see `transformer.py::_compute_edges()`). Coordinate-based problems would create O(n²) explosion.

## Essential Commands

```bash
# Development (use 'uv' NOT 'pip')
uv sync                                    # Install dependencies
uv run pytest tests/ -v                    # Run all 134 tests
uv run pytest --cov=src --cov-report=term  # Coverage report

# CLI usage
uv run converter process -i datasets_raw/problems -o datasets/
uv run converter process --workers 1 --verbose  # Debug mode
uv run converter process --types TSP --types VRP  # Specific types

# Database inspection
duckdb datasets/db/routing.duckdb
  SHOW TABLES;
  SELECT type, COUNT(*) FROM problems GROUP BY type;
```

## Critical Patterns

### Exception Hierarchy (use specific types!)

```python
# src/converter/utils/exceptions.py defines:
ConverterError           # Base class
├── ExtractionError     # Parse failures (with problem_name)
├── TransformError      # Data conversion issues (with field_name)
├── DatabaseError       # DB operations (with operation)
└── OutputError         # File I/O failures (with file_path)

# src/format/exceptions.py (vendored):
FormatError → ParseError, ValidationError, UnsupportedFeatureError
```

Always use specific exceptions with context parameters: `raise TransformError("Invalid dimension", field_name="dimension")`

### Dependency Injection Pattern

ALL components take logger via `__init__`:

```python
# Pattern used throughout codebase
class Component:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
```

Never create loggers inside methods. Use `setup_logging()` from `utils/logging.py` at CLI entry points only.

### Testing Conventions

- **Fixtures in conftest.py**: `tsp_files_small`, `vrp_files`, `temp_output_dir`, `in_memory_db`
- **Test data location**: `datasets_raw/problems/{tsp,vrp,atsp}/` - use existing files, don't create new ones
- **Database tests**: Use `:memory:` via `in_memory_db` fixture to avoid file I/O
- **Test structure**: `test_format/` (24 tests), `test_converter/` (85 tests), `test_integration/` (25 tests)

Example pattern:

```python
def test_something(temp_output_dir, in_memory_db):
    """Test with temporary output and in-memory database."""
    parser = FormatParser(logger=setup_logging())
    data = parser.parse_file('datasets_raw/problems/tsp/gr17.tsp')
    assert data['problem_data']['type'] == 'TSP'
```

### Config Loading (YAML + Environment)

```python
# src/converter/config.py pattern
config = ConverterConfig.from_yaml('config.yaml')  # Or from_env()
# Access via: config.batch_size, config.max_workers, config.input_path
```

Don't hardcode paths/settings. Use `config.yaml` or CLI options.

## File Organization Rules

```text
src/format/           # VENDORED LEGACY - minimize edits, accept type errors
  parser.py          # ✓ Public API (use this)
  models.py          # ✗ Internal legacy (1152 type warnings - don't fix)
  
src/converter/
  api.py             # ✓ Simple public API for library usage
  core/              # ✓ Pipeline orchestration
    scanner.py       # File discovery with glob patterns
    transformer.py   # THE critical index conversion logic
  database/
    operations.py    # Thread-safe DB ops, each worker gets own connection
  output/
    json_writer.py   # Flattened JSON structure
  utils/
    parallel.py      # Memory-limited worker pool
    exceptions.py    # ✓ Use these specific types!
```

## Common Pitfalls

1. **Index confusion**: TSPLIB is 1-based, database is 0-based. Always verify which system you're in.
2. **Edge explosion**: Don't precompute edges for coordinate-based problems (EUC_2D, MAN_2D, GEO, ATT).
3. **Direct StandardProblem usage**: Use `FormatParser` wrapper instead.
4. **Generic exceptions**: Use specific types (`TransformError`, not `Exception`).
5. **Logger creation**: Inject via `__init__`, don't create in methods.
6. **Test data paths**: Use fixtures like `tsp_files_small`, not hardcoded paths.

## When Adding Features

### New TSPLIB Format Support

1. Add test file to `datasets_raw/problems/{type}/`
2. Write test in `tests/test_format/test_format_parser.py`
3. Extend `FormatParser` (not `StandardProblem`)
4. Update `transformer.py` if new fields need conversion
5. Run full integration: `uv run pytest tests/test_integration/test_pipeline.py`

### Database Schema Changes

1. Create migration in `src/converter/database/migrations/`
2. Update `operations.py::_initialize_schema()`
3. Add version tracking to prevent re-running migrations
4. Test with `:memory:` database first, then file-based

### Performance Optimization

Always benchmark before/after:

```bash
time uv run converter process -i datasets_raw/problems/tsp/ -o temp/
# Profile: python -m cProfile -o profile.stats ...
```

Memory limit per worker: 2048 MB (see `parallel.py`). Check with `psutil.Process().memory_info()`.

## Questions to Clarify Before Implementation

- **Index system**: Am I working with 1-based (TSPLIB) or 0-based (database) indices?
- **Distance type**: Does this problem type need edge precomputation (EXPLICIT) or on-demand calculation (coordinate-based)?
- **Thread safety**: Will this run in parallel workers? (If yes, check database connection handling)
- **Error context**: What specific exception type + context parameters should I use?

---

**Documentation**: See `docs/reference/ARCHITECTURE.md` for design decisions, `docs/development/DEVELOPER_WORKFLOW.md` for patterns.

**Current Status**: 134/134 tests passing, 63% coverage. Core pipeline production-ready. VRP extensions and advanced analytics partially implemented.
