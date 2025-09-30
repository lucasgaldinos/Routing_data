# Command Reference

## Overview

Complete reference for all CLI commands in the TSPLIB95 ETL Converter.

## Global Options

These options work with all commands:

- `--help`: Show command help
- `--version`: Show version information

## Commands

### parse

Parse a TSPLIB file and store it in the database.

#### Syntax

```bash
python -m src.converter.cli.commands parse <file_path> [OPTIONS]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `file_path` | Yes | Path to TSPLIB file to parse |

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | Path | None | Custom configuration file |
| `--output-db` | `-o` | Path | config.yaml value | Override output database path |

#### Examples

**Basic usage:**
```bash
python -m src.converter.cli.commands parse datasets_raw/problems/tsp/gr17.tsp
```

**With custom database:**
```bash
python -m src.converter.cli.commands parse datasets_raw/problems/tsp/gr17.tsp -o ./custom.duckdb
```

**With custom config:**
```bash
python -m src.converter.cli.commands parse datasets_raw/problems/vrp/eil22.vrp -c my_config.yaml
```

#### Output

Success:
```
2025-09-30 12:00:00,000 - converter - INFO - Database schema initialized
Parsing datasets_raw/problems/tsp/gr17.tsp...
2025-09-30 12:00:00,010 - converter - INFO - Successfully parsed datasets_raw/problems/tsp/gr17.tsp: TSP with 17 nodes, 153 edges
2025-09-30 12:00:00,050 - converter - INFO - Successfully inserted problem ID 1 with 17 nodes, 153 edges
✓ Successfully processed datasets_raw/problems/tsp/gr17.tsp
  Problem: gr17 (TSP)
  Dimension: 17
  Nodes: 17
  Edges: 153
  Database ID: 1
  Database: ./datasets/db/routing.duckdb
```

Error:
```
2025-09-30 12:00:00,000 - converter - ERROR - Failed to process file.tsp: File validation failed: File does not exist: file.tsp
✗ Error processing file.tsp: Error processing file.tsp: File validation failed: File does not exist: file.tsp
```

#### Return Codes

- `0`: Success
- `1`: Error (file not found, parsing failed, database error, etc.)

#### Behavior

1. Validates file exists and is readable
2. Parses TSPLIB format using tsplib95 library
3. Extracts problem metadata, nodes, and edges
4. Stores data in database within a transaction
5. Reports results with statistics

**Note on Re-parsing**: If a problem with the same name already exists, it will be updated (UPSERT behavior). Existing nodes and edges are deleted and replaced.

---

### stats

Display statistics about the database contents.

#### Syntax

```bash
python -m src.converter.cli.commands stats [OPTIONS]
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | Path | None | Custom configuration file |

#### Examples

**Basic usage:**
```bash
python -m src.converter.cli.commands stats
```

**With custom config:**
```bash
python -m src.converter.cli.commands stats -c my_config.yaml
```

#### Output

```
2025-09-30 12:00:00,000 - converter - INFO - Database schema initialized
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

#### Return Codes

- `0`: Success
- `1`: Database error

#### What It Shows

- **Total Problems**: Count of unique problems in database
- **Total Nodes**: Sum of all nodes across all problems
- **Total Edges**: Sum of all edges across all problems
- **By Type**: Breakdown by problem type with:
  - Count of problems of that type
  - Average dimension (number of nodes)

---

### validate

Validate database integrity and check for data consistency issues.

#### Syntax

```bash
python -m src.converter.cli.commands validate [OPTIONS]
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | Path | None | Custom configuration file |

#### Examples

**Basic usage:**
```bash
python -m src.converter.cli.commands validate
```

**With custom config:**
```bash
python -m src.converter.cli.commands validate -c my_config.yaml
```

#### Output

Success:
```
2025-09-30 12:00:00,000 - converter - INFO - Database schema initialized
✓ Database integrity validation passed
```

Error (if issues found):
```
2025-09-30 12:00:00,000 - converter - INFO - Database schema initialized
✗ Database integrity issues found:
  - Problem 'xyz' has dimension > 0 but no nodes
  - Problem 'abc' dimension 50 != node count 48
```

#### Return Codes

- `0`: All validations passed
- `1`: Validation errors found or database error

#### Validation Checks

1. **Problems without nodes**: Checks if any problems with dimension > 0 have no nodes
2. **Dimension mismatches**: Verifies node count matches declared dimension
3. **Orphaned edges**: Checks if edges reference valid problems (via foreign keys)

#### When to Run

- After parsing multiple files
- Before running analysis queries
- After database maintenance
- Periodically to ensure data quality

---

### init

Create a configuration file with default settings.

#### Syntax

```bash
python -m src.converter.cli.commands init [OPTIONS]
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | Path | `config.yaml` | Output configuration file path |

#### Examples

**Basic usage:**
```bash
python -m src.converter.cli.commands init
```

**Custom output path:**
```bash
python -m src.converter.cli.commands init -o custom_config.yaml
```

#### Output

```
Configuration file created: config.yaml
```

#### Generated File

Creates a YAML file with these default settings:

```yaml
batch_size: 100
database_path: ./datasets/db/routing.duckdb
file_patterns:
- '*.tsp'
- '*.vrp'
- '*.atsp'
- '*.hcp'
- '*.sop'
- '*.tour'
input_path: ./datasets_raw/problems
log_file: ./logs/converter.log
log_level: INFO
```

#### Return Codes

- `0`: Success
- `1`: Error writing file

#### When to Use

- Setting up a new project
- Creating environment-specific configs
- Resetting to default configuration

---

## Usage Patterns

### Single File Processing

```bash
# Parse one file
python -m src.converter.cli.commands parse datasets_raw/problems/tsp/berlin52.tsp

# Check what was added
python -m src.converter.cli.commands stats

# Validate
python -m src.converter.cli.commands validate
```

### Batch Processing (Manual)

```bash
# Parse multiple files
for file in datasets_raw/problems/tsp/*.tsp; do
    python -m src.converter.cli.commands parse "$file"
done

# View results
python -m src.converter.cli.commands stats
```

### Different Environments

```bash
# Development environment
python -m src.converter.cli.commands init -o dev_config.yaml
# Edit dev_config.yaml to use dev database
python -m src.converter.cli.commands parse file.tsp -c dev_config.yaml

# Production environment
python -m src.converter.cli.commands init -o prod_config.yaml
# Edit prod_config.yaml to use prod database
python -m src.converter.cli.commands parse file.tsp -c prod_config.yaml
```

### Debugging

```bash
# Enable debug logging
# Edit config.yaml: log_level: DEBUG

# Parse with verbose output
python -m src.converter.cli.commands parse file.tsp

# Check logs
tail -f logs/converter.log
```

## Exit Codes Summary

| Code | Meaning | Commands |
|------|---------|----------|
| 0 | Success | All commands |
| 1 | Error occurred | All commands |

## Error Messages

### Common Errors

**File Not Found**
```
✗ Error processing file.tsp: Error processing file.tsp: File validation failed: File does not exist: file.tsp
```
**Solution**: Check file path is correct

**File Too Large**
```
✗ Error processing huge.tsp: File validation failed: File too large (>100MB): huge.tsp
```
**Solution**: File exceeds 100MB limit

**Database Locked**
```
✗ Error processing file.tsp: Schema initialization failed: IO Error: Could not set lock on file
```
**Solution**: Close other connections to database, wait and retry

**Invalid TSPLIB Format**
```
✗ Error processing file.tsp: Error processing file.tsp: Parser Error: Invalid TSPLIB format
```
**Solution**: Verify file is valid TSPLIB format

## Environment Variables

While not directly supported, you can use environment variables in shell scripts:

```bash
# Set database path
export DB_PATH="./my_database.duckdb"

# Use in command
python -m src.converter.cli.commands parse file.tsp -o "$DB_PATH"
```

## Performance Tips

### Large Files

For files with many nodes/edges:
- Expected time: ~1 second per 1000 edges
- Monitor with DEBUG logging
- Ensure sufficient disk space

### Batch Processing

When parsing many files:
- Parse in order of increasing size
- Validate after each batch
- Monitor log file for errors
- Consider using transaction batching (future feature)

### Database Optimization

- Keep database on SSD for better performance
- Run validate periodically to ensure indexes are used
- Compact database periodically (DuckDB handles this automatically)

## See Also

- [User Guide](03-user-guide.md) - General usage and workflows
- [Examples](04-examples.md) - Real-world examples
- [Database Schema](05-database-schema.md) - Database structure and queries
