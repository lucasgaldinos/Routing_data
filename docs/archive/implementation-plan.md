# TSPLIB95 ETL System Implementation Plan

## Overview

This document outlines the implementation plan for creating an ETL (Extract, Transform, Load) system that converts TSPLIB95 format files into JSON format and a DuckDB database. The system is designed to be extensible, maintainable, and capable of handling large datasets efficiently.

## Project Structure

```tree
src/
├── converter/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── scanner.py          # File discovery and classification
│   │   ├── parser.py           # TSPLIB95 parsing using vendored library
│   │   └── transformer.py      # Data transformation and extraction
│   ├── database/
│   │   ├── __init__.py
│   │   ├── schema.py           # Database schema definitions
│   │   ├── models.py           # Data models and validation
│   │   └── operations.py       # CRUD operations and queries
│   ├── output/
│   │   ├── __init__.py
│   │   ├── json_writer.py      # JSON file generation
│   │   └── formats.py          # Output format definitions
│   ├── cli/
│   │   ├── __init__.py
│   │   └── commands.py         # Command-line interface
│   └── utils/
│       ├── __init__.py
│       ├── logging.py          # Logging configuration
│       ├── parallel.py         # Parallel processing utilities
│       └── validation.py       # Data validation helpers
```

## Database Schema Design

### Problems Table

```sql
CREATE TABLE problems (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    type VARCHAR NOT NULL,  -- TSP, VRP, ATSP, HCP, SOP, TOUR
    comment TEXT,
    dimension INTEGER NOT NULL,
    capacity INTEGER,
    edge_weight_type VARCHAR,
    edge_weight_format VARCHAR,
    node_coord_type VARCHAR,
    display_data_type VARCHAR,
    file_path VARCHAR NOT NULL,
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Nodes Table

```sql
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY,
    problem_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
    x DOUBLE,
    y DOUBLE, 
    z DOUBLE,
    demand INTEGER DEFAULT 0,
    is_depot BOOLEAN DEFAULT FALSE,
    display_x DOUBLE,
    display_y DOUBLE,
    FOREIGN KEY (problem_id) REFERENCES problems(id),
    UNIQUE(problem_id, node_id)
);
```

### Edges Table

```sql
CREATE TABLE edges (
    id INTEGER PRIMARY KEY,
    problem_id INTEGER NOT NULL,
    from_node INTEGER NOT NULL,
    to_node INTEGER NOT NULL,
    weight DOUBLE NOT NULL,
    is_fixed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (problem_id) REFERENCES problems(id),
    UNIQUE(problem_id, from_node, to_node)
);
```

## Implementation Phases

### Phase 1: Core Infrastructure (2-3 days)

#### 1.1 Project Setup

- [x] 1.1.1 Create proper src/ directory structure
- [ ] 1.1.2 Set up logging system with configurable levels
- [ ] 1.1.3 Create base exception classes for error handling
- [ ] 1.1.4 Implement data validation utilities

#### 1.2 TSPLIB95 Parser Integration

- [ ] 1.2.1 Wrap vendored tsplib95 library functionality  
- [ ] 1.2.2 Implement StandardProblem parsing with error handling
- [ ] 1.2.3 Add validation for parsed problem data
- [ ] 1.2.4 Create problem metadata extraction

#### 1.3 Database Foundation

- [ ] 1.3.1 Design schema based on parsed data structure
- [ ] 1.3.2 Implement DuckDB schema creation and management
- [ ] 1.3.3 Create database connection management
- [ ] 1.3.4 Implement CRUD operations with conflict resolution
- [ ] 1.3.5 Add database migration support

### Phase 2: Data Processing (3-4 days)

#### 2.1 File Scanner

- [ ] 2.1.1 Implement recursive directory traversal
- [ ] 2.1.2 Add file type detection and classification
- [ ] 2.1.3 Implement batch processing with progress tracking
- [ ] 2.1.4 Add error handling for corrupt/invalid files

#### 2.2 Data Transformer

- [ ] Convert StandardProblem to normalized data structures
- [ ] Extract nodes, edges, and graph metadata
- [ ] Handle different problem types (TSP, VRP, ATSP, etc.)
- [ ] Implement data flattening for JSON output

#### 2.3 JSON Output

- [ ] Create JSON file writer with proper formatting
- [ ] Implement directory structure creation
- [ ] Add file naming conventions and organization
- [ ] Ensure JSON compatibility and validation

### Phase 3: Advanced Features (2-3 days)

#### 3.1 Parallel Processing

- [ ] Implement thread-safe file processing
- [ ] Add batch processing with configurable batch sizes
- [ ] Create progress tracking and reporting
- [ ] Handle memory management for large datasets

#### 3.2 CLI Interface

- [ ] Create command-line interface using Click
- [ ] Add configuration file support
- [ ] Implement progress bars and status reporting
- [ ] Add dry-run and validation modes

#### 3.3 Update Functionality

- [ ] Detect file changes and updates
- [ ] Implement incremental database updates
- [ ] Add conflict resolution strategies
- [ ] Create backup and recovery mechanisms

### Phase 4: Testing and Optimization (1-2 days)

#### 4.1 Testing Suite

- [ ] Unit tests for all core components
- [ ] Integration tests for end-to-end processing
- [ ] Performance tests with large datasets
- [ ] Error handling and edge case tests

#### 4.2 Performance Optimization

- [ ] Profile memory usage and processing times
- [ ] Optimize database operations and queries
- [ ] Implement caching strategies
- [ ] Add monitoring and metrics collection

## Key Design Patterns

### 1. Strategy Pattern for Problem Types

```python
class ProblemProcessor:
    def __init__(self):
        self.processors = {
            'TSP': TSPProcessor(),
            'VRP': VRPProcessor(), 
            'ATSP': ATSPProcessor(),
            # ... etc
        }
    
    def process(self, problem):
        processor = self.processors.get(problem.type)
        return processor.process(problem)
```

### 2. Factory Pattern for Output Formats

```python
class OutputFactory:
    @staticmethod
    def create_writer(format_type: str):
        if format_type == 'json':
            return JSONWriter()
        elif format_type == 'csv':
            return CSVWriter()
        # ... etc
```

### 3. Observer Pattern for Progress Tracking

```python
class ProcessingObserver:
    def on_file_started(self, filename): pass
    def on_file_completed(self, filename, result): pass
    def on_error(self, filename, error): pass
```

## Configuration System

### config.yaml

```yaml
# Input settings
input:
  datasets_path: "./datasets_raw"
  file_patterns: ["*.tsp", "*.vrp", "*.atsp", "*.hcp", "*.sop", "*.tour"]
  recursive: true

# Output settings  
output:
  json_path: "./datasets/json"
  database_path: "./datasets/db/routing.duckdb"
  create_directories: true
  
# Processing settings
processing:
  parallel: true
  max_workers: 4
  batch_size: 100
  memory_limit: "2GB"

# Database settings
database:
  backup_on_update: true
  conflict_resolution: "update"  # update, skip, error
  vacuum_after_load: true

# Logging
logging:
  level: "INFO"
  file: "./logs/converter.log"
  console: true
```

## Error Handling Strategy

### Exception Hierarchy

```python
class ConverterError(Exception):
    """Base exception for converter operations"""
    pass

class FileProcessingError(ConverterError):
    """Raised when file processing fails"""
    pass

class DatabaseError(ConverterError):
    """Raised when database operations fail"""
    pass

class ValidationError(ConverterError):
    """Raised when data validation fails"""
    pass
```

### Error Recovery

1. **File-level errors**: Log error, continue with next file
2. **Database errors**: Rollback transaction, retry with backoff
3. **Critical errors**: Graceful shutdown with cleanup
4. **Validation errors**: Skip invalid data, report in summary

## Performance Considerations

### Memory Management

- Stream processing for large files
- Configurable batch sizes
- Memory usage monitoring and limits
- Garbage collection optimization

### Database Performance

- Bulk insert operations with prepared statements
- Index creation after data loading
- Connection pooling for parallel processing
- Query optimization and analysis

### Parallel Processing

- Thread-safe database operations
- Work queue with configurable worker count
- Progress aggregation across workers
- Resource contention management

## Quality Assurance

### Code Quality

- Type hints throughout codebase
- Comprehensive docstrings
- Code formatting with black/ruff
- Static analysis with mypy

### Testing Strategy

- Unit tests for individual components
- Integration tests for complete workflows
- Performance benchmarks
- Error condition testing

### Documentation

- API documentation with examples
- User guide and tutorials
- Configuration reference
- Troubleshooting guide

## Deliverables

1. **Fully functional ETL system** with all specified features
2. **Comprehensive test suite** with >90% code coverage
3. **User documentation** including setup and usage guides
4. **Performance benchmarks** and optimization recommendations
5. **Configuration examples** for different use cases

## Success Criteria

1. Successfully process all files in datasets_raw/problems/
2. Generate valid JSON output with flattened structure
3. Create properly normalized DuckDB database
4. Handle updates and incremental loading
5. Process 1000+ files efficiently with parallel processing
6. Provide clear error reporting and logging
7. Maintain data integrity and consistency
8. Support configuration and customization

## Next Steps

1. Get user approval for this implementation plan
2. Begin Phase 1 implementation with project setup
3. Create initial database schema and core classes
4. Implement file scanner and basic processing pipeline
5. Integrate with tsplib95 library for parsing
6. Add JSON output and database storage
7. Implement parallel processing and CLI interface
8. Complete testing and documentation

This plan provides a solid foundation for building a robust, scalable ETL system that meets all the specified requirements while following software engineering best practices.
