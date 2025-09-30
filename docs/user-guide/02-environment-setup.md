# Environment Setup Guide

## Overview

This guide walks through setting up the development environment for the TSPLIB95 ETL Converter from scratch.

## Prerequisites

### Required Software

- **Python 3.11 or higher** (tested with Python 3.12)
- **Git** for version control
- **pip** or **uv** for package management

### System Requirements

- **OS**: Linux, macOS, or Windows (with WSL recommended)
- **Memory**: 2GB minimum (4GB recommended for large datasets)
- **Disk Space**: 500MB for dependencies and datasets

## Step-by-Step Setup

### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/lucasgaldinos/Routing_data.git
cd Routing_data
```

### 2. Verify Python Version

```bash
# Check Python version (must be 3.11+)
python --version
# or
python3 --version

# Expected output: Python 3.11.x or higher
```

If your Python version is lower than 3.11:
- **Ubuntu/Debian**: `sudo apt install python3.11`
- **macOS**: `brew install python@3.11`
- **Windows**: Download from [python.org](https://www.python.org/downloads/)

### 3. Install Dependencies

#### Option A: Using pip (recommended for most users)

```bash
# Install the package in editable mode with all dependencies
python -m pip install -e .

# Verify installation
python -c "import tsplib95, duckdb, click, yaml; print('All dependencies installed!')"
```

#### Option B: Using uv (faster, if available)

```bash
# Install uv (if not already installed)
pip install uv

# Install dependencies
uv add duckdb networkx click tabulate deprecated pytest pyyaml

# Install package in editable mode
uv pip install -e .
```

### 4. Verify Installation

```bash
# Run existing tests to ensure everything works
python -m pytest -q

# Expected output: All tests passing (366 tests)
```

### 5. Set Up Database Directory

```bash
# Create directory for database files
mkdir -p datasets/db

# Create directory for logs
mkdir -p logs
```

### 6. Verify Converter Installation

```bash
# Test the converter CLI
python -m src.converter.cli.commands --version

# Expected output: Version 0.1.0

# Show available commands
python -m src.converter.cli.commands --help
```

## Environment Configuration

### Configuration File

Create a `config.yaml` file in the project root (or use the existing one):

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

Generate default config with:
```bash
python -m src.converter.cli.commands init
```

### Environment Variables (Optional)

For advanced users, you can set environment variables:

```bash
# Set custom database path
export CONVERTER_DB_PATH="./my_custom_path/routing.duckdb"

# Set log level
export CONVERTER_LOG_LEVEL="DEBUG"
```

## Verification Steps

### 1. Test Parsing

```bash
# Parse a sample file
python -m src.converter.cli.commands parse datasets_raw/problems/tsp/gr17.tsp

# Expected output:
# ✓ Successfully processed datasets_raw/problems/tsp/gr17.tsp
#   Problem: gr17 (TSP)
#   Dimension: 17
#   Nodes: 17
#   Edges: 153
```

### 2. Check Database

```bash
# View database statistics
python -m src.converter.cli.commands stats

# Expected output:
# Database Statistics:
#   Total Problems: 1
#   Total Nodes: 17
#   Total Edges: 153
```

### 3. Validate Data Integrity

```bash
# Run integrity checks
python -m src.converter.cli.commands validate

# Expected output:
# ✓ Database integrity validation passed
```

## Troubleshooting

### Common Issues

#### Issue 1: Module Not Found Error

**Error**: `ModuleNotFoundError: No module named 'tsplib95'`

**Solution**:
```bash
# Reinstall the package
python -m pip install -e .
```

#### Issue 2: DuckDB Lock Error

**Error**: `IO Error: Could not set lock on file`

**Solution**: Close any open database connections
```bash
# Kill any Python processes holding the lock
pkill -f python
# Or restart your terminal
```

#### Issue 3: Permission Denied

**Error**: `Permission denied: './datasets/db/'`

**Solution**:
```bash
# Ensure directories exist and are writable
mkdir -p datasets/db logs
chmod 755 datasets/db logs
```

#### Issue 4: YAML Module Not Found

**Error**: `ModuleNotFoundError: No module named 'yaml'`

**Solution**:
```bash
# Install PyYAML explicitly
pip install pyyaml
```

### Getting Help

If you encounter issues not covered here:

1. **Check logs**: `tail -f logs/converter.log`
2. **Run tests with verbose output**: `pytest -v`
3. **Verify Python packages**: `pip list | grep -E "duckdb|click|yaml"`
4. **Check Python path**: `python -c "import sys; print('\n'.join(sys.path))"`

## Development Environment Setup

For contributors who want to modify the code:

### 1. Install Development Dependencies

```bash
# Install with development extras
pip install -e ".[dev]"

# Or install testing tools separately
pip install pytest pytest-cov black flake8 mypy
```

### 2. Set Up Git Hooks (Optional)

```bash
# Create pre-commit hook to run tests
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
python -m pytest -q
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
EOF

chmod +x .git/hooks/pre-commit
```

### 3. Configure IDE

#### VS Code

Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"]
}
```

#### PyCharm

1. File → Settings → Project → Python Interpreter
2. Add interpreter → Existing environment
3. Select Python from your venv

### 4. Verify Development Setup

```bash
# Run all tests with coverage
pytest --cov=src/converter tests/

# Check code style
black --check src/
flake8 src/

# Type checking
mypy src/converter/
```

## Docker Setup (Alternative)

For isolated environment:

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -e .

CMD ["python", "-m", "src.converter.cli.commands", "--help"]
```

Build and run:
```bash
docker build -t tsplib-converter .
docker run -v $(pwd)/datasets:/app/datasets tsplib-converter parse datasets_raw/problems/tsp/gr17.tsp
```

## Next Steps

Once your environment is set up:

1. Read the [User Guide](02-user-guide.md) to learn how to use the converter
2. Review [Command Reference](03-command-reference.md) for all available commands
3. Check [Examples](04-examples.md) for common usage patterns
4. See [Development Journey](01-development-journey.md) for architecture insights

## Environment Checklist

Use this checklist to ensure your environment is ready:

- [ ] Python 3.11+ installed and verified
- [ ] Repository cloned
- [ ] Dependencies installed (`pip install -e .`)
- [ ] Tests pass (`pytest -q`)
- [ ] Database directory created (`datasets/db/`)
- [ ] CLI accessible (`python -m src.converter.cli.commands --help`)
- [ ] Sample file parsed successfully
- [ ] Database statistics displayed
- [ ] Integrity validation passed

Once all items are checked, your environment is ready!
