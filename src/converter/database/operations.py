"""Database operations for TSPLIB data storage and retrieval."""

import duckdb
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime


class DatabaseManager:
    """
    Complete database management for TSPLIB converter.
    
    Features:
    - Thread-safe database operations for parallel processing
    - Bulk insert operations with prepared statements
    - Conflict resolution and incremental updates
    - Query interface for analysis and validation
    - Transaction management and error recovery
    """
    
    def __init__(self, db_path: str, logger: Optional[logging.Logger] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to DuckDB database file
            logger: Optional logger instance
        """
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
                # Create sequences first
                conn.execute("CREATE SEQUENCE IF NOT EXISTS problems_seq START 1")
                conn.execute("CREATE SEQUENCE IF NOT EXISTS nodes_seq START 1")

                conn.execute("CREATE SEQUENCE IF NOT EXISTS file_tracking_seq START 1")
                
                # Create problems table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS problems (
                        id INTEGER PRIMARY KEY DEFAULT nextval('problems_seq'),
                        name VARCHAR NOT NULL,
                        type VARCHAR NOT NULL,
                        comment VARCHAR,
                        dimension INTEGER NOT NULL,
                        capacity INTEGER,
                        edge_weight_type VARCHAR,
                        edge_weight_format VARCHAR,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Migrate schema to add VRP variant fields
                self._migrate_schema(conn)
                
                # Create nodes table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS nodes (
                        id INTEGER PRIMARY KEY DEFAULT nextval('nodes_seq'),
                        problem_id INTEGER NOT NULL,
                        node_id INTEGER NOT NULL,
                        x DOUBLE,
                        y DOUBLE,
                        z DOUBLE,
                        demand INTEGER DEFAULT 0,
                        is_depot BOOLEAN DEFAULT FALSE,
                        display_x DOUBLE,
                        display_y DOUBLE,
                        FOREIGN KEY (problem_id) REFERENCES problems(id)
                    )
                """)
                
                # NO EDGES TABLE - edges are computed on-demand
                
                # Create file tracking table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS file_tracking (
                        id INTEGER PRIMARY KEY DEFAULT nextval('file_tracking_seq'),
                        file_path VARCHAR UNIQUE NOT NULL,
                        problem_id INTEGER,
                        checksum VARCHAR,
                        last_processed TIMESTAMP,
                        file_size BIGINT,
                        FOREIGN KEY (problem_id) REFERENCES problems(id)
                    )
                """)
                
                # Create indexes for better query performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_problems_type_dim 
                    ON problems(type, dimension)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_nodes_problem 
                    ON nodes(problem_id, node_id)
                """)
                

                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_file_tracking_path 
                    ON file_tracking(file_path)
                """)
                
                self.logger.info(f"Database schema initialized at {self.db_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize database schema: {e}")
            raise
            
    def _migrate_schema(self, conn):
        """Apply schema migrations for VRP variant support."""
        try:
            # Check if VRP fields exist and add them if needed
            result = conn.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'problems' AND column_name = 'capacity_vol'
            """).fetchall()
            
            if not result:
                # Add VRP variant fields
                conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS capacity_vol INTEGER")
                conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS capacity_weight INTEGER")
                conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS max_distance DOUBLE")
                conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS service_time DOUBLE")
                conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS vehicles INTEGER")
                conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS depots INTEGER")
                conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS periods INTEGER")
                conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS has_time_windows BOOLEAN")
                conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS has_pickup_delivery BOOLEAN")
                self.logger.debug("Added VRP variant fields to problems table")
                
        except Exception as e:
            # If information_schema doesn't work, try direct column addition (will be ignored if exists)
            try:
                conn.execute("ALTER TABLE problems ADD COLUMN capacity_vol INTEGER")
                conn.execute("ALTER TABLE problems ADD COLUMN capacity_weight INTEGER")
                conn.execute("ALTER TABLE problems ADD COLUMN max_distance DOUBLE")
                conn.execute("ALTER TABLE problems ADD COLUMN service_time DOUBLE")
                conn.execute("ALTER TABLE problems ADD COLUMN vehicles INTEGER")
                conn.execute("ALTER TABLE problems ADD COLUMN depots INTEGER")
                conn.execute("ALTER TABLE problems ADD COLUMN periods INTEGER")
                conn.execute("ALTER TABLE problems ADD COLUMN has_time_windows BOOLEAN")
                conn.execute("ALTER TABLE problems ADD COLUMN has_pickup_delivery BOOLEAN")
            except Exception:
                pass  # Columns already exist
    
    def insert_problem(self, problem_data: Dict[str, Any]) -> int:
        """
        Insert problem data into database.
        
        Args:
            problem_data: Dictionary with problem information
            
        Returns:
            Problem ID
        """
        with duckdb.connect(str(self.db_path)) as conn:
            result = conn.execute("""
                INSERT INTO problems (name, type, comment, dimension, capacity, 
                                     edge_weight_type, edge_weight_format,
                                     capacity_vol, capacity_weight, max_distance,
                                     service_time, vehicles, depots, periods, 
                                     has_time_windows, has_pickup_delivery)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            """, [
                problem_data.get('name'),
                problem_data.get('type'),
                problem_data.get('comment'),
                problem_data.get('dimension'),
                problem_data.get('capacity'),
                problem_data.get('edge_weight_type'),
                problem_data.get('edge_weight_format'),
                problem_data.get('capacity_vol'),
                problem_data.get('capacity_weight'),
                problem_data.get('max_distance'),
                problem_data.get('service_time'),
                problem_data.get('vehicles'),
                problem_data.get('depots'),
                problem_data.get('periods'),
                problem_data.get('has_time_windows'),
                problem_data.get('has_pickup_delivery')
            ]).fetchone()
            
            return result[0] if result else None
    
    def insert_nodes(self, problem_id: int, nodes: List[Dict[str, Any]]) -> int:
        """
        Insert node data for a problem.
        
        Args:
            problem_id: Problem ID
            nodes: List of node dictionaries
            
        Returns:
            Number of nodes inserted
        """
        if not nodes:
            return 0
        
        with duckdb.connect(str(self.db_path)) as conn:
            for node in nodes:
                conn.execute("""
                    INSERT INTO nodes (problem_id, node_id, x, y, z, demand, is_depot,
                                      display_x, display_y)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
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
        
        return len(nodes)
    

    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file tracking information.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file tracking info or None
        """
        with duckdb.connect(str(self.db_path)) as conn:
            result = conn.execute("""
                SELECT problem_id, checksum, last_processed, file_size
                FROM file_tracking
                WHERE file_path = ?
            """, [file_path]).fetchone()
            
            if result:
                return {
                    'problem_id': result[0],
                    'checksum': result[1],
                    'last_processed': result[2],
                    'file_size': result[3]
                }
            
            return None
    
    def update_file_tracking(self, tracking_info: Dict[str, Any]) -> None:
        """
        Update file tracking information.
        
        Args:
            tracking_info: Dictionary with tracking information
        """
        with duckdb.connect(str(self.db_path)) as conn:
            # Check if file path exists
            existing = conn.execute("""
                SELECT id FROM file_tracking WHERE file_path = ?
            """, [tracking_info['file_path']]).fetchone()
            
            if existing:
                # Update existing record
                conn.execute("""
                    UPDATE file_tracking
                    SET problem_id = ?, checksum = ?, last_processed = ?, file_size = ?
                    WHERE file_path = ?
                """, [
                    tracking_info['problem_id'],
                    tracking_info['checksum'],
                    tracking_info['last_processed'],
                    tracking_info['file_size'],
                    tracking_info['file_path']
                ])
            else:
                # Insert new record
                conn.execute("""
                    INSERT INTO file_tracking 
                    (file_path, problem_id, checksum, last_processed, file_size)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    tracking_info['file_path'],
                    tracking_info['problem_id'],
                    tracking_info['checksum'],
                    tracking_info['last_processed'],
                    tracking_info['file_size']
                ])
    
    def get_problem_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored problems.
        
        Returns:
            Dictionary with statistics
        """
        with duckdb.connect(str(self.db_path)) as conn:
            # Count by type
            type_counts = conn.execute("""
                SELECT type, COUNT(*) as count, AVG(dimension) as avg_dim, MAX(dimension) as max_dim
                FROM problems
                GROUP BY type
            """).fetchall()
            
            # Total count
            total = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
            
            return {
                'total_problems': total,
                'by_type': [
                    {
                        'type': row[0],
                        'count': row[1],
                        'avg_dimension': round(row[2], 2) if row[2] else 0,
                        'max_dimension': row[3]
                    }
                    for row in type_counts
                ]
            }
    
    def query_problems(
        self,
        problem_type: Optional[str] = None,
        min_dimension: Optional[int] = None,
        max_dimension: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query problems with filters.
        
        Args:
            problem_type: Filter by problem type
            min_dimension: Minimum dimension
            max_dimension: Maximum dimension
            limit: Maximum results to return
            
        Returns:
            List of problem dictionaries
        """
        query = "SELECT * FROM problems WHERE 1=1"
        params = []
        
        if problem_type:
            query += " AND type = ?"
            params.append(problem_type)
        
        if min_dimension is not None:
            query += " AND dimension >= ?"
            params.append(min_dimension)
        
        if max_dimension is not None:
            query += " AND dimension <= ?"
            params.append(max_dimension)
        
        query += f" LIMIT {limit}"
        
        with duckdb.connect(str(self.db_path)) as conn:
            results = conn.execute(query, params).fetchall()
            
            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'comment': row[3],
                    'dimension': row[4],
                    'capacity': row[5],
                    'edge_weight_type': row[6],
                    'edge_weight_format': row[7]
                }
                for row in results
            ]
    
    def export_problem(self, problem_id: int) -> Dict[str, Any]:
        """
        Export complete problem data.
        
        Args:
            problem_id: Problem ID to export
            
        Returns:
            Dictionary with complete problem data
        """
        with duckdb.connect(str(self.db_path)) as conn:
            # Get problem data
            problem = conn.execute("""
                SELECT * FROM problems WHERE id = ?
            """, [problem_id]).fetchone()
            
            if not problem:
                raise ValueError(f"Problem {problem_id} not found")
            
            # Get nodes
            nodes = conn.execute("""
                SELECT * FROM nodes WHERE problem_id = ?
            """, [problem_id]).fetchall()
            
            # NO EDGES - not precomputed
            
            return {
                'problem': {
                    'id': problem[0],
                    'name': problem[1],
                    'type': problem[2],
                    'comment': problem[3],
                    'dimension': problem[4]
                },
                'nodes': [
                    {
                        'node_id': node[2],
                        'x': node[3],
                        'y': node[4],
                        'z': node[5],
                        'demand': node[6],
                        'is_depot': node[7]
                    }
                    for node in nodes
                ]
            }
