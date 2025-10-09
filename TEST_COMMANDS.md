# Quick Test Reference

## Run All Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing

# Quick run (minimal output)
uv run pytest tests/ -q
```

## Run Specific Test Files

```bash
# Format tests
uv run pytest tests/test_format/test_format_parser.py -v
uv run pytest tests/test_format/test_extraction.py -v

# Converter tests
uv run pytest tests/test_converter/test_converter_api.py -v
uv run pytest tests/test_converter/test_transformer.py -v
uv run pytest tests/test_converter/test_json_writer.py -v
uv run pytest tests/test_converter/test_database.py -v
uv run pytest tests/test_converter/test_scanner.py -v

# Integration tests
uv run pytest tests/test_integration/test_pipeline.py -v
uv run pytest tests/test_integration/test_cli.py -v
```

## Run Specific Test Classes

```bash
# CLI tests
uv run pytest tests/test_integration/test_cli.py::TestCLIBasic -v
uv run pytest tests/test_integration/test_cli.py::TestProcessCommand -v
uv run pytest tests/test_integration/test_cli.py::TestAnalyzeCommand -v
uv run pytest tests/test_integration/test_cli.py::TestValidateCommand -v
uv run pytest tests/test_integration/test_cli.py::TestCLIIntegration -v

# Pipeline tests
uv run pytest tests/test_integration/test_pipeline.py::TestFullPipelineIntegration -v
```

## Run Specific Tests

```bash
# Run a single test
uv run pytest tests/test_integration/test_cli.py::TestCLIBasic::test_cli_help -v

# Run tests matching a pattern
uv run pytest tests/ -k "cli" -v
uv run pytest tests/ -k "database" -v
uv run pytest tests/ -k "json" -v
```

## Coverage Reports

```bash
# Terminal report with missing lines
uv run pytest tests/ --cov=src --cov-report=term-missing

# HTML coverage report
uv run pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in browser

# Skip files with complete coverage
uv run pytest tests/ --cov=src --cov-report=term:skip-covered
```

## Debug Options

```bash
# Show print statements
uv run pytest tests/ -v -s

# Stop on first failure
uv run pytest tests/ -x

# Show detailed traceback
uv run pytest tests/ -v --tb=long

# Show only short traceback
uv run pytest tests/ -v --tb=short

# Show local variables in traceback
uv run pytest tests/ -v --tb=short --showlocals
```

## Test Statistics

```bash
# Collect test info without running
uv run pytest tests/ --collect-only

# Show slowest tests
uv run pytest tests/ --durations=10

# Show test execution times
uv run pytest tests/ -v --durations=0
```

## Current Test Suite Status

- **Total Tests**: 134
- **Pass Rate**: 100% (134/134) ✅
- **Coverage**: 63% (Core modules: 80-100%)
- **Execution Time**: ~33-50 seconds

## Test Files Summary

1. `test_format_parser.py` - 9 tests (format detection, parsing)
2. `test_extraction.py` - 15 tests (field extraction, validation)
3. `test_converter_api.py` - 13 tests (file processing, batch)
4. `test_transformer.py` - 17 tests (data transformation)
5. `test_json_writer.py` - 17 tests (JSON output)
6. `test_database.py` - 21 tests (DuckDB operations)
7. `test_scanner.py` - 17 tests (file discovery)
8. `test_pipeline.py` - 8 tests (ETL integration)
9. `test_cli.py` - 17 tests (CLI commands)

## CLI Testing with Actual Commands

```bash
# Test CLI directly (outside pytest)
converter --help
converter --version

# Process files
converter process -i datasets/problems/tsp -o /tmp/output

# Analyze database
converter analyze -d /tmp/output/db/routing.duckdb

# Validate database
converter validate -d /tmp/output/db/routing.duckdb
```

## Continuous Integration

```bash
# Run all tests with coverage (CI/CD)
uv run pytest tests/ --cov=src --cov-report=xml --cov-report=term

# Check for test failures
uv run pytest tests/ -v --tb=short || echo "Tests failed!"
```
