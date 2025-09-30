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
        # Check if problem already exists
        existing = conn.execute("SELECT id FROM problems WHERE name = ?", [problem_data.get('name')]).fetchone()
        
        if existing:
            # Update existing problem
            conn.execute("""
                UPDATE problems SET
                    updated_at = CURRENT_TIMESTAMP,
                    file_path = ?, file_size = ?, type = ?, dimension = ?,
                    capacity = ?, edge_weight_type = ?, edge_weight_format = ?,
                    node_coord_type = ?, display_data_type = ?, comment = ?
                WHERE name = ?
            """, [
                metadata.get('file_path'), metadata.get('file_size', 0),
                problem_data.get('type'), problem_data.get('dimension'),
                problem_data.get('capacity'), problem_data.get('edge_weight_type'),
                problem_data.get('edge_weight_format'), problem_data.get('node_coord_type'),
                problem_data.get('display_data_type'), problem_data.get('comment'),
                problem_data.get('name')
            ])
            result = existing
        else:
            # Get next available ID
            max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM problems").fetchone()
            new_id = max_id_result[0] if max_id_result else 1
            
            # Insert new problem
            conn.execute("""
                INSERT INTO problems (
                    id, name, type, comment, dimension, capacity, 
                    edge_weight_type, edge_weight_format, 
                    node_coord_type, display_data_type, 
                    file_path, file_size
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                new_id,
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
            ])
            result = [new_id]
        
        if not result:
            raise DatabaseError("Failed to insert problem - no ID returned")
        
        return result[0]
    
    def _bulk_insert_nodes(self, conn, problem_id: int, nodes_data: List[Dict[str, Any]]):
        """Bulk insert nodes using prepared statements for performance."""
        # Clear existing nodes for this problem first
        conn.execute("DELETE FROM nodes WHERE problem_id = ?", [problem_id])
        
        # Prepare bulk insert
        if nodes_data:
            # Get starting ID for nodes
            max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) FROM nodes").fetchone()
            next_id = (max_id_result[0] if max_id_result else 0) + 1
            
            values = []
            for node in nodes_data:
                values.append([
                    next_id,
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
                next_id += 1
            
            conn.executemany("""
                INSERT INTO nodes (id, problem_id, node_id, x, y, z, 
                                 demand, is_depot, display_x, display_y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
    
    def _bulk_insert_edges(self, conn, problem_id: int, edges_data: List[Dict[str, Any]]):
        """Bulk insert edges with conflict resolution."""
        # Clear existing edges for this problem first
        conn.execute("DELETE FROM edges WHERE problem_id = ?", [problem_id])
        
        # Prepare bulk insert
        if edges_data:
            # Get starting ID for edges
            max_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) FROM edges").fetchone()
            next_id = (max_id_result[0] if max_id_result else 0) + 1
            
            values = []
            for edge in edges_data:
                values.append([
                    next_id,
                    problem_id,
                    edge.get('from_node'),
                    edge.get('to_node'),
                    edge.get('weight', 0.0),
                    edge.get('is_fixed', False)
                ])
                next_id += 1
            
            conn.executemany("""
                INSERT INTO edges (id, problem_id, from_node, to_node, weight, is_fixed)
                VALUES (?, ?, ?, ?, ?, ?)
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
