# User Guide - TSPLIB95 ETL Converter

## Introduction

The TSPLIB95 ETL Converter is a command-line tool for parsing TSPLIB problem files and storing them in a DuckDB database for analysis and querying.

### What It Does

- **Parses** TSPLIB format files (TSP, VRP, ATSP, HCP, SOP, etc.)
- **Extracts** problem metadata, nodes, and edges
- **Stores** data in a structured DuckDB database
- **Validates** data integrity
- **Provides** statistics and analysis tools

### Supported Problem Types

| Type | Description | Features Supported |
|------|-------------|-------------------|
| TSP | Traveling Salesman Problem | Coordinates, edge weights |
| ATSP | Asymmetric TSP | Asymmetric weights |
| VRP/CVRP | Vehicle Routing Problem | Depots, demands, capacity |
| HCP | Hamiltonian Cycle Problem | Edge lists |
| SOP | Sequential Ordering Problem | Precedence constraints |

## Quick Start

### Basic Workflow

1. **Parse a file** to load it into the database
2. **View statistics** to see what's been loaded
3. **Validate** data integrity
4. **Query** the database for analysis

### Example Session

```bash
# Parse a TSP file
python -m src.converter.cli.commands parse datasets_raw/problems/tsp/berlin52.tsp

# View database statistics
python -m src.converter.cli.commands stats

# Validate the data
python -m src.converter.cli.commands validate
```

## Core Concepts

### Data Model

The converter stores data in three main tables:

**1. Problems Table**
- Stores problem metadata (name, type, dimension, etc.)
- One row per problem file
- Includes edge weight type and format information

**2. Nodes Table**
- Stores individual nodes/cities/locations
- Includes coordinates (if available)
- Includes VRP-specific data (demands, depot flags)
- Linked to problems via `problem_id`

**3. Edges Table**
- Stores pairwise distances/weights
- Uses 0-based indexing for consistency
- Linked to problems via `problem_id`

### Problem Type Handling

#### Coordinate-Based Problems (EUC_2D)

Files with node coordinates (x, y):
- Example: `berlin52.tsp`, `eil22.vrp`
- Edges computed using Euclidean distance
- All nodes have `x` and `y` values in database

#### Weight-Based Problems (EXPLICIT)

Files with pre-computed weight matrices:
- Example: `gr17.tsp`, `ft70.atsp`
- Edges extracted from matrix sections
- Nodes have NULL coordinates in database

#### Special Formats

- **HCP (EDGE_LIST)**: Edges stored as adjacency lists
- **SOP**: Includes precedence constraints (negative weights)

## Using the CLI

### General Command Structure

```bash
python -m src.converter.cli.commands <command> [OPTIONS] [ARGUMENTS]
```

### Available Commands

#### 1. parse - Load a Problem File

**Usage**:
```bash
python -m src.converter.cli.commands parse <file_path> [OPTIONS]
```

**Arguments**:
- `file_path`: Path to TSPLIB file (required)

**Options**:
- `--config`, `-c`: Custom configuration file path
- `--output-db`, `-o`: Override database path

**Examples**:
```bash
# Parse a TSP file
python -m src.converter.cli.commands parse datasets_raw/problems/tsp/gr17.tsp

# Parse with custom database
python -m src.converter.cli.commands parse datasets_raw/problems/vrp/eil22.vrp -o ./my_data.duckdb

# Parse with custom config
python -m src.converter.cli.commands parse datasets_raw/problems/atsp/ft70.atsp -c my_config.yaml
```

**Output**:
```
✓ Successfully processed datasets_raw/problems/tsp/gr17.tsp
  Problem: gr17 (TSP)
  Dimension: 17
  Nodes: 17
  Edges: 153
  Database ID: 1
  Database: ./datasets/db/routing.duckdb
```

#### 2. stats - View Database Statistics

**Usage**:
```bash
python -m src.converter.cli.commands stats [OPTIONS]
```

**Options**:
- `--config`, `-c`: Custom configuration file path

**Example**:
```bash
python -m src.converter.cli.commands stats
```

**Output**:
```
Database Statistics:
  Total Problems: 6
  Total Nodes: 1478
  Total Edges: 48787

By Problem Type:
  TSP: 2 problems (avg dimension: 166.0)
  ATSP: 1 problems (avg dimension: 70.0)
  CVRP: 1 problems (avg dimension: 22.0)
  HCP: 1 problems (avg dimension: 1000.0)
  SOP: 1 problems (avg dimension: 54.0)
```

#### 3. validate - Check Data Integrity

**Usage**:
```bash
python -m src.converter.cli.commands validate [OPTIONS]
```

**Options**:
- `--config`, `-c`: Custom configuration file path

**Example**:
```bash
python -m src.converter.cli.commands validate
```

**Success Output**:
```
✓ Database integrity validation passed
```

**Error Output** (if issues found):
```
✗ Database integrity issues found:
  - Problem 'xyz' has dimension 50 but no nodes
  - Problem 'abc' dimension 30 != node count 28
```

#### 4. init - Create Configuration File

**Usage**:
```bash
python -m src.converter.cli.commands init [OPTIONS]
```

**Options**:
- `--output`, `-o`: Output file path (default: `config.yaml`)

**Example**:
```bash
python -m src.converter.cli.commands init -o my_config.yaml
```

**Output**:
```
Configuration file created: my_config.yaml
```

## Configuration

### Configuration File Format

The `config.yaml` file controls converter behavior:

```yaml
# Input settings
input_path: ./datasets_raw/problems
file_patterns:
  - '*.tsp'
  - '*.vrp'
  - '*.atsp'
  - '*.hcp'
  - '*.sop'
  - '*.tour'

# Output settings
database_path: ./datasets/db/routing.duckdb

# Processing settings
batch_size: 100

# Logging
log_level: INFO
log_file: ./logs/converter.log
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `input_path` | string | `./datasets_raw/problems` | Directory containing TSPLIB files |
| `file_patterns` | list | `['*.tsp', '*.vrp', ...]` | File patterns to match |
| `database_path` | string | `./datasets/db/routing.duckdb` | Database file location |
| `batch_size` | integer | `100` | Batch size for future processing |
| `log_level` | string | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `log_file` | string | `./logs/converter.log` | Log file location |

### Customizing Configuration

```bash
# Create custom config
python -m src.converter.cli.commands init -o custom_config.yaml

# Edit the file
nano custom_config.yaml

# Use custom config
python -m src.converter.cli.commands parse file.tsp -c custom_config.yaml
```

## Database Querying

### Using DuckDB CLI

```bash
# Open database
duckdb datasets/db/routing.duckdb

# List tables
.tables

# Query examples in next section
```

### Common Queries

#### Get All Problems

```sql
SELECT id, name, type, dimension, edge_weight_type
FROM problems
ORDER BY dimension DESC;
```

#### Find Coordinate-Based Problems

```sql
SELECT p.name, p.type, COUNT(n.id) as nodes_with_coords
FROM problems p
JOIN nodes n ON p.id = n.problem_id
WHERE n.x IS NOT NULL
GROUP BY p.id, p.name, p.type;
```

#### Get Problem with Nodes and Edges

```sql
-- Problem details
SELECT * FROM problems WHERE name = 'berlin52';

-- Nodes for the problem
SELECT node_id, x, y, demand, is_depot
FROM nodes
WHERE problem_id = (SELECT id FROM problems WHERE name = 'berlin52')
ORDER BY node_id;

-- Edge statistics
SELECT 
    COUNT(*) as total_edges,
    MIN(weight) as min_weight,
    AVG(weight) as avg_weight,
    MAX(weight) as max_weight
FROM edges
WHERE problem_id = (SELECT id FROM problems WHERE name = 'berlin52');
```

#### Find VRP Problems with Depots

```sql
SELECT 
    p.name,
    p.capacity,
    COUNT(CASE WHEN n.is_depot THEN 1 END) as depot_count,
    SUM(n.demand) as total_demand
FROM problems p
JOIN nodes n ON p.id = n.problem_id
WHERE p.type IN ('VRP', 'CVRP')
GROUP BY p.id, p.name, p.capacity;
```

#### Analyze Edge Weight Distribution

```sql
SELECT 
    p.name,
    CASE 
        WHEN e.weight < 100 THEN '0-100'
        WHEN e.weight < 500 THEN '100-500'
        WHEN e.weight < 1000 THEN '500-1000'
        ELSE '1000+'
    END as weight_range,
    COUNT(*) as count
FROM problems p
JOIN edges e ON p.id = e.problem_id
WHERE p.name = 'ft70'
GROUP BY p.id, p.name, weight_range
ORDER BY weight_range;
```

### Python Querying

```python
import duckdb

# Connect to database
conn = duckdb.connect('datasets/db/routing.duckdb')

# Query problems
problems = conn.execute("SELECT * FROM problems").fetchall()
for p in problems:
    print(f"Problem: {p[1]} ({p[2]}), Dimension: {p[4]}")

# Query with pandas (if installed)
import pandas as pd
df = conn.execute("SELECT * FROM problems").df()
print(df.head())

conn.close()
```

## Workflows

### Workflow 1: Analyze a Single Problem

```bash
# 1. Parse the file
python -m src.converter.cli.commands parse datasets_raw/problems/tsp/berlin52.tsp

# 2. Query the database
duckdb datasets/db/routing.duckdb << EOF
SELECT p.name, p.dimension, COUNT(n.id) as nodes, COUNT(e.id) as edges
FROM problems p
LEFT JOIN nodes n ON p.id = n.problem_id
LEFT JOIN edges e ON p.id = e.problem_id
WHERE p.name = 'berlin52'
GROUP BY p.id, p.name, p.dimension;
EOF

# 3. Validate
python -m src.converter.cli.commands validate
```

### Workflow 2: Compare Multiple Problems

```bash
# Parse multiple files
for file in datasets_raw/problems/tsp/*.tsp; do
    python -m src.converter.cli.commands parse "$file"
done

# View statistics
python -m src.converter.cli.commands stats

# Compare in database
duckdb datasets/db/routing.duckdb << EOF
SELECT 
    type,
    COUNT(*) as count,
    AVG(dimension) as avg_dimension,
    MIN(dimension) as min_dimension,
    MAX(dimension) as max_dimension
FROM problems
GROUP BY type
ORDER BY avg_dimension DESC;
EOF
```

### Workflow 3: Find Specific Problem Characteristics

```bash
# Find problems with coordinates
duckdb datasets/db/routing.duckdb << EOF
SELECT p.name, p.type, p.edge_weight_type
FROM problems p
WHERE p.edge_weight_type = 'EUC_2D'
ORDER BY p.dimension;
EOF

# Find large problems
duckdb datasets/db/routing.duckdb << EOF
SELECT name, type, dimension
FROM problems
WHERE dimension > 100
ORDER BY dimension DESC;
EOF
```

## Troubleshooting

### Problem: File Won't Parse

**Symptoms**: Error message when parsing

**Solutions**:
1. Check file format is valid TSPLIB
2. Verify file is not corrupted
3. Check file size (must be < 100MB)
4. Enable DEBUG logging to see details:
   ```bash
   # Edit config.yaml
   log_level: DEBUG
   ```

### Problem: Database Locked

**Symptoms**: "Could not set lock on file" error

**Solutions**:
1. Close any DuckDB connections
2. Wait a few seconds and retry
3. Check for stale Python processes:
   ```bash
   pkill -f python
   ```

### Problem: Missing Dependencies

**Symptoms**: "ModuleNotFoundError"

**Solution**:
```bash
pip install -e .
```

### Problem: Integrity Validation Fails

**Symptoms**: Dimension mismatches or missing nodes

**Solution**:
1. Check the log file for details
2. Re-parse the problematic file
3. If issue persists, file may have errors

## Best Practices

### 1. Start Small

Parse a few small files first to understand the data:
```bash
python -m src.converter.cli.commands parse datasets_raw/problems/tsp/gr17.tsp
```

### 2. Validate Regularly

Run validation after parsing multiple files:
```bash
python -m src.converter.cli.commands validate
```

### 3. Use Consistent Paths

Keep all data in the configured directories:
- Input: `datasets_raw/problems/`
- Database: `datasets/db/`
- Logs: `logs/`

### 4. Monitor Logs

Check logs for warnings and errors:
```bash
tail -f logs/converter.log
```

### 5. Backup Database

Before major operations, backup your database:
```bash
cp datasets/db/routing.duckdb datasets/db/routing_backup.duckdb
```

## Next Steps

- See [Command Reference](03-command-reference.md) for detailed command documentation
- Check [Examples](04-examples.md) for real-world usage scenarios
- Review [Database Schema](05-database-schema.md) for query optimization
- Read [Development Journey](01-development-journey.md) for architecture insights
