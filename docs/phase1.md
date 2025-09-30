# GitHub Issue Title: Implement TSPLIB95 ETL System - Phase 1 Core Infrastructure

## Issue Description

@copilot #github-pull-request_copilot-coding-agent

We need to implement **Phase 1 only** of our TSPLIB95 ETL system - the core infrastructure foundation that enables parsing TSPLIB files and storing them in a DuckDB database. This focused scope ensures a high-quality, complete implementation that provides a solid foundation for future phases.

### Project Background

- Repository contains a vendored copy of `tsplib95` library under `src/tsplib95/`
- Raw TSPLIB/VRP files are located in `datasets_raw/problems/{tsp,vrp,atsp,hcp,sop,tour}/`  
- Target database: `datasets/db/routing.duckdb` (DuckDB database)
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

## Phase 1 Implementation Requirements

### 1.1 Project Setup & Utilities

**Create `src/converter/__init__.py`**:

```python
"""TSPLIB95 ETL Converter - Phase 1 Core Infrastructure."""
__version__ = "0.1.0"
```

**Create `src/converter/utils/logging.py`**:

```python
import logging
import sys
from typing import Optional
from pathlib import Path

def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Configure logging with file and console handlers."""
    logger = logging.getLogger("converter")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
```

**Create `src/converter/utils/exceptions.py`**:

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

**Create `src/converter/utils/validation.py`**:

```python
from typing import Dict, Any, List

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
    if not coords:
        return True  # Empty coordinates are valid
    
    return all(
        isinstance(coord, (tuple, list)) and len(coord) >= 2 and 
        all(isinstance(x, (int, float)) for x in coord[:2])
        for coord in coords
    )

def validate_file_path(file_path: str) -> List[str]:
    """Validate file accessibility and basic properties."""
    errors = []
    from pathlib import Path
    
    path = Path(file_path)
    if not path.exists():
        errors.append(f"File does not exist: {file_path}")
    elif not path.is_file():
        errors.append(f"Path is not a file: {file_path}")
    elif path.stat().st_size == 0:
        errors.append(f"File is empty: {file_path}")
    elif path.stat().st_size > 100 * 1024 * 1024:  # 100MB limit
        errors.append(f"File too large (>100MB): {file_path}")
    
    return errors
```

### 1.2 TSPLIB95 Parser Integration

**Create `src/converter/core/parser.py`**:

```python
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple
import logging

from tsplib95 import loaders
from tsplib95.models import StandardProblem
from ..utils.exceptions import ParsingError, ValidationError
from ..utils.validation import validate_problem_data, validate_file_path

class TSPLIBParser:
    """
    Parser for TSPLIB format files with complete extraction capabilities.
    
    This is the core component that integrates with the vendored tsplib95 library
    to parse TSPLIB files and extract normalized data for database storage.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def parse_file(self, file_path: str, special_func: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Parse TSPLIB file and return complete normalized data structure.
        
        Args:
            file_path: Path to TSPLIB file
            special_func: Custom distance function for SPECIAL edge weight types
            
        Returns:
            Complete problem data ready for database insertion:
            {
                'problem_data': Dict[str, Any],  # Basic problem metadata
                'nodes': List[Dict[str, Any]],   # Node coordinates and properties
                'edges': List[Dict[str, Any]],   # Edge weights and properties 
                'metadata': Dict[str, Any]       # File and processing metadata
            }
        """
        # Validate file first
        file_errors = validate_file_path(file_path)
        if file_errors:
            raise ParsingError(file_path, f"File validation failed: {'; '.join(file_errors)}")
        
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
                'metadata': self._extract_metadata(problem, file_path)
            }
            
            self.logger.info(f"Successfully parsed {file_path}: {result['problem_data'].get('type')} "
                           f"with {len(result['nodes'])} nodes, {len(result['edges'])} edges")
            return result
            
        except Exception as e:
            if isinstance(e, ParsingError):
                raise
            raise ParsingError(file_path, str(e))
    
    def _extract_problem_data(self, problem: StandardProblem) -> Dict[str, Any]:
        """Extract basic problem metadata using as_name_dict() for clean data."""
        # Get clean data (excludes defaults)
        data = problem.as_name_dict()
        
        # Ensure required fields are present
        if 'name' not in data:
            data['name'] = getattr(problem, 'name', 'unknown')
        if 'type' not in data:
            data['type'] = getattr(problem, 'type', 'UNKNOWN')
        if 'dimension' not in data:
            data['dimension'] = getattr(problem, 'dimension', 0)
            
        return data
    
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
        nodes = []
        
        # Get coordinates if available
        coords = getattr(problem, 'node_coords', None) or {}
        demands = getattr(problem, 'demands', None) or {}
        depots = getattr(problem, 'depots', None) or []
        display_coords = getattr(problem, 'display_data', None) or {}
        
        # Process all nodes (use dimension as reference)
        dimension = getattr(problem, 'dimension', len(coords)) if coords else 0
        
        for node_id in range(1, dimension + 1):
            coord = coords.get(node_id, [])
            display_coord = display_coords.get(node_id, [])
            
            node_data = {
                'node_id': node_id,  # Keep original 1-based TSPLIB ID
                'x': coord[0] if len(coord) > 0 else None,
                'y': coord[1] if len(coord) > 1 else None,
                'z': coord[2] if len(coord) > 2 else None,
                'demand': demands.get(node_id, 0),
                'is_depot': node_id in depots,
                'display_x': display_coord[0] if len(display_coord) > 0 else None,
                'display_y': display_coord[1] if len(display_coord) > 1 else None
            }
            nodes.append(node_data)
        
        return nodes
    
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
        edges = []
        
        try:
            # Get normalized graph (0-based indexing)
            graph = problem.get_graph(normalize=True)
            
            # Extract edges from graph
            for from_node, to_node, edge_data in graph.edges(data=True):
                edge = {
                    'from_node': from_node,  # Already 0-based from normalize=True
                    'to_node': to_node,      # Already 0-based from normalize=True
                    'weight': edge_data.get('weight', 0.0),
                    'is_fixed': edge_data.get('is_fixed', False)
                }
                edges.append(edge)
                
        except Exception as e:
            self.logger.warning(f"Could not extract edges from graph: {e}")
            # For some problem types, edges might not be available
            
        return edges
    
    def _extract_metadata(self, problem: StandardProblem, file_path: str) -> Dict[str, Any]:
        """Extract comprehensive file and processing metadata."""
        file_path_obj = Path(file_path)
        
        return {
            'file_path': str(file_path),
            'file_size': file_path_obj.stat().st_size if file_path_obj.exists() else 0,
            'file_name': file_path_obj.name,
            'problem_source': file_path_obj.parent.name,
            'has_coordinates': hasattr(problem, 'node_coords') and bool(getattr(problem, 'node_coords', None)),
            'has_demands': hasattr(problem, 'demands') and bool(getattr(problem, 'demands', None)),
            'has_depots': hasattr(problem, 'depots') and bool(getattr(problem, 'depots', None)),
            'edge_weight_type': getattr(problem, 'edge_weight_type', None),
            'edge_weight_format': getattr(problem, 'edge_weight_format', None)
        }
    
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
                coord_count = len(problem.node_coords)
                if coord_count > 0 and coord_count != problem.dimension:
                    errors.append(f"Node coordinate count {coord_count} "
                                f"doesn't match dimension {problem.dimension}")
        
        if errors:
            raise ValidationError(f"Validation errors: {'; '.join(errors)}")
    
    def detect_special_distance_type(self, file_path: str) -> bool:
        """Detect if file requires special distance function."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().upper()
                return 'EDGE_WEIGHT_TYPE' in content and 'SPECIAL' in content
        except Exception:
            return False
```

### 1.3 Database Foundation

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
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE,
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
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE,
    UNIQUE(problem_id, from_node, to_node)
);
"""

# Performance indexes
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_problems_type_dimension ON problems(type, dimension);",
    "CREATE INDEX IF NOT EXISTS idx_problems_name ON problems(name);",
    "CREATE INDEX IF NOT EXISTS idx_nodes_problem_id ON nodes(problem_id);",
    "CREATE INDEX IF NOT EXISTS idx_nodes_problem_node ON nodes(problem_id, node_id);",
    "CREATE INDEX IF NOT EXISTS idx_edges_problem_id ON edges(problem_id);",
    "CREATE INDEX IF NOT EXISTS idx_edges_from_to ON edges(problem_id, from_node, to_node);",
    "CREATE INDEX IF NOT EXISTS idx_nodes_depot ON nodes(problem_id, is_depot) WHERE is_depot = TRUE;",
]

def get_schema_version() -> str:
    """Get current schema version."""
    return "1.0.0"

def get_all_table_creation_sql() -> List[str]:
    """Get all SQL statements for table creation."""
    return [
        CREATE_PROBLEMS_TABLE,
        CREATE_NODES_TABLE,
        CREATE_EDGES_TABLE
    ] + CREATE_INDEXES
```

**Create `src/converter/database/operations.py`**:

```python
import duckdb
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

from .schema import get_all_table_creation_sql
from ..utils.exceptions import DatabaseError

class DatabaseManager:
    """
    Complete database management for TSPLIB converter Phase 1.
    
    Provides core CRUD operations with proper error handling and transaction management.
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
                # Execute all schema creation SQL
                for sql in get_all_table_creation_sql():
                    conn.execute(sql)
                
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
                - 'metadata': File metadata
                
        Returns:
            problem_id: Database ID of inserted problem
        """
        try:
            with duckdb.connect(str(self.db_path)) as conn:
                conn.execute("BEGIN TRANSACTION")
                
                try:
                    # Insert problem and get ID
                    problem_id = self._insert_problem_data(conn, problem_data['problem_data'], problem_data['metadata'])
                    
                    # Insert nodes if present
                    if problem_data.get('nodes'):
                        self._bulk_insert_nodes(conn, problem_id, problem_data['nodes'])
                    
                    # Insert edges if present  
                    if problem_data.get('edges'):
                        self._bulk_insert_edges(conn, problem_id, problem_data['edges'])
                    
                    conn.execute("COMMIT")
                    
                    self.logger.info(f"Successfully inserted problem ID {problem_id} with "
                                   f"{len(problem_data.get('nodes', []))} nodes, "
                                   f"{len(problem_data.get('edges', []))} edges")
                    
                    return problem_id
                    
                except Exception as e:
                    conn.execute("ROLLBACK")
                    raise e
                
        except Exception as e:
            raise DatabaseError(f"Complete problem insertion failed: {e}")
    
    def _insert_problem_data(self, conn, problem_data: Dict[str, Any], metadata: Dict[str, Any]) -> int:
        """Insert problem metadata and return ID."""
        # Handle conflict resolution with UPSERT
        result = conn.execute("""
            INSERT INTO problems (
                name, type, comment, dimension, capacity, 
                edge_weight_type, edge_weight_format, 
                node_coord_type, display_data_type, 
                file_path, file_size
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (name) DO UPDATE SET
                updated_at = CURRENT_TIMESTAMP,
                file_path = excluded.file_path,
                file_size = excluded.file_size,
                type = excluded.type,
                dimension = excluded.dimension,
                capacity = excluded.capacity,
                edge_weight_type = excluded.edge_weight_type,
                edge_weight_format = excluded.edge_weight_format
            RETURNING id;
        """, [
            problem_data.get('name'),
            problem_data.get('type'),
            problem_data.get('comment'),
            problem_data.get('dimension'),
            problem_data.get('capacity'),
            problem_data.get('edge_weight_type'),
            problem_data.get('edge_weight_format'),
            problem_data.get('node_coord_type'),
            problem_data.get('display_data_type'),
            metadata.get('file_path'),
            metadata.get('file_size', 0)
        ]).fetchone()
        
        if not result:
            raise DatabaseError("Failed to insert problem - no ID returned")
        
        return result[0]
    
    def _bulk_insert_nodes(self, conn, problem_id: int, nodes_data: List[Dict[str, Any]]):
        """Bulk insert nodes using prepared statements for performance."""
        # Clear existing nodes for this problem first
        conn.execute("DELETE FROM nodes WHERE problem_id = ?", [problem_id])
        
        # Prepare bulk insert
        if nodes_data:
            values = []
            for node in nodes_data:
                values.append([
                    problem_id,
                    node.get('node_id'),
                    node.get('x'),
                    node.get('y'),
                    node.get('z'),
                    node.get('demand', 0),
                    node.get('is_depot', False),
                    node.get('display_x'),
                    node.get('display_y')
                ])
            
            conn.executemany("""
                INSERT INTO nodes (problem_id, node_id, x, y, z, 
                                 demand, is_depot, display_x, display_y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
    
    def _bulk_insert_edges(self, conn, problem_id: int, edges_data: List[Dict[str, Any]]):
        """Bulk insert edges with conflict resolution."""
        # Clear existing edges for this problem first
        conn.execute("DELETE FROM edges WHERE problem_id = ?", [problem_id])
        
        # Prepare bulk insert
        if edges_data:
            values = []
            for edge in edges_data:
                values.append([
                    problem_id,
                    edge.get('from_node'),
                    edge.get('to_node'),
                    edge.get('weight', 0.0),
                    edge.get('is_fixed', False)
                ])
            
            conn.executemany("""
                INSERT INTO edges (problem_id, from_node, to_node, weight, is_fixed)
                VALUES (?, ?, ?, ?, ?)
            """, values)
    
    def get_problem_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get problem data by name."""
        try:
            with duckdb.connect(str(self.db_path)) as conn:
                result = conn.execute("""
                    SELECT * FROM problems WHERE name = ?
                """, [name]).fetchone()
                
                if result:
                    # Convert to dictionary (DuckDB returns tuples)
                    columns = [desc[0] for desc in conn.description]
                    return dict(zip(columns, result))
                
                return None
        except Exception as e:
            raise DatabaseError(f"Failed to get problem by name {name}: {e}")
    
    def get_problem_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        try:
            with duckdb.connect(str(self.db_path)) as conn:
                # Total problems by type
                type_stats = conn.execute("""
                    SELECT type, COUNT(*) as count, AVG(dimension) as avg_dimension, 
                           MAX(dimension) as max_dimension
                    FROM problems 
                    GROUP BY type
                    ORDER BY count DESC
                """).fetchall()
                
                # Overall statistics
                overall = conn.execute("""
                    SELECT COUNT(*) as total_problems, 
                           SUM((SELECT COUNT(*) FROM nodes WHERE nodes.problem_id = problems.id)) as total_nodes,
                           SUM((SELECT COUNT(*) FROM edges WHERE edges.problem_id = problems.id)) as total_edges
                    FROM problems
                """).fetchone()
                
                return {
                    'total_problems': overall[0] if overall else 0,
                    'total_nodes': overall[1] if overall else 0,
                    'total_edges': overall[2] if overall else 0,
                    'by_type': [
                        {'type': row[0], 'count': row[1], 'avg_dimension': row[2], 'max_dimension': row[3]}
                        for row in type_stats
                    ]
                }
        except Exception as e:
            raise DatabaseError(f"Failed to get statistics: {e}")
    
    def validate_data_integrity(self) -> List[str]:
        """
        Validate database integrity and return list of issues.
        """
        issues = []
        
        try:
            with duckdb.connect(str(self.db_path)) as conn:
                # Check for problems without nodes
                result = conn.execute("""
                    SELECT name FROM problems p 
                    WHERE p.dimension > 0 AND 
                          (SELECT COUNT(*) FROM nodes n WHERE n.problem_id = p.id) = 0
                """).fetchall()
                
                for row in result:
                    issues.append(f"Problem '{row[0]}' has dimension > 0 but no nodes")
                
                # Check dimension consistency
                result = conn.execute("""
                    SELECT p.name, p.dimension, COUNT(n.id) as node_count
                    FROM problems p
                    LEFT JOIN nodes n ON p.id = n.problem_id
                    WHERE p.dimension > 0
                    GROUP BY p.id, p.name, p.dimension
                    HAVING COUNT(n.id) != p.dimension AND COUNT(n.id) > 0
                """).fetchall()
                
                for row in result:
                    issues.append(f"Problem '{row[0]}' dimension {row[1]} != node count {row[2]}")
        
        except Exception as e:
            issues.append(f"Integrity check failed: {e}")
        
        return issues
    
    def get_connection(self):
        """Get database connection for custom queries."""
        return duckdb.connect(str(self.db_path))
```

### 1.4 Configuration System

**Create `src/converter/config.py`**:

```python
import yaml
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, field

@dataclass
class ConverterConfig:
    """Configuration for TSPLIB converter."""
    # Input settings
    input_path: str = "./datasets_raw/problems"
    file_patterns: List[str] = field(default_factory=lambda: ["*.tsp", "*.vrp", "*.atsp", "*.hcp", "*.sop", "*.tour"])
    
    # Output settings  
    database_path: str = "./datasets/db/routing.duckdb"
    
    # Processing settings
    batch_size: int = 100
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/converter.log"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'input_path': self.input_path,
            'file_patterns': self.file_patterns,
            'database_path': self.database_path,
            'batch_size': self.batch_size,
            'log_level': self.log_level,
            'log_file': self.log_file
        }

def load_config(config_path: str = "config.yaml") -> ConverterConfig:
    """Load configuration from YAML file."""
    if Path(config_path).exists():
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Handle missing keys gracefully
        valid_config = {}
        default_config = ConverterConfig()
        
        for key, default_value in default_config.to_dict().items():
            valid_config[key] = config_dict.get(key, default_value)
            
        return ConverterConfig(**valid_config)
    
    return ConverterConfig()

def save_config(config: ConverterConfig, config_path: str = "config.yaml"):
    """Save configuration to YAML file."""
    config_path_obj = Path(config_path)
    config_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        yaml.safe_dump(config.to_dict(), f, default_flow_style=False, indent=2)
```

## Phase 1 Integration & Testing

### Complete Integration Test

**Create `tests/test_phase1_integration.py`**:

```python
import pytest
import tempfile
from pathlib import Path

from src.converter.core.parser import TSPLIBParser
from src.converter.database.operations import DatabaseManager
from src.converter.config import ConverterConfig
from src.converter.utils.logging import setup_logging

def test_complete_phase1_workflow():
    """
    End-to-end test of Phase 1 functionality using gr17.tsp.
    This test validates that all components work together correctly.
    """
    # Setup
    test_file = Path("datasets_raw/problems/tsp/gr17.tsp")
    if not test_file.exists():
        pytest.skip("Test file gr17.tsp not found")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Configure components
        config = ConverterConfig(
            database_path=f"{temp_dir}/test.duckdb",
            log_level="DEBUG"
        )
        
        logger = setup_logging(config.log_level)
        parser = TSPLIBParser(logger)
        db_manager = DatabaseManager(config.database_path, logger)
        
        # Parse file
        problem_data = parser.parse_file(str(test_file))
        
        # Validate parsed data structure
        assert 'problem_data' in problem_data
        assert 'nodes' in problem_data
        assert 'edges' in problem_data
        assert 'metadata' in problem_data
        
        # Validate problem data
        assert problem_data['problem_data']['name'] == 'gr17'
        assert problem_data['problem_data']['type'] == 'TSP'
        assert problem_data['problem_data']['dimension'] == 17
        
        # Validate nodes
        assert len(problem_data['nodes']) == 17
        assert all('node_id' in node for node in problem_data['nodes'])
        assert all('x' in node and 'y' in node for node in problem_data['nodes'])
        
        # Insert into database
        problem_id = db_manager.insert_complete_problem(problem_data)
        assert problem_id is not None
        assert problem_id > 0
        
        # Validate database content
        retrieved_problem = db_manager.get_problem_by_name('gr17')
        assert retrieved_problem is not None
        assert retrieved_problem['name'] == 'gr17'
        assert retrieved_problem['dimension'] == 17
        
        # Validate statistics
        stats = db_manager.get_problem_statistics()
        assert stats['total_problems'] == 1
        assert stats['total_nodes'] == 17
        
        # Validate integrity
        issues = db_manager.validate_data_integrity()
        assert len(issues) == 0, f"Integrity issues found: {issues}"
        
        logger.info("Phase 1 integration test completed successfully!")

def test_parser_error_handling():
    """Test parser error handling with invalid files."""
    logger = setup_logging("DEBUG")
    parser = TSPLIBParser(logger)
    
    # Test non-existent file
    with pytest.raises(Exception):
        parser.parse_file("nonexistent.tsp")
    
    # Test empty file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tsp', delete=False) as f:
        f.write("")
        f.flush()
        
        with pytest.raises(Exception):
            parser.parse_file(f.name)
        
        Path(f.name).unlink()

def test_database_operations():
    """Test database operations independently."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = f"{temp_dir}/test.duckdb"
        db_manager = DatabaseManager(db_path)
        
        # Test problem insertion
        test_data = {
            'problem_data': {
                'name': 'test_problem',
                'type': 'TSP',
                'dimension': 3,
                'comment': 'Test problem'
            },
            'nodes': [
                {'node_id': 1, 'x': 0.0, 'y': 0.0, 'demand': 0, 'is_depot': False},
                {'node_id': 2, 'x': 1.0, 'y': 1.0, 'demand': 0, 'is_depot': False},
                {'node_id': 3, 'x': 2.0, 'y': 0.0, 'demand': 0, 'is_depot': False}
            ],
            'edges': [
                {'from_node': 0, 'to_node': 1, 'weight': 1.414, 'is_fixed': False},
                {'from_node': 1, 'to_node': 2, 'weight': 1.414, 'is_fixed': False},
                {'from_node': 2, 'to_node': 0, 'weight': 2.0, 'is_fixed': False}
            ],
            'metadata': {
                'file_path': 'test.tsp',
                'file_size': 100
            }
        }
        
        problem_id = db_manager.insert_complete_problem(test_data)
        assert problem_id > 0
        
        # Test retrieval
        problem = db_manager.get_problem_by_name('test_problem')
        assert problem is not None
        assert problem['name'] == 'test_problem'
        assert problem['dimension'] == 3
```

### Simple CLI Interface  

**Create `src/converter/cli/commands.py`**:

```python
import click
from pathlib import Path
import logging
import sys

from ..config import ConverterConfig, load_config, save_config
from ..core.parser import TSPLIBParser
from ..database.operations import DatabaseManager
from ..utils.logging import setup_logging

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """TSPLIB95 ETL Converter - Phase 1 Core Infrastructure."""
    pass

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
@click.option('--output-db', '-o', help='Output database path')
def parse(file_path, config, output_db):
    """
    Parse a single TSPLIB file and store in database.
    
    Example: converter parse datasets_raw/problems/tsp/gr17.tsp
    """
    # Load configuration
    if config:
        converter_config = load_config(config)
    else:
        converter_config = ConverterConfig()
    
    if output_db:
        converter_config.database_path = output_db
    
    # Setup logging
    logger = setup_logging(converter_config.log_level, converter_config.log_file)
    
    try:
        # Initialize components
        parser = TSPLIBParser(logger)
        db_manager = DatabaseManager(converter_config.database_path, logger)
        
        # Parse file
        click.echo(f"Parsing {file_path}...")
        problem_data = parser.parse_file(file_path)
        
        # Insert into database
        problem_id = db_manager.insert_complete_problem(problem_data)
        
        # Report results
        click.echo(f"✓ Successfully processed {file_path}")
        click.echo(f"  Problem: {problem_data['problem_data']['name']} ({problem_data['problem_data']['type']})")
        click.echo(f"  Dimension: {problem_data['problem_data']['dimension']}")
        click.echo(f"  Nodes: {len(problem_data['nodes'])}")
        click.echo(f"  Edges: {len(problem_data['edges'])}")
        click.echo(f"  Database ID: {problem_id}")
        click.echo(f"  Database: {converter_config.database_path}")
        
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        click.echo(f"✗ Error processing {file_path}: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
def stats(config):
    """Show database statistics."""
    # Load configuration
    if config:
        converter_config = load_config(config)
    else:
        converter_config = ConverterConfig()
    
    # Setup logging
    logger = setup_logging(converter_config.log_level)
    
    try:
        db_manager = DatabaseManager(converter_config.database_path, logger)
        statistics = db_manager.get_problem_statistics()
        
        click.echo("Database Statistics:")
        click.echo(f"  Total Problems: {statistics['total_problems']}")
        click.echo(f"  Total Nodes: {statistics['total_nodes']}")
        click.echo(f"  Total Edges: {statistics['total_edges']}")
        
        if statistics['by_type']:
            click.echo("\nBy Problem Type:")
            for type_stat in statistics['by_type']:
                click.echo(f"  {type_stat['type']}: {type_stat['count']} problems "
                          f"(avg dimension: {type_stat['avg_dimension']:.1f})")
                
    except Exception as e:
        click.echo(f"✗ Error getting statistics: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
def validate(config):
    """Validate database integrity."""
    # Load configuration
    if config:
        converter_config = load_config(config)
    else:
        converter_config = ConverterConfig()
    
    logger = setup_logging(converter_config.log_level)
    
    try:
        db_manager = DatabaseManager(converter_config.database_path, logger)
        issues = db_manager.validate_data_integrity()
        
        if not issues:
            click.echo("✓ Database integrity validation passed")
        else:
            click.echo("✗ Database integrity issues found:")
            for issue in issues:
                click.echo(f"  - {issue}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ Error validating database: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--output', '-o', default='config.yaml', help='Output configuration file path')
def init(output):
    """Initialize configuration file with default settings."""
    config = ConverterConfig()
    save_config(config, output)
    click.echo(f"Configuration file created: {output}")

if __name__ == '__main__':
    cli()
```

## Required Directory Structure & Files

Create this exact directory structure:

```tree
src/converter/
├── __init__.py                  # Package initialization
├── config.py                    # Configuration management
├── core/
│   ├── __init__.py
│   └── parser.py                # TSPLIB95 parser integration
├── database/
│   ├── __init__.py
│   ├── schema.py                # Database schema definitions
│   └── operations.py            # Database CRUD operations
├── utils/
│   ├── __init__.py
│   ├── logging.py               # Logging setup
│   ├── exceptions.py            # Exception hierarchy
│   └── validation.py            # Data validation functions
└── cli/
    ├── __init__.py
    └── commands.py              # CLI interface

tests/
└── test_phase1_integration.py  # Integration test

config.yaml                      # Default configuration file
```

## Success Criteria

Phase 1 is complete when:

- [ ] All modules are created with working implementations (no TODO placeholders)
- [ ] Integration test `test_complete_phase1_workflow()` passes using `gr17.tsp`
- [ ] CLI commands work: `converter parse`, `converter stats`, `converter validate`
- [ ] Database contains correct problem, node, and edge data with proper indexing
- [ ] Error handling gracefully manages invalid files
- [ ] Configuration system loads and saves settings correctly
- [ ] All unit tests pass with realistic test data

## Validation Commands

After implementation, test with these commands:

```bash
# Test parsing a single file
python -m src.converter.cli.commands parse datasets_raw/problems/tsp/gr17.tsp

# Check database statistics
python -m src.converter.cli.commands stats

# Validate database integrity  
python -m src.converter.cli.commands validate

# Run integration tests
pytest tests/test_phase1_integration.py -v
```

## Critical Success Factors

1. **Complete Implementation**: All TODO methods must have working code, not placeholders
2. **Real Data Testing**: Must work with actual `gr17.tsp` file from the repository
3. **Error Recovery**: Individual component failures should not crash the system
4. **Data Integrity**: Database content must accurately represent the parsed TSPLIB data
5. **Validation**: Integration test must pass completely demonstrating end-to-end functionality

This Phase 1 implementation provides a solid, working foundation that can be confidently extended to Phases 2-3 by human developers or future agent iterations.
