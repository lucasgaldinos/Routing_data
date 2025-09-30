## AI agent guide for this repo (tsplib95-based converter)

This workspace vendors tsplib95 under `src/tsplib95` and includes tests in `tests/`. Goal (see `README.md`): parse TSPLIB/VRP instances and convert them into JSON or a DuckDB database. Datasets live under `datasets/`.

Architecture overview

**TSPLIB95 Core Components:**

- `models.py`: `Problem` base and `StandardProblem` with metaclass `FileMeta` mapping TSPLIB keywords to fields. Key methods: `parse/read/load`, `as_name_dict()/as_keyword_dict()`, `get_nodes()/get_edges()`, `get_graph(normalize)`, `get_weight(i,j)`, `trace_tours`.
- `fields.py`: TSPLIB sections as fields (e.g., `NAME`, `TYPE`, `DIMENSION`, `EDGE_WEIGHT_SECTION`, `NODE_COORD_SECTION`, `TOUR_SECTION`).
- `transformers.py`: Reusable text↔data transformers (`ListT`, `MapT`, `UnionT`, `FuncT`, `NumberT`) with separator/terminal handling and contextual errors.
- `distances.py`: `TYPES` maps `EDGE_WEIGHT_TYPE` to functions (`EUC_2D`, `MAN_2D`, `CEIL_2D`, `GEO`, `ATT`, `XRAY*`).
- `matrix.py`: `TYPES` maps `EDGE_WEIGHT_FORMAT` to matrix classes (`FULL_MATRIX`, `UPPER_DIAG_ROW`, etc.).
- `loaders.py`: Thin façade (`load/read/parse`) with optional `problem_class` and `special` function.
- `cli.py`: Click command `summarize` printing columns such as `DIMENSION`, `TYPE`, `EDGE_WEIGHT_TYPE`, `EDGE_WEIGHT_FORMAT`.

**ETL Converter Architecture:**

- `src/converter/core/scanner.py`: File discovery with recursive traversal, type detection via extensions/content, batch processing with parallel workers, and comprehensive error handling.
- `src/converter/core/parser.py`: TSPLIB95 integration wrapper using `loaders.load()`, StandardProblem validation, special distance function handling, and parsing error recovery.
- `src/converter/core/transformer.py`: Data extraction from Problem objects, normalization (1-based→0-based indexing), format conversion for JSON/DB output, and metadata enrichment.
- `src/converter/database/schema.py`: DuckDB table definitions, index management, constraint validation, and migration system for schema evolution.
- `src/converter/database/operations.py`: Bulk insert operations with prepared statements, conflict resolution strategies, incremental updates, and analytical query functions.
- `src/converter/output/json_writer.py`: Flattened JSON structure generation, schema validation, directory management, and optional compression.
- `src/converter/cli/commands.py`: Click-based CLI with process/validate/analyze commands, progress reporting, and configuration management.

Project structure & current state

- `datasets_raw/problems/{tsp,vrp,atsp,hcp,sop,tour}/` - Raw problem files organized by type
- `datasets/zips/` - Downloaded archived datasets
- `src/converter/` - ETL system implementation (see `docs/implementation-plan.md`)
  - `core/` - Scanner, parser, and transformer modules
  - `database/` - DuckDB schema, models, and CRUD operations
  - `output/` - JSON writer and format definitions
  - `cli/` - Command-line interface and configuration
  - `utils/` - Logging, parallel processing, and validation utilities
- `datasets/json/` - Target for JSON output (flattened structure)
- `datasets/db/` - Target for DuckDB database (problems/nodes/edges schema)
- `docs/implementation-plan.md` - Comprehensive implementation guide and architecture
- `docs/diagrams/converter-architecture.mmd` - Detailed system architecture diagram
- `docs/diagrams/database-schema.mmd` - Complete database schema with relationships
- `docs/diagrams/database-queries.mmd` - Query patterns and data organization strategies

Conventions and gotchas

**TSPLIB95 Library:**

- Field mapping lives on `StandardProblem` (e.g., `dimension = F.IntegerField('DIMENSION')`); `FileMeta` builds name↔keyword maps automatically.
- Defaults are lazy: `Problem.__getattribute__` uses `Field.get_default_value()`; to serialize only non-defaults, prefer `as_name_dict()` / `as_keyword_dict()`.
- Weight source: if `is_explicit()` use a matrix from `EDGE_WEIGHT_SECTION`; otherwise use `edge_weight_type` from `distances.TYPES`. For `TYPE=SPECIAL`, pass a callable via `special=` to `loaders.load`.
- Indices/tours: node indices are typically 1-based; `Matrix` respects `min_index`. `ToursField` uses `-1` as a required terminator.
- Graphs: `get_graph(normalize=True)` yields 0-based sequential node IDs; node attrs: `coord`, `display`, `demand`, `is_depot`; edge attrs: `weight`, `is_fixed`.

**Converter Implementation:**

- Always use `StandardProblem.as_name_dict()` for clean data extraction - excludes default values and provides consistent field names.
- Handle `SPECIAL` edge weight types by detecting missing `EDGE_WEIGHT_SECTION` and requiring custom distance functions.
- Normalize node indexing: TSPLIB uses 1-based, database uses 0-based sequential IDs, Use only 0 based indexing.
- Process VRP demands/depots: extract from `DEMAND_SECTION`/`DEPOT_SECTION` fields, mark depot nodes with `is_depot=True`.
- Error handling hierarchy: `FileProcessingError` for parsing issues, `ValidationError` for data inconsistencies, `DatabaseError` for storage problems.
- Parallel processing: use thread-safe database connections, batch inserts for performance, maintain file-level error isolation.
- Update detection: compare file modification times, use database timestamps, implement incremental processing for large datasets.

Developer workflow

- Setup: Use `uv` for venv management (already present). Install deps: `uv add duckdb networkx click tabulate deprecated pytest pyyaml`.
- Runtime deps: `networkx`, `click`, `tabulate`, `deprecated`, `duckdb`, `pyyaml`; tests use `pytest`. Python ≥ 3.11.
- Run tests from repo root: `pytest -q` or target a single test like `tests/test_models.py::TestStandardProblem::test_get_graph`.
- CLI examples:
  - `python -m tsplib95.cli summarize datasets_raw/problems/tsp/gr17.tsp` - Inspect parsed metadata
  - `python -m converter.cli process --input datasets_raw/problems --output datasets/` - Run ETL conversion
  - `python -m converter.cli validate --config config/converter.yaml` - Validate configuration
- Current development focus: Implement ETL system per `docs/implementation-plan.md` with phased approach.

Typical usage

**Library Operations:**

- Load/inspect: `from tsplib95 import loaders; p = loaders.load('datasets_raw/problems/tsp/gr17.tsp'); p.get_weight(1, 2); p.as_keyword_dict(); G = p.get_graph(normalize=True)`.
- SPECIAL distance: define `def w(a, b): ...` where `a`/`b` are coords, then `p = loaders.load(path, special=w)`.
- Convert to JSON: build from `p.as_name_dict()` (or `as_keyword_dict()` if mirroring TSPLIB keywords). For tours, remember `-1` termination.

**ETL Operations:**

- Scanner usage: `from src.converter.core.scanner import FileScanner; scanner = FileScanner(); files = scanner.scan_directory('datasets_raw/problems', patterns=['*.tsp', '*.vrp'])`.
- Parser usage: `from src.converter.core.parser import TSPLIBParser; parser = TSPLIBParser(); problem_data = parser.parse_file(file_path)`.
- Database operations: `from src.converter.database.operations import DatabaseManager; db = DatabaseManager('datasets/db/routing.duckdb'); db.insert_problem(problem_data)`.
- JSON output: `from src.converter.output.json_writer import JSONWriter; writer = JSONWriter('datasets/json'); writer.write_problem(problem_data)`.

**Database Queries:**

- Connect: `import duckdb; conn = duckdb.connect('datasets/db/routing.duckdb')`.
- Find problems: `SELECT * FROM problems WHERE type = 'TSP' AND dimension > 100 ORDER BY dimension`.
- Get problem with nodes: `SELECT p.*, n.* FROM problems p JOIN nodes n ON p.id = n.problem_id WHERE p.name = 'gr17'`.
- Edge analysis: `SELECT AVG(weight), MIN(weight), MAX(weight) FROM edges WHERE problem_id = 1`.
- Problem statistics: `SELECT type, COUNT(*), AVG(dimension), MAX(dimension) FROM problems GROUP BY type`.
- VRP depot analysis: `SELECT p.name, COUNT(*) depot_count FROM problems p JOIN nodes n ON p.id = n.problem_id WHERE p.type = 'VRP' AND n.is_depot = true GROUP BY p.id, p.name`.
- Distance distribution: `SELECT CASE WHEN weight < 10 THEN '0-10' WHEN weight < 50 THEN '10-50' ELSE '50+' END range, COUNT(*) FROM edges WHERE problem_id = ? GROUP BY range`.
- Performance queries: Use indexes on (type, dimension), (problem_id, node_id), (problem_id, from_node, to_node) for efficient joins and filtering.

Extending for new VRP datasets

- Parse source files into a `StandardProblem` (populate `dimension`, `node_coords`, `demands`, `depots`, `edge_weights` or provide `special`). Reuse `get_weight`, `get_graph`, and `as_*_dict` for downstream conversion.
- Target VRP formats include Cordeau instances (`pr01`-`pr20`) for MDVRP/VRPPDTW - see `docs/vrps.md` for detailed analysis of problem characteristics and recommendations.

Where to start reading

- `src/tsplib95/models.py` (weight/graph), `fields.py` (available sections), `transformers.py` (parsing rules), `distances.py` and `matrix.py` (selection logic), and `tests/` (behavioral examples, sample inputs under `tests/data`).
