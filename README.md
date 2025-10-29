# TSPLIB95 ETL Converter

[![Tests](https://img.shields.io/badge/tests-134%2F134%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-63%25-yellow)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

**High-performance ETL pipeline for converting TSPLIB95 routing problem instances to queryable database and analytics-ready formats.**

## 🎯 What It Does

Transforms academic routing problem benchmarks (TSP, VRP, ATSP, HCP, SOP) from the TSPLIB95 format into:

- **DuckDB database** - Fast SQL queries and analytics
- **JSON files** - Human-readable, easily parseable
- **Parquet files** - Columnar format for data science and ML workflows

### Key Features

- ✅ **3-phase ETL pipeline**: Parse → Transform → Load
- ✅ **Parallel processing**: 27x speedup with ProcessPoolExecutor
- ✅ **Change detection**: Only process modified files
- ✅ **Hybrid storage**: Coordinates + distance matrices
- ✅ **Dual output**: DuckDB + JSON + Parquet
- ✅ **134/134 tests passing** with 63% coverage

## 📦 Installation

```bash
# Clone repository
git clone <repo-url>
cd Routing_data

# Install dependencies (using uv - recommended)
uv sync

# Or with pip
pip install -r requirements.txt
```

**Requirements**: Python 3.11+, DuckDB, pandas

## 🚀 Quick Start

### 1. Process TSPLIB Files

```bash
# Process all files in datasets_raw/problems/
uv run converter process -i datasets_raw/problems -o datasets/

# Parallel processing with 8 workers
uv run converter process -i datasets_raw/problems --workers 8

# Process specific problem types
uv run converter process --types TSP --types VRP

# Force reprocessing (ignore change detection)
uv run converter process --force
```

### 2. Export to Parquet

```bash
# Export all tables to Parquet format
uv run converter export-parquet -d datasets/db/routing.duckdb

# Export specific tables
uv run converter export-parquet -t problems -t nodes -o ./parquet/

# Use different compression
uv run converter export-parquet -c zstd

# Available compression: snappy (default), gzip, zstd, uncompressed
```

### 3. Query the Database

```python
import duckdb

# Connect to database
conn = duckdb.connect('datasets/db/routing.duckdb')

# Get all TSP problems
problems = conn.execute("""
    SELECT name, dimension, edge_weight_type
    FROM problems
    WHERE type = 'TSP'
    ORDER BY dimension
""").fetchall()

# Get problem with nodes
result = conn.execute("""
    SELECT p.name, p.dimension, COUNT(n.node_id) as node_count
    FROM problems p
    LEFT JOIN nodes n ON p.id = n.problem_id
    WHERE p.name = 'gr17'
    GROUP BY p.name, p.dimension
""").fetchone()
```

### 4. Load Parquet Files

```python
import pandas as pd
import polars as pl

# With pandas
problems_df = pd.read_parquet('datasets/parquet/problems.parquet')
nodes_df = pd.read_parquet('datasets/parquet/nodes.parquet')

# With polars (faster for large datasets)
problems_pl = pl.read_parquet('datasets/parquet/problems.parquet')
nodes_pl = pl.read_parquet('datasets/parquet/nodes.parquet')

# With DuckDB (zero-copy, most efficient)
import duckdb
conn = duckdb.connect(':memory:')
df = conn.execute("SELECT * FROM 'datasets/parquet/problems.parquet'").df()
```

## 📊 Database Schema

### Tables

- **problems** - Problem metadata (name, type, dimension, edge_weight_type, etc.)
- **nodes** - Node coordinates and attributes (x, y, z, demand, is_depot)
- **edge_weight_matrices** - Distance matrices for EXPLICIT problems
- **solutions** - Optimal routes and costs
- **file_tracking** - Change detection (checksums, last_processed)

### Storage Model

**Hybrid approach** for optimal space efficiency:

| Problem Type | Storage Method | Example |
|-------------|----------------|---------|
| **Coordinate-based** (EUC_2D, GEO, ATT) | Store (x,y) coordinates, compute distances on-demand | `gr17.tsp`, `berlin52.tsp` |
| **EXPLICIT** (ATSP, irregular) | Store full distance matrix as JSON | `br17.atsp`, `ft53.atsp` |

**Why this matters**: Only 15% of TSP problems need matrix storage. The rest use coordinates, saving massive storage space.

## 🎨 Architecture

```text
TSPLIB95 ETL Pipeline (3-Phase Design)

Phase 1: PARSE                Phase 2: TRANSFORM            Phase 3: LOAD
────────────────────          ──────────────────            ─────────────────
[TSPLIB Files]                [Standardize]                 [DuckDB]
 ├─ br17.atsp                  ├─ 1-based → 0-based          ├─ problems
 ├─ gr17.tsp      →  Parser  →  ├─ Matrix conversion   →     ├─ nodes
 ├─ att48.tsp                  └─ Field normalization        ├─ edge_weight_matrices
 └─ eil51.tsp                                                ├─ solutions
                                                             └─ [JSON Files]
                                                                 [Parquet Files]
```

### Key Components

- **`src/tsplib_parser/`** - TSPLIB95 format parsing (Field-based extraction)
- **`src/converter/core/`** - Data transformation & pipeline orchestration
- **`src/converter/database/`** - DuckDB operations (thread-safe, batch inserts)
- **`src/converter/output/`** - JSON & Parquet writers
- **`src/converter/utils/`** - Parallel processing, logging, exceptions

## ⚡ Performance

**Processing Speed** (113 TSP files, 301K nodes):

| Mode | Time | Throughput |
|------|------|------------|
| **Sequential** (old) | 389s | 0.29 files/sec |
| **Parallel** (8 workers) | 14.4s | 7.85 files/sec |
| **Speedup** | **27x faster** | - |

**Breakdown**:

- Parsing: 3.2s (ProcessPoolExecutor, bypasses GIL)
- Transformation: 2.1s
- Database insert: 2.3s (pandas bulk insert)
- JSON write: 1.8s (ThreadPoolExecutor, parallel I/O)

**Storage Efficiency**:

| Format | Size | Compression | Best For |
|--------|------|-------------|----------|
| **JSON** | 8.14 MB | None | Human-readable, web APIs |
| **Parquet** | 6.27 MB | Snappy (default) | Data science, ML pipelines |
| **Parquet (zstd)** | ~4.5 MB | High compression | Long-term archival |
| **DuckDB** | ~12 MB | Built-in compression | SQL queries, analytics |

## 🧪 Testing

```bash
# Run all tests (134 tests)
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ --cov=src --cov-report=term-missing

# Quick test run
uv run pytest tests/ -q

# Run specific test category
uv run pytest tests/test_format/ -v        # Format module (24 tests)
uv run pytest tests/test_converter/ -v    # Converter module (85 tests)
uv run pytest tests/test_integration/ -v  # Integration (25 tests)
```

**Test Suite Overview**:

- **Total Tests**: 134 ✅
- **Pass Rate**: 100% (134/134)
- **Code Coverage**: 63% (Core modules: 80-100%)

**Core Module Coverage**:

- Transformer: 100% ✅
- Scanner: 94% ✅
- JSON Writer: 89% ✅
- Database: 85% ✅
- CLI Commands: 80% ✅

## 📚 Documentation

### User Guides

- [Getting Started](docs/guides/GETTING_STARTED.md) - Installation and first steps
- [User Guide](docs/guides/USER_GUIDE.md) - Detailed usage examples
- [Troubleshooting](docs/guides/TROUBLESHOOTING.md) - Common issues and solutions

### Technical Reference

- [Architecture](docs/reference/ARCHITECTURE.md) - Design decisions and patterns
- [API Reference](docs/reference/API_REFERENCE.md) - Module and function documentation
- [Database Schema](docs/diagrams/database-schema.md) - Table structures and relationships
- [TSPLIB95 Format](docs/reference/tsplib95_format.md) - Format specification

### Development

- [Developer Workflow](docs/development/DEVELOPER_WORKFLOW.md) - Contributing guidelines
- [Testing Summary](TESTING_SUMMARY.md) - Test documentation
- [Test Commands](TEST_COMMANDS.md) - Quick reference

## 🔧 CLI Reference

```bash
# Main commands
converter process     # Process TSPLIB files → DuckDB + JSON
converter export-parquet  # Export database → Parquet files
converter validate    # Validate database integrity
converter analyze     # Generate statistics and analysis
converter init        # Create configuration template

# Global options
-v, --verbose        # Enable debug logging
--version            # Show version

# Process options
-i, --input PATH     # Input directory (required)
-o, --output PATH    # Output directory (default: ./datasets)
--parallel/--no-parallel  # Enable parallel processing (default: enabled)
--workers N          # Number of workers (default: 4)
--batch-size N       # Batch size (default: 100)
--types TSP VRP      # Filter problem types
--force              # Reprocess all files

# Export Parquet options
-d, --database PATH  # Database file (default: ./datasets/db/routing.duckdb)
-o, --output PATH    # Output directory (default: ./datasets/parquet)
-t, --tables TABLE   # Export specific tables (repeatable)
-c, --compression CODEC  # snappy | gzip | zstd | uncompressed
--info/--no-info     # Show file information after export
```

## 📖 Example Usage

### Python API

```python
from converter.api import TSPLIBConverter

# Initialize converter
converter = TSPLIBConverter(
    db_path="datasets/db/routing.duckdb",
    json_path="datasets/json"
)

# Process files
stats = converter.process_files(
    input_dir="datasets_raw/problems",
    parallel=True,
    workers=8
)

print(f"Processed {stats['successful']} files in {stats['time']:.2f}s")

# Export to Parquet
from converter.output.parquet_writer import export_database_to_parquet

files = export_database_to_parquet(
    db_path="datasets/db/routing.duckdb",
    output_dir="datasets/parquet",
    compression="snappy"
)
```

### Advanced Database Queries

```sql
-- Find all TSP problems with 100-200 nodes
SELECT name, dimension, edge_weight_type
FROM problems
WHERE type = 'TSP' AND dimension BETWEEN 100 AND 200
ORDER BY dimension;

-- Get problem with all nodes
SELECT p.name, p.dimension, 
       n.node_id, n.x, n.y, n.demand
FROM problems p
JOIN nodes n ON p.id = n.problem_id
WHERE p.name = 'berlin52'
ORDER BY n.node_id;

-- Retrieve EXPLICIT distance matrix
SELECT p.name, p.dimension, 
       e.matrix_json, e.is_symmetric
FROM problems p
JOIN edge_weight_matrices e ON p.id = e.problem_id
WHERE p.name = 'br17' AND p.type = 'ATSP';

-- Aggregate statistics by problem type
SELECT type, 
       COUNT(*) as count,
       AVG(dimension) as avg_dim,
       MAX(dimension) as max_dim
FROM problems
GROUP BY type
ORDER BY count DESC;
```

## 🤝 Contributing

Contributions welcome! See [Developer Workflow](docs/development/DEVELOPER_WORKFLOW.md) for guidelines.

**Key conventions**:

- TSPLIB95 uses 1-based indexing; we convert to 0-based
- Use specific exception types (`TransformError`, not `Exception`)
- Inject loggers via `__init__`, never create in methods
- Test with `:memory:` database for speed

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- **TSPLIB95** - Format specification by Gerhard Reinelt (Heidelberg University)
- **DuckDB** - Embedded analytics database
- **tsplib95** library - Initial parsing implementation reference

---

**Status**: Production-ready. 134/134 tests passing. Optimized for performance (27x speedup).
