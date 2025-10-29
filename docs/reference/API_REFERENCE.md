# API Reference - TSPLIB95 ETL System

## Overview

The TSPLIB95 ETL System provides both a Python API and CLI for converting TSPLIB95/VRP routing problems into JSON and DuckDB formats. This document covers the complete programmatic interface.

## Installation & Setup

```python
import converter

# Optional: Configure logging
from converter.utils.logging import setup_logging
logger = setup_logging("INFO")
```

## Core API Functions

### File Parsing

#### `converter.parse_file(file_path: str) -> Dict[str, Any]`

Parse a single TSPLIB file and return structured data.

```python
# Parse TSP file
data = converter.parse_file("datasets_raw/problems/tsp/gr17.tsp")

# Returns structured data:
{
    'problem_data': {
        'name': 'gr17',
        'type': 'TSP', 
        'dimension': 17,
        'edge_weight_type': 'EUC_2D',
        ...
    },
    'nodes': [
        {'node_id': 0, 'x': 38.24, 'y': 20.42, 'demand': 0, 'is_depot': False},
        ...
    ],
    'edges': [...],  # Only for EXPLICIT weight types
    'tours': [...],  # If solution file provided
    'metadata': {
        'file_path': '/path/to/gr17.tsp',
        'file_size': 1024,
        'parsing_time': 0.045
    }
}
```

**Supported File Types:**

- `.tsp` - Traveling Salesman Problem
- `.atsp` - Asymmetric TSP
- `.vrp` - Vehicle Routing Problem  
- `.hcp` - Hamiltonian Cycle Problem
- `.sop` - Sequential Ordering Problem
- `.tour` - Solution/Tour files

**Key Features:**

- **Automatic index conversion**: TSPLIB95's 1-based → 0-based for database compatibility
- **Distance function support**: EUC_2D, MAN_2D, GEO, ATT, EXPLICIT, etc.
- **VRP extensions**: Handles demands, depots, capacity constraints
- **Error handling**: Comprehensive validation with detailed error messages

### Output Generation

#### `converter.to_json(data: Dict[str, Any], output_path: str) -> None`

Convert parsed data to JSON format.

```python
data = converter.parse_file("problem.tsp")
converter.to_json(data, "output/problem.json")

# Creates flattened JSON structure optimized for analysis:
{
    "problem": {
        "name": "gr17",
        "type": "TSP",
        "dimension": 17
    },
    "nodes": [...],
    "solution_quality": {
        "optimal_distance": 2085,
        "tour_length": 17
    }
}
```

#### `converter.to_database(data: Dict[str, Any], db_path: str) -> int`

Store data in DuckDB database with full relational schema.

```python
data = converter.parse_file("problem.tsp")
problem_id = converter.to_database(data, "datasets/routing.duckdb")

print(f"Stored as problem ID: {problem_id}")
```

**Database Schema:**

- `problems` - Problem metadata (name, type, dimension, etc.)
- `nodes` - Node coordinates, demands, depot flags
- `edges` - Precomputed edge weights (EXPLICIT types only)
- `tours` - Solution tours (if available)
- `file_tracking` - Change detection for incremental processing

#### `converter.process_directory(input_dir: str, output_dir: str, **kwargs) -> Dict[str, Any]`

Batch process entire directories with parallel processing.

```python
# Basic directory processing
results = converter.process_directory(
    input_dir="datasets_raw/problems",
    output_dir="datasets"
)

# Advanced options
results = converter.process_directory(
    input_dir="datasets_raw/problems",
    output_dir="datasets", 
    workers=8,                    # Parallel processing
    batch_size=200,              # Files per batch
    file_patterns=["*.tsp", "*.vrp"],  # Specific types only
    force_reprocess=False,       # Skip unchanged files
    memory_limit_mb=4096        # Memory management
)

# Returns processing statistics:
{
    'total_files': 1234,
    'processed_files': 856,
    'skipped_files': 378,
    'failed_files': 0,
    'processing_time': 45.2,
    'database_size_mb': 128.5,
    'json_files_created': 856
}
```

## Low-Level Parsing API

For advanced use cases requiring direct access to the TSPLIB95 parser, use the `FormatParser` class (recommended) or the deprecated legacy functions.

### FormatParser (Recommended)

The `FormatParser` class provides the most control over TSPLIB95 file parsing with proper error handling and logging.

```python
from tsplib_parser.parser import FormatParser
from converter.utils.logging import setup_logging

# Initialize parser
logger = setup_logging("INFO")
parser = FormatParser(logger=logger)

# Parse TSPLIB95 file
result = parser.parse_file("datasets_raw/problems/tsp/gr17.tsp")

# Returns detailed parsed data:
{
    'problem_data': {
        'name': 'gr17',
        'type': 'TSP',
        'dimension': 17,
        'edge_weight_type': 'EXPLICIT',
        'edge_weight_format': 'LOWER_DIAG_ROW',
        'node_coord_type': None,
        'capacity': None,
        'depots': None,
        'display_data_type': None
    },
    'nodes': [],  # Empty for EXPLICIT types
    'edge_weights': [...],  # Full distance matrix
    'tours': [],
    'metadata': {
        'file_path': '/absolute/path/to/gr17.tsp',
        'file_size': 1024,
        'parsing_time': 0.045
    }
}
```

**Key Features:**

- Handles all TSPLIB95 formats (TSP, ATSP, VRP, HCP, SOP, TOUR)
- Proper index conversion (1-based → 0-based)
- Matrix expansion for EXPLICIT edge weights
- Comprehensive error reporting
- Logging integration

**Use Cases:**

- Custom data pipelines
- Research tools requiring low-level access
- Debugging TSPLIB95 format issues
- Integration with other systems

### Deprecated Legacy Functions

> ⚠️ **DEPRECATED**: The following functions are deprecated and will be removed in a future version. Please migrate to `FormatParser` for new code.

#### `parse_tsplib(text: str, special: dict = None) -> StandardProblem`

**Deprecated since**: Version 1.0  
**Migration**: Use `FormatParser.parse_file()` instead

```python
# OLD (deprecated):
from tsplib_parser import parse_tsplib

with open('problem.tsp', 'r') as f:
    text = f.read()
problem = parse_tsplib(text)  # ⚠️ Deprecated

# NEW (recommended):
from tsplib_parser.parser import FormatParser

parser = FormatParser()
result = parser.parse_file('problem.tsp')  # ✅ Recommended
```

#### `load(path: str, special: dict = None) -> StandardProblem`

**Deprecated since**: Version 1.0  
**Migration**: Use `FormatParser.parse_file()` instead

```python
# OLD (deprecated):
from tsplib_parser import load

problem = load('problem.tsp')  # ⚠️ Deprecated

# NEW (recommended):
from tsplib_parser.parser import FormatParser

parser = FormatParser()
result = parser.parse_file('problem.tsp')  # ✅ Recommended
```

**Why Migrate?**

- `FormatParser` provides better error messages
- Integrated logging support
- Returns structured dictionaries instead of opaque objects
- Consistent API with the rest of the system
- Better testing and maintenance

**Migration Guide:**

1. Replace `from tsplib_parser import load, parse_tsplib` with `from tsplib_parser.parser import FormatParser`
2. Create a `FormatParser` instance: `parser = FormatParser(logger=your_logger)`
3. Use `parser.parse_file(path)` instead of `load(path)`
4. Update code to work with dictionary results instead of `StandardProblem` objects

## Advanced Components

### Custom Parser Integration

```python
from converter.core.parser import TSPLIBParser
from converter.core.transformer import DataTransformer

# Initialize with custom settings
parser = TSPLIBParser(logger=logger)
transformer = DataTransformer(logger=logger)

# Parse with special distance function
def custom_distance(coords1, coords2):
    # Custom distance calculation
    return ((coords1[0] - coords2[0])**2 + (coords1[1] - coords2[1])**2)**0.5

data = parser.parse_file("problem.tsp", special_func=custom_distance)
normalized_data = transformer.transform_problem(data)
```

### Database Operations

```python
from converter.database.operations import DatabaseManager

# Advanced database operations
db = DatabaseManager("routing.duckdb", logger=logger)

# Query examples
problems = db.get_problems_by_type("TSP")
large_problems = db.get_problems_by_dimension_range(100, 1000)
vrp_with_capacity = db.get_vrp_problems_with_capacity()

# Batch operations
db.bulk_insert_problems(problem_list)
db.update_problem_metadata(problem_id, new_metadata)

# Analytics queries
stats = db.get_collection_statistics()
performance_metrics = db.analyze_processing_performance()
```

### Parallel Processing Control

```python
from converter.utils.parallel import ParallelProcessor

# Fine-grained parallel processing
processor = ParallelProcessor(
    workers=8,
    batch_size=100,
    memory_limit_mb=2048,
    logger=logger
)

# Process with custom callback
def process_callback(file_path, result):
    print(f"Processed {file_path}: {result['nodes_count']} nodes")

results = processor.process_files(
    file_list=["file1.tsp", "file2.vrp"],
    process_function=converter.parse_file,
    callback=process_callback
)
```

## Configuration Management

### YAML Configuration

```python
from converter.config import load_config, save_config

# Load configuration
config = load_config("config.yaml")

# Modify settings
config['processing']['max_workers'] = 16
config['output']['json_output_path'] = "/custom/output"

# Save updated configuration
save_config(config, "custom_config.yaml")
```

**Configuration Options:**

```yaml
# Processing settings
processing:
  batch_size: 100
  max_workers: 4
  memory_limit_mb: 2048
  
# Input/Output paths
paths:
  input_path: "./datasets_raw/problems"
  json_output_path: "./datasets/json"
  database_path: "./datasets/db/routing.duckdb"
  
# File processing
files:
  patterns: ["*.tsp", "*.vrp", "*.atsp", "*.hcp", "*.sop", "*.tour"]
  max_file_size_mb: 100
  skip_corrupted: true
  
# Logging
logging:
  level: "INFO"
  file: "./logs/converter.log"
  console: true
```

## Error Handling

### Exception Hierarchy

```python
from converter.utils.exceptions import (
    ConverterError,          # Base exception
    ParsingError,           # TSPLIB parsing failures  
    ValidationError,        # Data validation failures
    DatabaseError,          # Database operation failures
    FileProcessingError,    # File I/O failures
    ConfigurationError      # Configuration issues
)

try:
    data = converter.parse_file("problematic.tsp")
except ParsingError as e:
    print(f"Parse failed: {e}")
    print(f"File: {e.file_path}")
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Validation Functions

```python
from converter.utils.validation import (
    validate_problem_data,
    validate_file_size,
    validate_coordinates,
    validate_tour_solution
)

# Validate before processing
if validate_file_size("large_file.tsp", max_mb=100):
    data = converter.parse_file("large_file.tsp")
    
    if validate_problem_data(data):
        converter.to_database(data, "routing.duckdb")
```

## Performance Optimization

### Memory Management

```python
# For large datasets, use streaming processing
results = converter.process_directory(
    "datasets_raw/problems",
    "datasets",
    batch_size=50,          # Smaller batches for large files
    memory_limit_mb=1024,   # Strict memory limits
    workers=2               # Fewer workers to reduce memory pressure
)
```

### Database Optimization

```python
# Optimize database for analytics
db = DatabaseManager("routing.duckdb", logger=logger)

# Create indexes for common queries
db.create_performance_indexes()

# Analyze query performance
query_stats = db.analyze_query_performance(
    "SELECT * FROM problems WHERE dimension > 1000"
)
```

## Integration Examples

### Data Analysis Pipeline

```python
import pandas as pd
import duckdb

# 1. Process TSPLIB files
converter.process_directory("datasets_raw/problems", "datasets")

# 2. Connect to database for analysis
conn = duckdb.connect("datasets/db/routing.duckdb")

# 3. Extract data for analysis
df = conn.execute("""
    SELECT p.name, p.type, p.dimension, 
           COUNT(n.node_id) as actual_nodes,
           AVG(n.x) as center_x, AVG(n.y) as center_y
    FROM problems p
    LEFT JOIN nodes n ON p.id = n.problem_id
    WHERE p.type = 'TSP' AND p.dimension < 100
    GROUP BY p.id, p.name, p.type, p.dimension
    ORDER BY p.dimension
""").df()

# 4. Analyze results
print(f"Average problem size: {df['dimension'].mean():.1f} nodes")
print(f"Problems with coordinate data: {df['center_x'].notna().sum()}")
```

### Custom ETL Pipeline

```python
# Custom processing pipeline
class CustomProcessor:
    def __init__(self):
        self.parser = TSPLIBParser()
        self.transformer = DataTransformer()
        self.db = DatabaseManager("custom.duckdb")
    
    def process_with_validation(self, file_path):
        try:
            # Parse with validation
            data = self.parser.parse_file(file_path)
            
            # Custom validation rules
            if data['problem_data']['dimension'] > 10000:
                raise ValidationError("Problem too large for processing")
            
            # Transform and store
            transformed = self.transformer.transform_problem(data)
            problem_id = self.db.insert_problem(transformed)
            
            return {'success': True, 'problem_id': problem_id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Use custom processor
processor = CustomProcessor()
result = processor.process_with_validation("huge_problem.tsp")
```

## Best Practices

### 1. **Always Use Dependency Injection**

```python
# Good: Pass logger to components
logger = setup_logging("INFO")
parser = TSPLIBParser(logger=logger)

# Bad: Components create their own loggers
parser = TSPLIBParser()  # Creates default logger
```

### 2. **Handle Index Conversion Explicitly**

```python
# The transformer automatically converts 1-based → 0-based
# But be aware of this when working with raw TSPLIB data
raw_data = parser.parse_file("problem.tsp")  # Still 1-based
transformed = transformer.transform_problem(raw_data)  # Now 0-based
```

### 3. **Use Batch Processing for Large Datasets**

```python
# Good: Process in batches
converter.process_directory("large_dataset/", batch_size=50, workers=4)

# Bad: Process all at once (memory issues)
for file in large_file_list:
    converter.parse_file(file)  # Memory accumulates
```

### 4. **Validate Before Processing**

```python
# Always validate files before processing
if validate_file_size(file_path, max_mb=100):
    data = converter.parse_file(file_path)
else:
    logger.warning(f"Skipping oversized file: {file_path}")
```

## Common Patterns

### Processing Status Tracking

```python
from tqdm import tqdm

def process_with_progress(file_list):
    results = []
    for file_path in tqdm(file_list, desc="Processing TSPLIB files"):
        try:
            data = converter.parse_file(file_path)
            converter.to_database(data, "routing.duckdb")
            results.append({'file': file_path, 'status': 'success'})
        except Exception as e:
            results.append({'file': file_path, 'status': 'failed', 'error': str(e)})
    
    return results
```

### Incremental Processing

```python
from converter.utils.update import UpdateManager

# Only process changed files
update_manager = UpdateManager(db_manager, logger)
file_list = ["file1.tsp", "file2.vrp", "file3.tsp"]

update_stats = update_manager.perform_incremental_update(
    file_list, 
    force=False  # Skip unchanged files
)

print(f"New files: {update_stats['new_files']}")
print(f"Modified files: {update_stats['modified_files']}")
print(f"Skipped files: {update_stats['unchanged_files']}")
```
