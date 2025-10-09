# TSPLIB95 ETL System - User Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Basic Usage](#basic-usage)
4. [Advanced Usage](#advanced-usage)
5. [CLI Reference](#cli-reference)
6. [Python API](#python-api)
7. [Database Queries](#database-queries)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

Get started in 3 simple steps:

```bash
# 1. Install the package
pip install -e .

# 2. Initialize configuration
python -m converter.cli.commands init

# 3. Process TSPLIB files
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --parallel
```

That's it! You now have:

- A DuckDB database at `datasets/db/routing.duckdb`
- JSON files organized by type in `datasets/json/`
- File tracking for incremental updates

---

## Installation

### Prerequisites

- Python ≥ 3.11
- 2GB+ RAM (for processing large files)
- 1GB+ disk space (for database and JSON output)

### Install from Source

```bash
# Clone repository
git clone https://github.com/lucasgaldinos/Routing_data.git
cd Routing_data

# Install with dependencies
pip install -e .

# Verify installation
python -c "from converter.cli.commands import cli; print('✓ Installation successful')"
```

### Install Development Dependencies

For testing and development:

```bash
pip install -e ".[dev]"
```

---

## Basic Usage

### 1. Initialize Configuration

Create a configuration file with default settings:

```bash
python -m converter.cli.commands init --output config.yaml
```

This creates `config.yaml`:

```yaml
input_path: ./datasets_raw/problems
file_patterns:
- '*.tsp'
- '*.vrp'
- '*.atsp'
- '*.hcp'
- '*.sop'
- '*.tour'
json_output_path: ./datasets/json
database_path: ./datasets/db/routing.duckdb
batch_size: 100
max_workers: 4
memory_limit_mb: 2048
log_level: INFO
log_file: ./logs/converter.log
```

**Customize settings:**

```bash
# Edit config.yaml
nano config.yaml

# Modify settings as needed:
# - max_workers: 8  (for faster processing on powerful machines)
# - log_level: DEBUG  (for troubleshooting)
# - batch_size: 50  (for lower memory usage)
```

### 2. Process TSPLIB Files

#### Process All Files

```bash
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/
```

**What happens:**

1. Scans `datasets_raw/problems` recursively
2. Finds all TSPLIB files (*.tsp,*.vrp, etc.)
3. Parses each file to extract metadata, nodes, edges
4. Stores in DuckDB at `datasets/db/routing.duckdb`
5. Writes JSON to `datasets/json/{tsp,vrp,atsp}/`
6. Tracks files with SHA256 checksums

#### Process Specific Types

```bash
# Only TSP files
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --types tsp

# Multiple types
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --types tsp --types vrp
```

#### Parallel Processing

```bash
# Use 4 workers (default)
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --parallel

# Use 8 workers (for faster processing)
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --parallel \
  --workers 8
```

#### Sequential Processing

For debugging or low-memory systems:

```bash
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --no-parallel
```

### 3. Validate Database

Check database integrity:

```bash
python -m converter.cli.commands validate \
  --database datasets/db/routing.duckdb
```

**Output:**

```
✓ Database connection successful
✓ All required tables exist
✓ All sequences exist
✓ Foreign key constraints valid
✓ Database validation passed
```

### 4. Analyze Data

#### View Statistics (Table Format)

```bash
python -m converter.cli.commands analyze \
  --database datasets/db/routing.duckdb \
  --format table
```

**Output:**

```
Problem Statistics:
┌──────┬────────┬───────────┬───────────┐
│ Type │ Count  │ Avg Dim   │ Max Dim   │
├──────┼────────┼───────────┼───────────┤
│ TSP  │ 113    │ 1204.5    │ 13509     │
│ VRP  │ 45     │ 342.8     │ 1001      │
│ ATSP │ 28     │ 156.3     │ 443       │
└──────┴────────┴───────────┴───────────┘
```

#### View Statistics (JSON Format)

```bash
python -m converter.cli.commands analyze \
  --database datasets/db/routing.duckdb \
  --format json > stats.json
```

#### Filter by Type

```bash
python -m converter.cli.commands analyze \
  --database datasets/db/routing.duckdb \
  --type TSP \
  --limit 20
```

---

## Advanced Usage

### Incremental Updates

The system automatically detects changed files:

```bash
# First run: processes all files
python -m converter.cli.commands process -i datasets_raw/problems -o datasets/

# Modify a file
echo "COMMENT : Updated" >> datasets_raw/problems/tsp/gr17.tsp

# Second run: only processes changed file
python -m converter.cli.commands process -i datasets_raw/problems -o datasets/
```

**Output:**

```
INFO - Checking for changed files...
INFO - Processing modified file: datasets_raw/problems/tsp/gr17.tsp
INFO - Skipping 112 unchanged files
```

### Force Reprocessing

Skip change detection and process all files:

```bash
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --force
```

### Custom Batch Size

Adjust memory usage:

```bash
# Lower batch size for limited memory
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --batch-size 50

# Higher batch size for better performance
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --batch-size 200
```

### Custom Worker Count

```bash
# Single worker (sequential)
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --workers 1

# Maximum parallelization (for powerful systems)
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --workers 16
```

### Using Configuration File

```bash
# Create custom config
cat > my_config.yaml << EOF
input_path: ./my_data
json_output_path: ./output/json
database_path: ./output/db/data.duckdb
max_workers: 8
log_level: DEBUG
EOF

# Use custom config
python -m converter.cli.commands process --config my_config.yaml
```

---

## CLI Reference

### `init` Command

Generate a configuration file.

```bash
python -m converter.cli.commands init [OPTIONS]
```

**Options:**

- `--output, -o PATH` - Output path for config file (default: config.yaml)

**Example:**

```bash
python -m converter.cli.commands init -o my_config.yaml
```

### `process` Command

Run the ETL pipeline.

```bash
python -m converter.cli.commands process [OPTIONS]
```

**Options:**

- `--input, -i PATH` - Input directory containing TSPLIB files
- `--output, -o PATH` - Output directory for JSON and database
- `--config, -c PATH` - Configuration file path
- `--parallel / --no-parallel` - Enable/disable parallel processing (default: enabled)
- `--batch-size INT` - Batch size for processing (default: 100)
- `--workers INT` - Number of parallel workers (default: 4)
- `--types TEXT` - Problem types to process (can be specified multiple times)
- `--force / --no-force` - Force reprocessing of existing files (default: disabled)

**Examples:**

```bash
# Basic usage
python -m converter.cli.commands process -i data/ -o output/

# With configuration
python -m converter.cli.commands process --config config.yaml

# Parallel with 8 workers
python -m converter.cli.commands process -i data/ -o output/ --workers 8

# Only TSP and VRP files
python -m converter.cli.commands process -i data/ -o output/ --types tsp --types vrp

# Force reprocessing
python -m converter.cli.commands process -i data/ -o output/ --force
```

### `validate` Command

Validate database integrity.

```bash
python -m converter.cli.commands validate [OPTIONS]
```

**Options:**

- `--database PATH` - Path to DuckDB database file
- `--config PATH` - Configuration file path

**Examples:**

```bash
# Validate specific database
python -m converter.cli.commands validate --database datasets/db/routing.duckdb

# Use config file
python -m converter.cli.commands validate --config config.yaml
```

### `analyze` Command

Generate statistics and analyze data.

```bash
python -m converter.cli.commands analyze [OPTIONS]
```

**Options:**

- `--database PATH` - Path to DuckDB database file
- `--config PATH` - Configuration file path
- `--format [table|json]` - Output format (default: table)
- `--type TEXT` - Filter by problem type
- `--limit INT` - Limit number of results (default: 100)

**Examples:**

```bash
# Table format
python -m converter.cli.commands analyze --database datasets/db/routing.duckdb

# JSON format
python -m converter.cli.commands analyze \
  --database datasets/db/routing.duckdb \
  --format json

# Filter by type
python -m converter.cli.commands analyze \
  --database datasets/db/routing.duckdb \
  --type TSP \
  --limit 50

# Save to file
python -m converter.cli.commands analyze \
  --database datasets/db/routing.duckdb \
  --format json > analysis.json
```

---

## Python API

Use the converter programmatically in your Python code.

### Basic Parsing

```python
from converter.core.parser import TSPLIBParser
from converter.utils.logging import setup_logging

# Setup
logger = setup_logging("INFO")
parser = TSPLIBParser(logger)

# Parse a file
result = parser.parse_file('datasets_raw/problems/tsp/berlin52.tsp')

# Access data
print(f"Problem: {result['problem_data']['name']}")
print(f"Dimension: {result['problem_data']['dimension']}")
print(f"Nodes: {len(result['nodes'])}")
print(f"Edges: {len(result['edges'])}")
```

### Complete Pipeline

```python
from converter.core.scanner import FileScanner
from converter.core.parser import TSPLIBParser
from converter.core.transformer import DataTransformer
from converter.database.operations import DatabaseManager
from converter.output.json_writer import JSONWriter
from converter.utils.logging import setup_logging

# Initialize components
logger = setup_logging("INFO")
scanner = FileScanner(logger=logger)
parser = TSPLIBParser(logger)
transformer = DataTransformer(logger)
db_manager = DatabaseManager("output.duckdb", logger)
json_writer = JSONWriter("output_json/", logger=logger)

# Scan for files
files = scanner.scan_files('datasets_raw/problems/tsp', patterns=['*.tsp'])
print(f"Found {len(files)} files")

# Process each file
for file_path in files[:5]:  # First 5 files
    # Parse
    problem_data = parser.parse_file(file_path)
    
    # Transform
    transformed = transformer.transform_problem(problem_data)
    
    # Store in database
    problem_id = db_manager.insert_problem(transformed['problem_data'])
    if transformed['nodes']:
        db_manager.insert_nodes(problem_id, transformed['nodes'])
    if transformed['edges']:
        db_manager.insert_edges(problem_id, transformed['edges'][:1000])
    
    # Write JSON
    json_writer.write_problem(transformed)
    
    print(f"✓ Processed {problem_data['problem_data']['name']}")
```

### Parallel Processing

```python
from converter.utils.parallel import ParallelProcessor
from converter.core.parser import TSPLIBParser
from converter.utils.logging import setup_logging

logger = setup_logging("INFO")
parser = TSPLIBParser(logger)
processor = ParallelProcessor(max_workers=4, logger=logger)

# Define processing function
def process_file(file_path):
    result = parser.parse_file(file_path)
    return result['problem_data']['name']

# Process files in parallel
files = ['file1.tsp', 'file2.tsp', 'file3.tsp']
results = processor.process_files_parallel(files, process_file)

print(f"Successful: {results['successful']}")
print(f"Failed: {results['failed']}")
print(f"Time: {results['processing_time']:.2f}s")
```

### Update Detection

```python
from converter.utils.update import UpdateManager
from converter.database.operations import DatabaseManager
from converter.utils.logging import setup_logging

logger = setup_logging("INFO")
db_manager = DatabaseManager("routing.duckdb", logger)
update_manager = UpdateManager(db_manager, logger)

# Check if file needs processing
file_path = 'datasets_raw/problems/tsp/berlin52.tsp'
change_info = update_manager.detect_changes(file_path)

if change_info['needs_update']:
    print(f"File needs update: {change_info['change_type']}")
else:
    print("File unchanged, skipping")
```

---

## Database Queries

### Connect to Database

```python
import duckdb

conn = duckdb.connect('datasets/db/routing.duckdb')
```

### Basic Queries

```python
# Count problems
result = conn.execute('SELECT COUNT(*) FROM problems').fetchone()
print(f"Total problems: {result[0]}")

# List all TSP problems
tsp_problems = conn.execute('''
    SELECT name, dimension 
    FROM problems 
    WHERE type = 'TSP' 
    ORDER BY dimension
''').fetchall()

for name, dim in tsp_problems:
    print(f"{name}: {dim} nodes")
```

### Advanced Queries

#### Find Problems by Dimension Range

```python
query = '''
    SELECT name, type, dimension, edge_weight_type
    FROM problems
    WHERE dimension BETWEEN ? AND ?
    ORDER BY dimension
'''

results = conn.execute(query, [50, 100]).fetchall()
for row in results:
    print(f"{row[0]} ({row[1]}): dimension={row[2]}, weight_type={row[3]}")
```

#### Node Density Analysis

```python
query = '''
    SELECT 
        p.name,
        p.dimension,
        COUNT(n.id) as node_count,
        ROUND(COUNT(n.id) * 100.0 / p.dimension, 2) as coverage_pct
    FROM problems p
    LEFT JOIN nodes n ON p.id = n.problem_id
    GROUP BY p.id, p.name, p.dimension
    ORDER BY coverage_pct DESC
    LIMIT 10
'''

results = conn.execute(query).fetchall()
print("Top 10 problems by node coverage:")
for name, dim, count, coverage in results:
    print(f"{name}: {count}/{dim} nodes ({coverage}% coverage)")
```

#### Edge Weight Statistics

```python
query = '''
    SELECT 
        p.name,
        COUNT(e.id) as edge_count,
        ROUND(AVG(e.weight), 2) as avg_weight,
        ROUND(MIN(e.weight), 2) as min_weight,
        ROUND(MAX(e.weight), 2) as max_weight
    FROM problems p
    JOIN edges e ON p.id = e.problem_id
    GROUP BY p.id, p.name
    ORDER BY edge_count DESC
    LIMIT 10
'''

results = conn.execute(query).fetchall()
print("Top 10 problems by edge count:")
for name, count, avg, min_w, max_w in results:
    print(f"{name}: {count} edges, avg={avg}, min={min_w}, max={max_w}")
```

#### VRP Depot Analysis

```python
query = '''
    SELECT 
        p.name,
        p.capacity,
        COUNT(DISTINCT n.id) FILTER (WHERE n.is_depot = true) as depot_count,
        COUNT(DISTINCT n.id) FILTER (WHERE n.is_depot = false) as customer_count
    FROM problems p
    JOIN nodes n ON p.id = n.problem_id
    WHERE p.type = 'VRP'
    GROUP BY p.id, p.name, p.capacity
    ORDER BY customer_count DESC
'''

results = conn.execute(query).fetchall()
print("VRP Problems:")
for name, capacity, depots, customers in results:
    print(f"{name}: capacity={capacity}, depots={depots}, customers={customers}")
```

#### Problem Type Distribution

```python
query = '''
    SELECT 
        type,
        COUNT(*) as problem_count,
        ROUND(AVG(dimension), 1) as avg_dimension,
        MAX(dimension) as max_dimension
    FROM problems
    GROUP BY type
    ORDER BY problem_count DESC
'''

results = conn.execute(query).fetchall()
print("Problem Type Distribution:")
for ptype, count, avg_dim, max_dim in results:
    print(f"{ptype}: {count} problems, avg_dim={avg_dim}, max_dim={max_dim}")
```

### Export Query Results

```python
import pandas as pd

# Query to DataFrame
df = conn.execute('''
    SELECT name, type, dimension, edge_weight_type
    FROM problems
    WHERE dimension < 100
''').df()

# Save to CSV
df.to_csv('small_problems.csv', index=False)

# Save to Excel
df.to_excel('small_problems.xlsx', index=False)
```

---

## Troubleshooting

### Common Issues

#### 1. Import Error: No module named 'converter'

**Problem:**

```
ModuleNotFoundError: No module named 'converter'
```

**Solution:**

```bash
# Install package in editable mode
pip install -e .

# Or add src to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/Routing_data/src"
```

#### 2. Database Lock Error

**Problem:**

```
IO Error: Could not set lock on file
```

**Solution:**

```bash
# Close all connections to database
# Make sure no other process is using it

# If stuck, remove lock file
rm datasets/db/routing.duckdb.wal
```

#### 3. Memory Error During Processing

**Problem:**

```
MemoryError: Unable to allocate array
```

**Solution:**

```bash
# Reduce batch size
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --batch-size 50

# Use sequential processing
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --no-parallel

# Limit edge storage (modify in operations.py)
# edges_to_insert = transformed_data['edges'][:1000]
```

#### 4. Parsing Error on Specific File

**Problem:**

```
ParsingError: Failed to parse file.tsp
```

**Solution:**

```bash
# Check file format
head -20 datasets_raw/problems/tsp/problem.tsp

# Try parsing individually with debug logging
python << EOF
from converter.core.parser import TSPLIBParser
from converter.utils.logging import setup_logging

logger = setup_logging("DEBUG")
parser = TSPLIBParser(logger)
try:
    result = parser.parse_file('problem.tsp')
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
EOF
```

#### 5. CLI Command Not Found

**Problem:**

```
python: No module named converter.cli.commands
```

**Solution:**

```bash
# Ensure package is installed
pip install -e .

# Or run from correct directory
cd /path/to/Routing_data
python -m converter.cli.commands --help
```

### Debug Mode

Enable detailed logging:

```bash
# Set log level to DEBUG
python -m converter.cli.commands process \
  -i datasets_raw/problems \
  -o datasets/ \
  --config config.yaml

# After editing config.yaml to set log_level: DEBUG
```

Or in Python:

```python
from converter.utils.logging import setup_logging

logger = setup_logging("DEBUG")
# Now all operations will show debug logs
```

### Performance Tuning

If processing is slow:

```bash
# Increase workers (for multi-core systems)
python -m converter.cli.commands process \
  --workers 8

# Increase batch size
python -m converter.cli.commands process \
  --batch-size 200

# Skip edge storage (modify code)
# Comment out: db_manager.insert_edges(...)
```

If memory usage is too high:

```bash
# Decrease workers
python -m converter.cli.commands process \
  --workers 2

# Decrease batch size
python -m converter.cli.commands process \
  --batch-size 50

# Use sequential processing
python -m converter.cli.commands process \
  --no-parallel
```

---

## Best Practices

### 1. Always Use Incremental Updates

```bash
# First run
python -m converter.cli.commands process -i data/ -o output/

# Subsequent runs (only processes changed files)
python -m converter.cli.commands process -i data/ -o output/
```

### 2. Validate After Processing

```bash
python -m converter.cli.commands process -i data/ -o output/
python -m converter.cli.commands validate --database output/db/routing.duckdb
```

### 3. Backup Database Regularly

```bash
# Create backup
cp datasets/db/routing.duckdb datasets/db/routing_backup_$(date +%Y%m%d).duckdb

# Or export to SQL
duckdb datasets/db/routing.duckdb -c "EXPORT DATABASE 'backup/';"
```

### 4. Monitor Log Files

```bash
# Tail log file during processing
tail -f logs/converter.log

# Check for errors
grep "ERROR" logs/converter.log
```

### 5. Use Configuration Files

Don't hardcode settings in commands:

```bash
# Bad
python -m converter.cli.commands process \
  -i /very/long/path/to/data \
  --workers 8 \
  --batch-size 150

# Good
python -m converter.cli.commands process --config config.yaml
```

---

## Getting Help

### Check Documentation

- Development Guide: `docs/DEVELOPMENT_GUIDE.md`
- Implementation Details: `COMPLETE_IMPLEMENTATION.md`
- Test Results: `PHASE3_TEST_RESULTS.md`

### Run Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific module
python -m pytest tests/converter/test_phase3.py -v

# Integration tests
python -m pytest tests/test_complete_pipeline.py -v
```

### Command Help

```bash
# General help
python -m converter.cli.commands --help

# Command-specific help
python -m converter.cli.commands process --help
python -m converter.cli.commands validate --help
python -m converter.cli.commands analyze --help
```

---

## Next Steps

Now that you know how to use the system:

1. **Process Your Data**: Run the pipeline on your TSPLIB files
2. **Explore the Database**: Use SQL queries to analyze problems
3. **Integrate**: Use the Python API in your own code
4. **Optimize**: Tune workers and batch size for your system
5. **Extend**: Add custom processing or analysis functions

Happy routing! 🚀
