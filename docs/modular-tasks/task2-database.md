# Task 2: Database Foundation Implementation

## Objective
Implement the database layer for the TSPLIB95 ETL system, including schema definitions and CRUD operations using DuckDB.

## Context
This task implements Phase 1.3 from `docs/phase1.md`. The database layer provides:
- Schema creation and management for problems, nodes, and edges tables
- CRUD operations with proper transaction management
- Conflict resolution and incremental updates
- Query interface for data retrieval

## Prerequisites
- Python >= 3.11
- DuckDB dependency already installed in pyproject.toml
- Understanding of TSPLIB95 data structure (see `.github/copilot-instructions.md`)

## Implementation Requirements

### 1. Create Database Schema Module

**File: `src/converter/database/__init__.py`**
- Package initialization file

**File: `src/converter/database/schema.py`**
- Define SQL schema for problems, nodes, and edges tables
- Create indexes for performance optimization
- Provide schema versioning support

Schema requirements:
- **problems table**: Store problem metadata (name, type, dimension, file info, etc.)
- **nodes table**: Store node coordinates, demands, depot flags
- **edges table**: Store edge weights and fixed edge indicators
- **indexes**: On problem type/dimension, problem_id foreign keys, depot flags

### 2. Create Database Operations Module

**File: `src/converter/database/operations.py`**
- Implement `DatabaseManager` class with:
  - Database initialization and schema creation
  - Transaction-based problem insertion (problem + nodes + edges)
  - Bulk insert operations for performance
  - Query methods for data retrieval
  - Proper error handling with rollback

Key methods needed:
- `__init__(db_path, logger)`: Initialize database and schema
- `insert_problem(problem_data)`: Insert complete problem with transaction
- `get_problem_by_name(name)`: Retrieve problem data
- `get_problem_statistics()`: Database statistics
- Transaction management with proper rollback on errors

### 3. Update Utilities

**File: `src/converter/utils/__init__.py`**
- Package initialization

**File: `src/converter/utils/exceptions.py`**
- Define exception hierarchy: `ConverterError`, `DatabaseError`, `FileProcessingError`, `ValidationError`, `ParsingError`

**File: `src/converter/utils/logging.py`**
- Implement `setup_logging(level, log_file)` function
- Configure console and file handlers with proper formatting

### 4. Create Configuration Module

**File: `src/converter/__init__.py`**
- Package initialization with version

**File: `src/converter/config.py`**
- Define `ConverterConfig` dataclass with:
  - Input/output path settings
  - Database path configuration  
  - Processing settings (batch size, workers)
  - Logging configuration

## Expected Data Structure

The `insert_problem()` method should accept data in this format:

```python
{
    'problem_data': {
        'name': str,
        'type': str,  # TSP|VRP|ATSP|HCP|SOP|TOUR
        'dimension': int,
        'comment': str (optional),
        'capacity': int (optional),
        'edge_weight_type': str (optional),
        'edge_weight_format': str (optional),
        'node_coord_type': str (optional),
        'display_data_type': str (optional)
    },
    'nodes': [
        {
            'node_id': int,  # 0-based
            'x': float (optional),
            'y': float (optional),
            'z': float (optional),
            'demand': int (default 0),
            'is_depot': bool (default False),
            'display_x': float (optional),
            'display_y': float (optional)
        }
    ],
    'edges': [
        {
            'from_node': int,  # 0-based
            'to_node': int,    # 0-based
            'weight': float,
            'is_fixed': bool (default False)
        }
    ],
    'metadata': {
        'file_path': str,
        'file_size': int
    }
}
```

## Implementation Guidelines

### Database Best Practices
1. **Use transactions**: Wrap problem insertion in BEGIN/COMMIT/ROLLBACK
2. **Bulk operations**: Use executemany() for nodes and edges
3. **Conflict resolution**: Use INSERT OR REPLACE for updates
4. **Error handling**: Catch and wrap exceptions in DatabaseError
5. **Connection management**: Use context managers (with statement)
6. **0-based indexing**: All node IDs must be 0-based in database

### Code Quality
1. Follow existing tsplib95 code style
2. Add docstrings to all classes and methods
3. Use type hints for all function signatures
4. Proper error messages with context
5. Logger integration for debugging

## Testing Requirements

**File: `tests/test_database.py`**

Create focused tests:
1. Test schema creation
2. Test problem insertion with transaction
3. Test bulk node/edge insertion
4. Test conflict resolution (update existing problem)
5. Test error handling and rollback
6. Test query operations

Use in-memory database (`:memory:`) for tests.

## Success Criteria

- [ ] All database schema tables created correctly
- [ ] DatabaseManager can insert problems with full transaction support
- [ ] Bulk insert operations work for nodes and edges
- [ ] Proper error handling with rollback on failure
- [ ] All tests pass
- [ ] Code follows project style guidelines
- [ ] Logging integrated throughout

## Reference Documentation

- `docs/phase1.md` - Complete Phase 1 specification
- `docs/implementation-plan.md` - Overall project plan
- `docs/diagrams/database-schema.mmd` - Database schema diagram
- `.github/copilot-instructions.md` - Project conventions and architecture

## Files to Create

```
src/converter/
├── __init__.py
├── config.py
├── database/
│   ├── __init__.py
│   ├── schema.py
│   └── operations.py
└── utils/
    ├── __init__.py
    ├── exceptions.py
    └── logging.py

tests/
└── test_database.py
```

## Notes

- Database path default: `./datasets/db/routing.duckdb`
- All node IDs must be 0-based (TSPLIB uses 1-based, convert during parsing)
- Problems table has UNIQUE constraint on name for conflict detection
- Foreign key constraints ensure referential integrity
- Indexes optimize common query patterns (type, dimension, problem_id)
