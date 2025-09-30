# GitHub Issue Title: Implement TSPLIB95 ETL System Phases 1-3

## Issue Description

@copilot #github-pull-request_copilot-coding-agent

We need to implement phases 1-3 of our TSPLIB95 ETL system that converts TSPLIB/VRP instances into JSON and DuckDB formats. This includes core infrastructure, data processing, and advanced features. Please follow the detailed implementation plan below.

### Project Background

- Repository contains a vendored copy of `tsplib95` library under `src/tsplib95/`
- Raw TSPLIB/VRP files are located in `datasets_raw/problems/{tsp,vrp,atsp,hcp,sop,tour}/`
- Output should go to `datasets/json/` (flattened JSON) and `datasets/db/routing.duckdb` (DuckDB database)
- **CRITICAL**: Read `.github/copilot-instructions.md` for complete architecture guidance
- **CRITICAL**: Follow `docs/implementation-plan.md` for detailed phase breakdown
- **CRITICAL**: Reference `docs/diagrams/converter-architecture.mmd` for system flow

### Existing Codebase Understanding

The vendored tsplib95 library provides these key classes and patterns:

```python
# Example usage patterns (study src/tsplib95/ for details):
from tsplib95 import loaders
from tsplib95.models import StandardProblem

# Basic parsing:
problem = loaders.load('path/to/file.tsp')
problem.as_name_dict()  # Clean data extraction (preferred)
problem.get_graph(normalize=True)  # 0-based node IDs
problem.get_weight(i, j)  # Get edge weight

# For SPECIAL distance types:
def custom_distance(coord1, coord2): return distance
problem = loaders.load('path', special=custom_distance)
```

### Environment Setup

- Python ≥ 3.11 required
- Use `uv` as the package manager: `uv add duckdb networkx click tabulate deprecated pytest pyyaml`

## Implementation Requirements

### Phase 1: Core Infrastructure

#### 1.1 Project Setup

- Project directory structure is already created under `src/converter/`
- **Create `src/converter/utils/logging.py`**:

```python
import logging
import sys
from typing import Optional

def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Configure logging with file and console handlers."""
    logger = logging.getLogger("converter")
    logger.setLevel(getattr(logging, level.upper()))
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
```

- **Create `src/converter/utils/exceptions.py`**:

```python
"""Exception hierarchy for converter operations."""

class ConverterError(Exception):
    """Base exception for all converter operations."""
    pass

class FileProcessingError(ConverterError):
    """Raised when file processing fails."""
    def __init__(self, file_path: str, message: str):
        self.file_path = file_path
        super().__init__(f"Error processing {file_path}: {message}")

class ValidationError(ConverterError):
    """Raised when data validation fails."""
    pass

class DatabaseError(ConverterError):
    """Raised when database operations fail."""
    pass

class ParsingError(FileProcessingError):
    """Raised when TSPLIB parsing fails."""
    pass
```

- **Create `src/converter/utils/validation.py`**:

```python
from typing import Dict, Any, List
import re

def validate_problem_data(data: Dict[str, Any]) -> List[str]:
    """Validate extracted problem data. Returns list of error messages."""
    errors = []
    
    # Required fields
    if not data.get('name'):
        errors.append("Problem name is required")
    if not data.get('type'):
        errors.append("Problem type is required")
    if not isinstance(data.get('dimension'), int) or data['dimension'] <= 0:
        errors.append("Dimension must be positive integer")
    
    # Type-specific validation
    problem_type = data.get('type', '').upper()
    if problem_type not in ['TSP', 'VRP', 'ATSP', 'HCP', 'SOP', 'TOUR']:
        errors.append(f"Unknown problem type: {problem_type}")
    
    return errors

def validate_coordinates(coords: List[tuple]) -> bool:
    """Validate coordinate data."""
    return all(
        isinstance(coord, (tuple, list)) and len(coord) >= 2
        for coord in coords
    )
```

#### 1.2 TSPLIB95 Parser Integration

**Create `src/converter/core/parser.py`** with complete implementation:

```python
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple
import logging

from tsplib95 import loaders
from tsplib95.models import StandardProblem
from ..utils.exceptions import ParsingError, ValidationError
from ..utils.validation import validate_problem_data

class TSPLIBParser:
    """
    Parser for TSPLIB format files with complete extraction capabilities.
    
    Key Requirements:
    - Parse all TSPLIB problem types (TSP, VRP, ATSP, HCP, SOP, TOUR)
    - Handle SPECIAL distance types with custom functions
    - Extract nodes, edges, and metadata in normalized format
    - Convert 1-based TSPLIB indices to 0-based database format
    - Validate data integrity and problem structure
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def parse_file(self, file_path: str, special_func: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Parse TSPLIB file and return complete normalized data structure.
        
        Returns:
            {
                'problem_data': {...},  # Basic problem metadata
                'nodes': [...],         # Node coordinates and properties
                'edges': [...],         # Edge weights and properties 
                'tours': [...],         # Tour data if available
                'metadata': {...}       # File and processing metadata
            }
        """
        try:
            # Load using tsplib95 with special distance handling
            problem = loaders.load(file_path, special=special_func)
            
            # Validate the loaded problem
            self.validate_problem(problem)
            
            # Extract all components
            result = {
                'problem_data': self._extract_problem_data(problem),
                'nodes': self._extract_nodes(problem),
                'edges': self._extract_edges(problem),
                'tours': self._extract_tours(problem),
                'metadata': self._extract_metadata(problem, file_path)
            }
            
            self.logger.info(f"Successfully parsed {file_path}: {result['problem_data'].get('type')} "
                           f"with {len(result['nodes'])} nodes, {len(result['edges'])} edges")
            return result
            
        except Exception as e:
            raise ParsingError(file_path, str(e))
    
    def _extract_problem_data(self, problem: StandardProblem) -> Dict[str, Any]:
        """Extract basic problem metadata using as_name_dict() for clean data."""
        # TODO: Implement using problem.as_name_dict() - excludes defaults
        # Must include: name, type, comment, dimension, capacity, edge_weight_type, etc.
        pass
    
    def _extract_nodes(self, problem: StandardProblem) -> List[Dict[str, Any]]:
        """
        Extract node data with coordinates, demands, and depot information.
        
        Returns list of nodes with structure:
        {
            'node_id': int,      # Original 1-based TSPLIB ID
            'x': float,          # X coordinate
            'y': float,          # Y coordinate  
            'z': float,          # Z coordinate (if 3D)
            'demand': int,       # Node demand (VRP)
            'is_depot': bool,    # True if depot node (VRP)
            'display_x': float,  # Display coordinates if different
            'display_y': float
        }
        """
        # TODO: Implement node extraction
        # Use problem.node_coords, problem.demands, problem.depots
        # Handle coordinate types: NODE_COORD_SECTION, DISPLAY_DATA_SECTION
        pass
    
    def _extract_edges(self, problem: StandardProblem) -> List[Dict[str, Any]]:
        """
        Extract edge weights in normalized format.
        
        Returns list of edges with structure:
        {
            'from_node': int,    # 0-based normalized source node
            'to_node': int,      # 0-based normalized target node
            'weight': float,     # Edge weight/distance
            'is_fixed': bool     # True if edge is fixed (from FIXED_EDGES_SECTION)
        }
        """
        # TODO: Implement edge extraction
        # Use problem.get_graph(normalize=True) for 0-based indexing
        # Handle different weight sources: explicit matrices vs. distance functions
        # For symmetric problems, store both directions or implement constraint
        pass
    
    def _extract_tours(self, problem: StandardProblem) -> List[Dict[str, Any]]:
        """Extract tour data if available (from .tour files)."""
        # TODO: Implement tour extraction
        # Use problem.tours if available, handle -1 terminators
        pass
    
    def _extract_metadata(self, problem: StandardProblem, file_path: str) -> Dict[str, Any]:
        """Extract comprehensive file and processing metadata."""
        file_path_obj = Path(file_path)
        
        return {
            'file_path': str(file_path),
            'file_size': file_path_obj.stat().st_size if file_path_obj.exists() else 0,
            'file_name': file_path_obj.name,
            'problem_source': file_path_obj.parent.name,
            'has_coordinates': hasattr(problem, 'node_coords') and bool(problem.node_coords),
            'has_demands': hasattr(problem, 'demands') and bool(problem.demands),
            'has_depots': hasattr(problem, 'depots') and bool(problem.depots),
            'is_symmetric': self._check_symmetry(problem),
            'weight_source': self._identify_weight_source(problem)
        }
    
    def _check_symmetry(self, problem: StandardProblem) -> bool:
        """Determine if problem has symmetric distances."""
        # TODO: Implement symmetry detection
        # Check problem type and edge_weight_format
        pass
    
    def _identify_weight_source(self, problem: StandardProblem) -> str:
        """Identify how edge weights are determined."""
        # TODO: Implement weight source detection
        # Return: 'explicit_matrix', 'coordinate_based', 'special_function'
        pass
    
    def validate_problem(self, problem: StandardProblem) -> None:
        """Comprehensive problem validation with specific error messages."""
        if not isinstance(problem, StandardProblem):
            raise ValidationError("Not a valid StandardProblem")
        
        # Extract data for validation
        data = problem.as_name_dict()
        errors = validate_problem_data(data)
        
        # Additional structural validation
        if hasattr(problem, 'dimension') and problem.dimension:
            if hasattr(problem, 'node_coords') and problem.node_coords:
                if len(problem.node_coords) != problem.dimension:
                    errors.append(f"Node coordinate count {len(problem.node_coords)} "
                                f"doesn't match dimension {problem.dimension}")
        
        if errors:
            raise ValidationError(f"Validation errors: {'; '.join(errors)}")
    
    def detect_special_distance_type(self, file_path: str) -> bool:
        """Detect if file requires special distance function."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                return 'EDGE_WEIGHT_TYPE' in content and 'SPECIAL' in content
        except Exception:
            return False
    
    def get_required_special_functions(self) -> Dict[str, Callable]:
        """
        Return mapping of SPECIAL distance types to their functions.
        
        Agent must implement distance functions for:
        - XRAY problems: Custom geometric calculations
        - Other SPECIAL types as encountered in dataset
        """
        # TODO: Implement special distance function registry
        # Research actual SPECIAL types in datasets_raw/problems/
        pass
```

#### 1.3 Database Foundation

**Create `src/converter/database/schema.py`**:

```python
"""Database schema definitions for TSPLIB converter."""

# SQL for creating tables - reference docs/diagrams/database-schema.mmd
CREATE_PROBLEMS_TABLE = """
CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    type VARCHAR NOT NULL,  -- TSP|VRP|ATSP|HCP|SOP|TOUR
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
"""

CREATE_NODES_TABLE = """
CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY,
    problem_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,  -- Original 1-based ID from TSPLIB
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
"""

CREATE_EDGES_TABLE = """
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY,
    problem_id INTEGER NOT NULL,
    from_node INTEGER NOT NULL,  -- 0-based normalized
    to_node INTEGER NOT NULL,    -- 0-based normalized
    weight DOUBLE NOT NULL,
    is_fixed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (problem_id) REFERENCES problems(id),
    UNIQUE(problem_id, from_node, to_node)
);
"""

# Performance indexes - see docs/diagrams/database-queries.mmd for query patterns
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_problems_type_dimension ON problems(type, dimension);",
    "CREATE INDEX IF NOT EXISTS idx_nodes_problem_id ON nodes(problem_id);",
    "CREATE INDEX IF NOT EXISTS idx_edges_problem_id ON edges(problem_id);",
    "CREATE INDEX IF NOT EXISTS idx_nodes_depot ON nodes(problem_id, is_depot);",
]

def get_schema_version() -> str:
    """Get current schema version."""
    return "1.0.0"
```

**Create `src/converter/database/operations.py`** with complete CRUD interface:

```python
import duckdb
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

from .schema import (
    CREATE_PROBLEMS_TABLE, CREATE_NODES_TABLE, CREATE_EDGES_TABLE, 
    CREATE_INDEXES
)
from ..utils.exceptions import DatabaseError

class DatabaseManager:
    """
    Complete database management for TSPLIB converter.
    
    Key Requirements:
    - Thread-safe database operations for parallel processing
    - Bulk insert operations with prepared statements
    - Conflict resolution and incremental updates
    - Query interface for analysis and validation
    - Transaction management and error recovery
    """
    
    def __init__(self, db_path: str, logger: Optional[logging.Logger] = None):
        self.db_path = Path(db_path)
        self.logger = logger or logging.getLogger(__name__)
        self._ensure_db_directory()
        self._initialize_schema()
    
    def _ensure_db_directory(self):
        """Create database directory if it doesn't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _initialize_schema(self):
        """Initialize database schema and indexes."""
        try:
            with duckdb.connect(str(self.db_path)) as conn:
                # Create tables
                conn.execute(CREATE_PROBLEMS_TABLE)
                conn.execute(CREATE_NODES_TABLE)
                conn.execute(CREATE_EDGES_TABLE)
                
                # Create indexes
                for index_sql in CREATE_INDEXES:
                    conn.execute(index_sql)
                
                self.logger.info("Database schema initialized")
        except Exception as e:
            raise DatabaseError(f"Schema initialization failed: {e}")
    
    def insert_complete_problem(self, problem_data: Dict[str, Any]) -> int:
        """
        Insert complete problem with nodes and edges in single transaction.
        
        Args:
            problem_data: Complete data structure from parser with:
                - 'problem_data': Basic problem metadata
                - 'nodes': List of node dictionaries  
                - 'edges': List of edge dictionaries
                
        Returns:
            problem_id: Database ID of inserted problem
        """
        try:
            with duckdb.connect(str(self.db_path)) as conn:
                conn.execute("BEGIN TRANSACTION")
                
                # Insert problem and get ID
                problem_id = self._insert_problem_data(conn, problem_data['problem_data'])
                
                # Insert nodes if present
                if problem_data.get('nodes'):
                    self._bulk_insert_nodes(conn, problem_id, problem_data['nodes'])
                
                # Insert edges if present  
                if problem_data.get('edges'):
                    self._bulk_insert_edges(conn, problem_id, problem_data['edges'])
                
                conn.execute("COMMIT")
                return problem_id
                
        except Exception as e:
            conn.execute("ROLLBACK")
            raise DatabaseError(f"Complete problem insertion failed: {e}")
    
    def _insert_problem_data(self, conn, problem_data: Dict[str, Any]) -> int:
        """Insert problem metadata and return ID."""
        # TODO: Implement with proper conflict resolution
        # Must handle UPSERT logic for incremental updates
        # Return problem_id for foreign key references
        pass
    
    def _bulk_insert_nodes(self, conn, problem_id: int, nodes_data: List[Dict[str, Any]]):
        """Bulk insert nodes using prepared statements for performance."""
        # TODO: Implement bulk insert with executemany()
        # Clear existing nodes for problem_id first
        # Use prepared statement for performance with large node sets
        pass
    
    def _bulk_insert_edges(self, conn, problem_id: int, edges_data: List[Dict[str, Any]]):
        """Bulk insert edges with conflict resolution."""
        # TODO: Implement bulk edge insertion
        # Handle symmetric vs asymmetric edge storage
        # Use UPSERT for weight updates in incremental processing
        pass
    
    def get_problem_summary(self, problem_name: str = None) -> List[Dict[str, Any]]:
        """
        Get problem summary statistics.
        
        Returns:
            List of problems with node/edge counts and basic metadata
        """
        # TODO: Implement summary query
        # Join problems with counts from nodes/edges tables
        # Filter by problem_name if provided
        pass
    
    def get_problems_by_type(self, problem_type: str, min_dimension: int = None) -> List[Dict[str, Any]]:
        """Query problems by type with optional size filtering."""
        # TODO: Implement filtered query
        # Use indexes for efficient filtering
        # Support: TSP, VRP, ATSP, HCP, SOP, TOUR
        pass
    
    def check_problem_exists(self, problem_name: str, file_path: str = None) -> Optional[Tuple[int, str]]:
        """
        Check if problem exists and needs update.
        
        Returns:
            (problem_id, last_updated) if exists, None otherwise
        """
        # TODO: Implement existence check
        # Compare file modification times for update detection
        # Return data for incremental processing decisions
        pass
    
    def get_problem_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        # TODO: Implement statistics query
        # Return: total problems, breakdown by type, average dimensions, etc.
        # Use GROUP BY queries for type analysis
        pass
    
    def validate_data_integrity(self) -> List[str]:
        """
        Validate database integrity and return list of issues.
        
        Checks:
        - Foreign key consistency
        - Node count vs dimension
        - Edge symmetry for TSP problems  
        - VRP depot requirements
        """
        # TODO: Implement integrity validation
        # Return list of error messages for any inconsistencies
        pass
    
    def export_problem_json(self, problem_name: str) -> Dict[str, Any]:
        """Export complete problem data as JSON structure."""
        # TODO: Implement JSON export
        # Join all tables for complete problem reconstruction
        # Match output format from JSON writer
        pass
    
    def get_connection(self):
        """Get database connection for custom queries."""
        return duckdb.connect(str(self.db_path))
```

### Phase 2: Data Processing

#### 2.1 File Scanner

**Create `src/converter/core/scanner.py`** with complete discovery system:

```python
from pathlib import Path
from typing import List, Dict, Any, Iterator, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import mimetypes

class FileScanner:
    """
    Comprehensive file discovery and batch processing system.
    
    Requirements:
    - Recursive directory traversal with configurable depth
    - File type detection via extensions and content analysis
    - Batch processing with memory management
    - Parallel processing support with worker pools
    - Error isolation per file with detailed reporting
    """
    
    def __init__(self, batch_size: int = 100, max_workers: int = 4, 
                 logger: Optional[logging.Logger] = None):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger(__name__)
        
        # Supported file patterns
        self.supported_extensions = {
            '.tsp': 'TSP',
            '.vrp': 'VRP', 
            '.atsp': 'ATSP',
            '.hcp': 'HCP',
            '.sop': 'SOP',
            '.tour': 'TOUR'
        }
    
    def scan_directory(self, root_path: str, patterns: List[str] = None, 
                      max_depth: int = None) -> Iterator[List[Dict[str, Any]]]:
        """
        Scan directory and yield batches of file information.
        
        Yields:
            Batches of file dictionaries with metadata
        """
        # TODO: Implement recursive scanning with pathlib.Path.rglob()
        # Yield batches of file metadata dictionaries
        # Include: file_path, file_type, size, modification_time, validation_status
        pass
    
    def detect_file_type(self, file_path: Path) -> Optional[str]:
        """Detect TSPLIB file type from extension and content."""
        # TODO: Implement type detection
        # Check extension first, then validate with content sampling
        # Return problem type or None if not supported
        pass
    
    def validate_file_access(self, file_path: Path) -> List[str]:
        """Validate file is readable and non-empty."""
        # TODO: Implement file validation
        # Check: exists, readable, non-empty, size limits
        # Return list of validation errors
        pass
```

#### 2.2 Data Transformer

**Create `src/converter/core/transformer.py`** with complete normalization:

```python
from typing import Dict, Any, List, Optional
import logging
from tsplib95.models import StandardProblem

class DataTransformer:
    """
    Transform StandardProblem objects to normalized database format.
    
    Critical Requirements:
    - Convert 1-based TSPLIB indexing to 0-based database format
    - Handle all problem types with type-specific logic
    - Extract VRP demands and depot information correctly
    - Normalize coordinate systems and distance calculations
    - Maintain data integrity through validation
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def transform_problem(self, problem: StandardProblem, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform complete StandardProblem to normalized format.
        
        Returns structured data ready for database insertion:
        {
            'problem_data': {...},  # Basic metadata
            'nodes': [...],         # Normalized node data
            'edges': [...],         # Normalized edge data
            'tours': [...],         # Tour data if available
            'metadata': {...}       # Processing metadata
        }
        """
        # TODO: Implement complete transformation pipeline
        # Use problem.as_name_dict() for clean problem data
        # Call specialized methods for each component
        pass
    
    def extract_nodes_data(self, problem: StandardProblem) -> List[Dict[str, Any]]:
        """Extract and normalize node information."""
        # TODO: Implement node extraction
        # Handle: coordinates, demands, depot marking
        # Convert indices: keep original TSPLIB IDs, add normalized references
        pass
    
    def extract_edges_data(self, problem: StandardProblem) -> List[Dict[str, Any]]:
        """Extract edge weights with 0-based indexing."""
        # TODO: Implement edge extraction
        # Use problem.get_graph(normalize=True) for consistent indexing
        # Handle symmetric vs asymmetric storage
        pass
    
    def normalize_coordinates(self, coords: Dict[int, tuple]) -> List[Dict[str, Any]]:
        """Normalize coordinate data with proper indexing."""
        # TODO: Implement coordinate normalization
        # Handle 2D, 3D coordinates and missing values
        pass
    
    def process_vrp_specific_data(self, problem: StandardProblem) -> Dict[str, Any]:
        """Extract VRP-specific demands and depot information."""
        # TODO: Implement VRP data extraction
        # Use problem.demands and problem.depots attributes
        # Mark depot nodes and extract capacity constraints
        pass
```

#### 2.3 JSON Output

**Create `src/converter/output/json_writer.py`** with complete output system:

```python
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import gzip

class JSONWriter:
    """
    Write normalized problem data to flattened JSON structure.
    
    Requirements:
    - Generate consistent directory structure
    - Support optional compression for large files
    - Maintain schema validation
    - Provide readable formatting with metadata
    """
    
    def __init__(self, output_path: str, compress_large_files: bool = True,
                 logger: Optional[logging.Logger] = None):
        self.output_path = Path(output_path)
        self.compress_large_files = compress_large_files
        self.logger = logger or logging.getLogger(__name__)
        
        # Size threshold for compression (bytes)
        self.compression_threshold = 100 * 1024  # 100KB
    
    def write_problem(self, problem_data: Dict[str, Any]) -> str:
        """
        Write complete problem data to JSON file.
        
        Output structure:
        datasets/json/{type}/{problem_name}.json
        
        Returns:
            Path to written file
        """
        # TODO: Implement JSON writing with proper structure
        # Create type-based subdirectories
        # Generate readable JSON with consistent formatting
        # Apply compression for large files
        pass
    
    def create_output_structure(self):
        """Create directory structure for JSON output."""
        # TODO: Create directories for each problem type
        # Structure: json/tsp/, json/vrp/, json/atsp/, etc.
        pass
    
    def validate_json_schema(self, data: Dict[str, Any]) -> List[str]:
        """Validate output JSON structure."""
        # TODO: Implement schema validation
        # Check required fields and data types
        # Return validation errors
        pass
```

### Phase 3: Advanced Features

#### 3.1 Parallel Processing

**Create `src/converter/utils/parallel.py`** with production-ready concurrency:

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Iterator, Optional
import threading
import logging
from queue import Queue
import time

class ParallelProcessor:
    """
    Production-grade parallel processing for TSPLIB conversion.
    
    Requirements:
    - Thread-safe database connections with connection pooling
    - Memory-efficient batch processing with backpressure
    - Progress reporting with ETA calculations  
    - Error isolation with detailed failure tracking
    - Resource management with cleanup handling
    """
    
    def __init__(self, max_workers: int = 4, batch_size: int = 100,
                 memory_limit_mb: int = 2048, logger: Optional[logging.Logger] = None):
        self.max_workers = max_workers
        self.batch_size = batch_size 
        self.memory_limit_mb = memory_limit_mb
        self.logger = logger or logging.getLogger(__name__)
        
        # Progress tracking
        self._progress_queue = Queue()
        self._total_items = 0
        self._completed_items = 0
        self._failed_items = 0
    
    def process_files_parallel(self, file_list: List[str], 
                              process_func: Callable, **kwargs) -> Dict[str, Any]:
        """
        Process files in parallel with comprehensive error handling.
        
        Returns:
            {
                'successful': int,
                'failed': int, 
                'errors': List[Dict],
                'processing_time': float,
                'throughput': float  # files per second
            }
        """
        # TODO: Implement parallel file processing
        # Use ThreadPoolExecutor for I/O-bound tasks
        # Implement progress tracking and resource monitoring
        # Collect detailed error information for failed files
        pass
    
    def monitor_memory_usage(self) -> Dict[str, float]:
        """Monitor memory usage and trigger cleanup if needed."""
        # TODO: Implement memory monitoring
        # Return current usage stats and trigger cleanup at thresholds
        pass
    
    def create_progress_reporter(self) -> Callable:
        """Create thread-safe progress reporting function."""
        # TODO: Implement progress reporting
        # Return callable for updating progress from worker threads
        pass
```

#### 3.2 CLI Interface  

**Create `src/converter/cli/commands.py`** with complete CLI system:

```python
import click
from pathlib import Path
import logging
import yaml
from typing import Optional
import sys

from ..config import ConverterConfig, load_config
from ..core.scanner import FileScanner
from ..core.parser import TSPLIBParser
from ..database.operations import DatabaseManager
from ..utils.logging import setup_logging

@click.group()
@click.version_option()
def cli():
    """TSPLIB95 ETL Converter - Convert TSPLIB/VRP instances to JSON and DuckDB."""
    pass

@cli.command()
@click.option('--input', '-i', type=click.Path(exists=True), 
              help='Input directory containing TSPLIB files')
@click.option('--output', '-o', type=click.Path(), 
              help='Output directory for JSON and database')
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Configuration file path')
@click.option('--parallel/--no-parallel', default=True,
              help='Enable parallel processing')
@click.option('--batch-size', default=100, 
              help='Batch size for processing')
@click.option('--workers', default=4,
              help='Number of parallel workers')
@click.option('--types', multiple=True, 
              help='Problem types to process (TSP, VRP, etc.)')
@click.option('--force/--no-force', default=False,
              help='Force reprocessing of existing files')
def process(input, output, config, parallel, batch_size, workers, types, force):
    """
    Process TSPLIB files and generate JSON/database outputs.
    
    Examples:
        converter process -i datasets_raw/problems -o datasets/
        converter process --config config.yaml --parallel --workers 8
        converter process --types TSP --types VRP --force
    """
    # TODO: Implement complete process command
    # Load configuration, setup logging, initialize components
    # Create progress bar, process files, generate summary report
    pass

@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Configuration file to validate')
@click.option('--database', '-d', type=click.Path(exists=True),
              help='Database file to validate')
@click.option('--input-dir', '-i', type=click.Path(exists=True),
              help='Input directory to scan for issues')
def validate(config, database, input_dir):
    """
    Validate configuration, database integrity, and input files.
    
    Performs comprehensive validation:
    - Configuration file structure and values
    - Database schema and data integrity  
    - Input file accessibility and format
    - Dependency availability and versions
    """
    # TODO: Implement validation command
    # Run all validation checks and report detailed results
    pass

@cli.command()
@click.option('--database', '-d', required=True, type=click.Path(exists=True),
              help='Database file to analyze')
@click.option('--type', '-t', type=click.Choice(['TSP', 'VRP', 'ATSP', 'HCP', 'SOP', 'TOUR']),
              help='Filter by problem type')
@click.option('--output', '-o', type=click.File('w'), default=sys.stdout,
              help='Output file for analysis results')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), default='table',
              help='Output format')
def analyze(database, type, output, format):
    """
    Analyze processed problems and generate statistics.
    
    Generates comprehensive analysis:
    - Problem type distribution and size statistics
    - Processing success/failure rates
    - Database storage efficiency metrics
    - Data quality assessment reports
    """
    # TODO: Implement analysis command
    # Query database, generate statistics, format output
    pass

@cli.command()
@click.option('--output', '-o', type=click.Path(), default='config.yaml',
              help='Output path for configuration file')
def init(output):
    """Initialize configuration file with default settings."""
    # TODO: Implement configuration initialization
    # Generate template config.yaml with documented options
    pass

if __name__ == '__main__':
    cli()
```

#### 3.3 Update Functionality

**Create `src/converter/utils/update.py`** with incremental processing:

```python
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
import hashlib
from datetime import datetime

class UpdateManager:
    """
    Manage incremental updates and change detection.
    
    Requirements:
    - File modification time tracking
    - Content-based change detection via checksums
    - Database synchronization with conflict resolution
    - Backup and recovery for interrupted updates
    """
    
    def __init__(self, database_manager, logger: Optional[logging.Logger] = None):
        self.db_manager = database_manager
        self.logger = logger or logging.getLogger(__name__)
    
    def detect_changes(self, file_path: str) -> Dict[str, Any]:
        """
        Detect if file needs processing based on modification time and checksum.
        
        Returns:
            {
                'needs_update': bool,
                'change_type': str,  # 'new', 'modified', 'unchanged'
                'last_processed': datetime,
                'file_checksum': str
            }
        """
        # TODO: Implement change detection
        # Compare file modification time with database records
        # Use content checksums for reliable change detection
        pass
    
    def create_backup(self, problem_id: int) -> str:
        """Create backup of existing problem data before update."""
        # TODO: Implement backup creation
        # Export current database state for recovery
        pass
    
    def perform_incremental_update(self, file_list: List[str]) -> Dict[str, Any]:
        """Process only changed files with rollback capability."""
        # TODO: Implement incremental processing
        # Process only files that have changed since last run
        # Maintain transaction integrity across updates
        pass
```

## Critical Implementation Details & Configuration

### Configuration System

**Create `src/converter/config.py`**:

```python
import yaml
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, field

@dataclass
class ConverterConfig:
    # Input settings
    input_path: str = "./datasets_raw/problems"
    file_patterns: list = field(default_factory=lambda: ["*.tsp", "*.vrp", "*.atsp", "*.hcp", "*.sop", "*.tour"])
    
    # Output settings
    json_output_path: str = "./datasets/json"
    database_path: str = "./datasets/db/routing.duckdb"
    
    # Processing settings
    batch_size: int = 100
    max_workers: int = 4
    memory_limit_mb: int = 2048
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/converter.log"

def load_config(config_path: str = "config.yaml") -> ConverterConfig:
    """Load configuration from YAML file."""
    if Path(config_path).exists():
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return ConverterConfig(**config_dict)
    return ConverterConfig()
```

### Data Transformation Examples

**For Phase 2.2 - Critical transformation patterns**:

```python
def transform_problem_data(problem: StandardProblem) -> Dict[str, Any]:
    """Transform StandardProblem to database format."""
    
    # Get clean data (excludes defaults)
    base_data = problem.as_name_dict()
    
    # Extract node coordinates (convert 1-based to 0-based indexing)
    nodes = []
    if hasattr(problem, 'node_coords') and problem.node_coords:
        for node_id, coords in problem.node_coords.items():
            nodes.append({
                'node_id': node_id,  # Keep original 1-based ID
                'x': coords[0] if len(coords) > 0 else None,
                'y': coords[1] if len(coords) > 1 else None,
                'z': coords[2] if len(coords) > 2 else None,
                'demand': problem.demands.get(node_id, 0) if hasattr(problem, 'demands') else 0,
                'is_depot': node_id in (problem.depots or []) if hasattr(problem, 'depots') else False
            })
    
    # Extract edges with weights
    edges = []
    graph = problem.get_graph(normalize=True)  # This gives 0-based indexing
    for from_node, to_node, edge_data in graph.edges(data=True):
        edges.append({
            'from_node': from_node,  # Already 0-based
            'to_node': to_node,      # Already 0-based
            'weight': edge_data.get('weight', 0),
            'is_fixed': edge_data.get('is_fixed', False)
        })
    
    return {
        'problem_data': base_data,
        'nodes': nodes,
        'edges': edges
    }
```

### CLI Command Specifications

**For Phase 3.2 - Exact command interface**:

```python
# Expected CLI commands:
# python -m converter.cli process --input datasets_raw/problems --output datasets/ --config config.yaml
# python -m converter.cli validate --config config.yaml
# python -m converter.cli analyze --database datasets/db/routing.duckdb --type TSP

import click

@click.group()
def cli():
    """TSPLIB95 ETL Converter CLI."""
    pass

@cli.command()
@click.option('--input', '-i', help='Input directory path')
@click.option('--output', '-o', help='Output directory path') 
@click.option('--config', '-c', help='Configuration file path')
@click.option('--parallel/--no-parallel', default=True, help='Enable parallel processing')
def process(input, output, config, parallel):
    """Process TSPLIB files and generate outputs."""
    pass
```

### Essential Validation Rules

- **File validation**: Check file extensions, readable format, non-empty, size < 100MB
- **Data validation**: Verify dimension matches node count, coordinates are numeric
- **Type-specific validation**:
  - TSP: Symmetric distance matrix, single tour
  - VRP: Depot nodes marked, capacity constraints
  - ATSP: Asymmetric distances allowed
- **Memory validation**: Node count < 10,000 for single-threaded processing

### Key Implementation Points

- **Index Normalization**: TSPLIB uses 1-based indices, database stores 0-based
- **VRP Processing**: Extract demands/depots correctly using `problem.demands` and `problem.depots`
- **Special Distance Handling**: Use `special` parameter for `TYPE=SPECIAL` problems
- **Data Extraction**: Always use `StandardProblem.as_name_dict()` for clean data
- **Error Isolation**: One file's failure shouldn't stop batch processing
- **Type Annotations**: Add proper type hints and docstrings for all functions

## Testing Requirements with Specific Examples

**Create comprehensive test suite using pytest**:

```python
# tests/test_parser.py - Required test cases
def test_parser_basic_tsp():
    """Test parsing gr17.tsp from datasets_raw/problems/tsp/"""
    parser = TSPLIBParser()
    data = parser.parse_file('datasets_raw/problems/tsp/gr17.tsp')
    assert data['name'] == 'gr17'
    assert data['type'] == 'TSP'
    assert data['dimension'] == 17

def test_parser_vrp_with_demands():
    """Test VRP parsing with demand and depot extraction"""
    # Use actual VRP file from datasets_raw/problems/vrp/
    
def test_parser_special_distance():
    """Test handling of SPECIAL edge weight types"""
    # Test with XRAY problems that require special distance functions
    
def test_database_operations():
    """Test database CRUD operations"""
    db = DatabaseManager(':memory:')  # Use in-memory for tests
    problem_id = db.insert_problem({'name': 'test', 'type': 'TSP', 'dimension': 5})
    assert problem_id is not None

def test_transformer_index_normalization():
    """Test 1-based to 0-based index conversion"""
    # Verify node indexing conversion works correctly

def test_cli_process_command():
    """Test CLI process command with real arguments"""
    # Use click.testing.CliRunner to test CLI
```

## Integration Specifications & Complete Workflow

### Expected Agent Implementation Pattern

The agent must implement a **complete end-to-end workflow** by connecting these components:

```python
# Main processing workflow that agent must implement:
def main_conversion_workflow(input_dir: str, output_dir: str, config: ConverterConfig):
    """
    Complete ETL workflow that demonstrates all components working together.
    This is the integration test for the entire system.
    """
    # 1. Initialize components
    logger = setup_logging(config.log_level, config.log_file)
    scanner = FileScanner(config.batch_size, config.max_workers, logger)
    parser = TSPLIBParser(logger)
    transformer = DataTransformer(logger) 
    db_manager = DatabaseManager(config.database_path, logger)
    json_writer = JSONWriter(config.json_output_path, logger=logger)
    
    # 2. Discover and process files
    total_processed = 0
    total_errors = 0
    
    for file_batch in scanner.scan_directory(input_dir, config.file_patterns):
        for file_info in file_batch:
            try:
                # Parse TSPLIB file
                problem_data = parser.parse_file(file_info['file_path'])
                
                # Transform to normalized format  
                normalized_data = transformer.transform_problem(
                    problem_data, file_info
                )
                
                # Store in database
                problem_id = db_manager.insert_complete_problem(normalized_data)
                
                # Generate JSON output
                json_path = json_writer.write_problem(normalized_data)
                
                total_processed += 1
                logger.info(f"Successfully processed {file_info['file_path']}")
                
            except Exception as e:
                total_errors += 1
                logger.error(f"Failed to process {file_info['file_path']}: {e}")
    
    # 3. Generate summary report
    return {
        'total_processed': total_processed,
        'total_errors': total_errors,
        'database_path': config.database_path,
        'json_output_path': config.json_output_path
    }
```

### Required Files and Directory Structure

```text
src/converter/
├── __init__.py                  # Package initialization
├── config.py                    # Configuration management (COMPLETE)
├── main.py                      # Main workflow integration (AGENT MUST CREATE)
├── core/
│   ├── __init__.py
│   ├── parser.py                # TSPLIB95 integration (COMPLETE INTERFACE)
│   ├── scanner.py               # File discovery (COMPLETE INTERFACE)
│   └── transformer.py           # Data transformation (COMPLETE INTERFACE)
├── database/
│   ├── __init__.py
│   ├── schema.py                # Database schema (COMPLETE)
│   └── operations.py            # Database CRUD (COMPLETE INTERFACE)
├── output/
│   ├── __init__.py
│   └── json_writer.py           # JSON output (COMPLETE INTERFACE)
├── utils/
│   ├── __init__.py
│   ├── logging.py               # Logging setup (COMPLETE)
│   ├── exceptions.py            # Exception hierarchy (COMPLETE)
│   ├── validation.py            # Data validation (COMPLETE)
│   ├── parallel.py              # Parallel processing (COMPLETE INTERFACE)
│   └── update.py               # Update functionality (COMPLETE INTERFACE)
└── cli/
    ├── __init__.py
    └── commands.py              # CLI interface (COMPLETE INTERFACE)

# Additional required files:
config.yaml                      # Default configuration (AGENT MUST CREATE)
pyproject.toml                   # Update dependencies (AGENT MUST UPDATE)
tests/converter/                 # Test suite (AGENT MUST CREATE)
```

### Critical Integration Requirements

1. **End-to-End Testing**: Agent must create integration test that processes actual files from `datasets_raw/problems/tsp/gr17.tsp` through complete pipeline

2. **Error Recovery**: System must handle individual file failures without stopping batch processing

3. **Memory Management**: Large datasets must process within memory limits via streaming and batching

4. **Performance Validation**: Must process 100+ files within reasonable time limits  

5. **Data Validation**: Output JSON and database must contain valid, complete data that matches input files

### Success Validation Checklist

The agent implementation will be considered successful when:

- [ ] All TODO methods are implemented with working code (not placeholders)
- [ ] Integration test processes `gr17.tsp` through complete pipeline successfully  
- [ ] Database contains correct nodes/edges data with proper indexing
- [ ] JSON output matches expected flattened structure
- [ ] CLI commands execute without errors on sample data
- [ ] Parallel processing works with multiple files concurrently
- [ ] Error handling gracefully manages invalid or corrupt files
- [ ] Memory usage stays within configured limits during processing
- [ ] All unit tests pass with realistic test data

## Success Criteria Checklist

- [ ] All Phase 1-3 modules created and functional
- [ ] Can parse at least 5 different problem types (TSP, VRP, ATSP, HCP, SOP)
- [ ] Database schema created with all tables and indexes
- [ ] JSON output generates flattened structure
- [ ] CLI interface works with basic commands
- [ ] Parallel processing handles multiple files
- [ ] Error handling prevents crashes on invalid files
- [ ] Memory management works for large datasets
- [ ] Unit tests cover core functionality
- [ ] Can process entire `datasets_raw/problems/` directory

## Critical References (Read These First!)

- **`.github/copilot-instructions.md`** - Complete project guidance and conventions
- **`docs/implementation-plan.md`** - Detailed phase breakdown and requirements  
- **`docs/diagrams/converter-architecture.mmd`** - System architecture and data flow
- **`docs/diagrams/database-schema.mmd`** - Complete database schema with relationships
- **`docs/diagrams/database-queries.mmd`** - Query patterns and optimization strategies
- **`src/tsplib95/`** - Study vendored library for API understanding

## Expected Deliverables

This implementation should provide a complete ETL pipeline that:

1. **Discovers and processes** all files in `datasets_raw/problems/`
2. **Generates structured JSON** in `datasets/json/` with flattened format
3. **Creates DuckDB database** at `datasets/db/routing.duckdb` with normalized schema
4. **Provides CLI interface** for processing, validation, and analysis
5. **Handles parallel processing** for performance with large datasets
6. **Includes comprehensive error handling** and logging
7. **Supports incremental updates** and change detection
8. **Maintains data integrity** throughout the pipeline

The agent should work autonomously overnight and create a pull request with the complete implementation of phases 1-3, ready for review and integration.
