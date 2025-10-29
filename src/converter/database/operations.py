"""Database operations for TSPLIB data storage and retrieval."""

import duckdb
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ..utils.exceptions import DatabaseError


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
                conn.execute("CREATE SEQUENCE IF NOT EXISTS solutions_seq START 1")
                
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
                
                # NO EDGES TABLE - edges are computed on-demand for coordinate-based problems
                
                # Create edge_weight_matrices table for EXPLICIT distance problems
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS edge_weight_matrices (
                        problem_id INTEGER PRIMARY KEY,
                        dimension INTEGER NOT NULL,
                        matrix_format VARCHAR NOT NULL,
                        is_symmetric BOOLEAN NOT NULL,
                        matrix_json TEXT NOT NULL,
                        FOREIGN KEY (problem_id) REFERENCES problems(id)
                    )
                """)
                
                # Create solutions table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS solutions (
                        id INTEGER PRIMARY KEY DEFAULT nextval('solutions_seq'),
                        problem_id INTEGER NOT NULL,
                        solution_name VARCHAR,
                        solution_type VARCHAR,
                        cost DOUBLE,
                        routes INTEGER[][],
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (problem_id) REFERENCES problems(id)
                    )
                """)
                
                # Create file tracking table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS file_tracking (
                        id INTEGER PRIMARY KEY DEFAULT nextval('file_tracking_seq'),
                        file_path VARCHAR UNIQUE NOT NULL,
                        problem_id INTEGER,
                        checksum VARCHAR,
                        last_processed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                    CREATE INDEX IF NOT EXISTS idx_solutions_problem 
                    ON solutions(problem_id)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_edge_matrices_problem 
                    ON edge_weight_matrices(problem_id)
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
        """Apply schema migrations for VRP variant support with transaction protection."""
        try:
            # Check if VRP fields exist and add them if needed
            result = conn.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'problems' AND column_name = 'capacity_vol'
            """).fetchall()
            
            if not result:
                # Wrap ALTER TABLE statements in transaction for atomicity
                conn.execute("BEGIN TRANSACTION")
                try:
                    # Add VRP variant fields (all-or-nothing)
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS capacity_vol INTEGER")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS capacity_weight INTEGER")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS max_distance DOUBLE")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS service_time DOUBLE")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS vehicles INTEGER")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS depots INTEGER")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS periods INTEGER")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS has_time_windows BOOLEAN")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS has_pickup_delivery BOOLEAN")
                    conn.execute("COMMIT")
                    self.logger.debug("Added VRP variant fields to problems table")
                except Exception as e:
                    conn.execute("ROLLBACK")
                    # Only raise if it's not a "column already exists" type error
                    if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                        self.logger.error(f"Schema migration failed: {e}")
                        raise DatabaseError(
                            f"Failed to migrate schema: {e}",
                            operation="schema_migration"
                        )
                
        except Exception as e:
            # If information_schema query fails, try direct column addition with IF NOT EXISTS
            # This is a fallback for databases that don't support information_schema
            if "information_schema" in str(e).lower() or "catalog" in str(e).lower():
                try:
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS capacity_vol INTEGER")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS capacity_weight INTEGER")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS max_distance DOUBLE")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS service_time DOUBLE")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS vehicles INTEGER")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS depots INTEGER")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS periods INTEGER")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS has_time_windows BOOLEAN")
                    conn.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS has_pickup_delivery BOOLEAN")
                except Exception as fallback_error:
                    # Only ignore "column exists" errors, raise everything else
                    if "already exists" not in str(fallback_error).lower():
                        self.logger.error(f"Schema migration fallback failed: {fallback_error}")
                        raise DatabaseError(
                            f"Failed to migrate schema (fallback): {fallback_error}",
                            operation="schema_migration_fallback"
                        )
            else:
                # Not an information_schema issue, re-raise
                raise
    
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
    
    def insert_edge_weights(self, problem_id: int, edge_weight_data: Dict[str, Any]) -> bool:
        """
        Insert edge weight matrix for EXPLICIT distance problems.
        
        Args:
            problem_id: Problem ID
            edge_weight_data: Dictionary with:
                - dimension: Number of nodes
                - matrix_format: 'FULL_MATRIX', 'LOWER_ROW', 'UPPER_ROW', etc.
                - is_symmetric: True if symmetric TSP, False if ATSP
                - matrix_json: JSON string of distance matrix
                
        Returns:
            True if successful
            
        Examples:
            >>> import json
            >>> matrix = [[0, 10, 15], [10, 0, 20], [15, 20, 0]]
            >>> db.insert_edge_weights(1, {
            ...     'dimension': 3,
            ...     'matrix_format': 'FULL_MATRIX',
            ...     'is_symmetric': True,
            ...     'matrix_json': json.dumps(matrix)
            ... })
        """
        if not edge_weight_data:
            return False
        
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO edge_weight_matrices (problem_id, dimension, matrix_format, 
                                                  is_symmetric, matrix_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (problem_id) DO UPDATE SET
                    dimension = EXCLUDED.dimension,
                    matrix_format = EXCLUDED.matrix_format,
                    is_symmetric = EXCLUDED.is_symmetric,
                    matrix_json = EXCLUDED.matrix_json
            """, [
                problem_id,
                edge_weight_data.get('dimension'),
                edge_weight_data.get('matrix_format'),
                edge_weight_data.get('is_symmetric'),
                edge_weight_data.get('matrix_json')
            ])
        
        return True
    
    def _insert_problem_internal(
        self,
        conn,
        problem_data: Dict[str, Any], 
        nodes: List[Dict[str, Any]],
        file_path: str,
        checksum: str,
        solution_data: Optional[Dict[str, Any]] = None,
        edge_weight_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Internal method to insert problem data using an existing connection.
        
        This is the core insert logic extracted for use in both atomic and batch operations.
        Does NOT manage transactions - caller is responsible for BEGIN/COMMIT/ROLLBACK.
        
        Args:
            conn: Active DuckDB connection
            problem_data: Dictionary with problem information
            nodes: List of node dictionaries
            file_path: Path to source file for tracking
            checksum: File checksum for change detection
            solution_data: Optional solution data
            edge_weight_data: Optional edge weight matrix for EXPLICIT problems
            
        Returns:
            Problem ID if successful
            
        Raises:
            DatabaseError: If any database operation fails
        """
        # Step 1: Insert problem
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
        
        problem_id = result[0] if result else None
        if not problem_id:
            raise DatabaseError(
                "Failed to insert problem - no ID returned",
                operation="insert_problem"
            )
        
        # Step 2: Insert nodes (bulk insert for performance)
        if nodes:
            # Build parameter list for bulk insert (much faster than loop)
            node_params = [
                [
                    problem_id,
                    node.get('node_id'),
                    node.get('x'),
                    node.get('y'),
                    node.get('z'),
                    node.get('demand', 0),
                    node.get('is_depot', False),
                    node.get('display_x'),
                    node.get('display_y')
                ]
                for node in nodes
            ]
            # Single bulk insert instead of N individual inserts
            conn.executemany("""
                INSERT INTO nodes (problem_id, node_id, x, y, z, demand, is_depot,
                                  display_x, display_y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, node_params)
        
        # Step 3: Insert edge weights (if provided - EXPLICIT problems)
        if edge_weight_data:
            conn.execute("""
                INSERT INTO edge_weight_matrices (problem_id, dimension, matrix_format, 
                                                  is_symmetric, matrix_json)
                VALUES (?, ?, ?, ?, ?)
            """, [
                problem_id,
                edge_weight_data.get('dimension'),
                edge_weight_data.get('matrix_format'),
                edge_weight_data.get('is_symmetric'),
                edge_weight_data.get('matrix_json')
            ])
        
        # Step 4: Insert solution (if provided)
        if solution_data:
            routes = solution_data.get('routes', [])
            conn.execute("""
                INSERT INTO solutions (problem_id, solution_name, solution_type, cost, routes)
                VALUES (?, ?, ?, ?, ?)
            """, [
                problem_id,
                solution_data.get('name'),
                solution_data.get('type'),
                solution_data.get('cost'),
                routes
            ])
        
        # Step 5: Insert file tracking
        file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
        conn.execute("""
            INSERT INTO file_tracking (file_path, problem_id, checksum, file_size)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (file_path) DO UPDATE SET
                problem_id = EXCLUDED.problem_id,
                checksum = EXCLUDED.checksum,
                last_processed = now(),
                file_size = EXCLUDED.file_size
        """, [file_path, problem_id, checksum, file_size])
        
        self.logger.debug(f"Inserted problem {problem_id} with {len(nodes)} nodes")
        return problem_id
    
    def insert_problem_atomic(
        self, 
        problem_data: Dict[str, Any], 
        nodes: List[Dict[str, Any]],
        file_path: str,
        checksum: str,
        solution_data: Optional[Dict[str, Any]] = None,
        edge_weight_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Atomically insert problem, nodes, edge weights, and file tracking in a single transaction.
        
        This method ensures all-or-nothing insertion: if any step fails, the entire
        operation is rolled back, preventing orphaned database entries.
        
        Args:
            problem_data: Dictionary with problem information
            nodes: List of node dictionaries
            file_path: Path to source file for tracking
            checksum: File checksum for change detection
            solution_data: Optional solution data
            edge_weight_data: Optional edge weight matrix for EXPLICIT problems
            
        Returns:
            Problem ID if successful
            
        Raises:
            Exception: If any database operation fails (transaction will be rolled back)
            
        Examples:
            >>> problem_id = db_manager.insert_problem_atomic(
            ...     problem_data={'name': 'gr17', 'type': 'TSP', ...},
            ...     nodes=[{'node_id': 0, 'x': 1.0, ...}, ...],
            ...     file_path='gr17.tsp',
            ...     checksum='abc123'
            ... )
        """
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute("BEGIN TRANSACTION")
            try:
                problem_id = self._insert_problem_internal(
                    conn, problem_data, nodes, file_path, checksum, 
                    solution_data, edge_weight_data
                )
                # Commit transaction
                conn.execute("COMMIT")
                return problem_id
            except Exception as e:
                # Rollback on any error
                conn.execute("ROLLBACK")
                self.logger.error(f"Transaction rolled back for {file_path}: {e}")
                raise
    
    def insert_problems_batch(
        self,
        problem_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Insert multiple problems using pandas DataFrames for maximum performance.
        
        Leverages DuckDB's native pandas integration and columnar engine for bulk inserts.
        This approach is ~24x faster than executemany() for large datasets.
        
        Why pandas > numpy:
        - DuckDB has zero-copy pandas DataFrame support
        - Handles mixed types (str, float, int, bool) naturally
        - Column-oriented like DuckDB (numpy is row-oriented)
        - Built-in NULL handling
        
        Args:
            problem_results: List of result dictionaries from worker processes
                
        Returns:
            Dictionary with:
                - successful: List of successfully inserted problem names
                - failed: List of dicts with {'name': str, 'error': str} for failures
                - total_inserted: Count of successful inserts
                - total_failed: Count of failures
                
        Examples:
            >>> results = processor.process_files_parallel(...)
            >>> batch_result = db.insert_problems_batch(results['results'])
            >>> print(f"Inserted {batch_result['total_inserted']} problems in ~15 seconds")
        """
        import time
        import pandas as pd
        
        batch_start = time.time()
        successful = []
        failed = []
        
        # Step 1: Collect all data into lists (fast Python operation)
        all_problems = []
        all_nodes = []
        all_edge_weights = []
        all_solutions = []
        all_file_tracking = []
        problem_name_to_temp_id = {}  # Map for foreign keys
        
        collect_start = time.time()
        for temp_id, result in enumerate(problem_results, start=1):
            try:
                problem_data = result.get('problem_data')
                if not problem_data:
                    continue
                
                # Collect problem data
                problem_record = {
                    'temp_id': temp_id,  # Temporary ID for mapping
                    'name': problem_data.get('name'),
                    'type': problem_data.get('type'),
                    'comment': problem_data.get('comment'),
                    'dimension': problem_data.get('dimension'),
                    'capacity': problem_data.get('capacity'),
                    'edge_weight_type': problem_data.get('edge_weight_type'),
                    'edge_weight_format': problem_data.get('edge_weight_format'),
                    'capacity_vol': problem_data.get('capacity_vol'),
                    'capacity_weight': problem_data.get('capacity_weight'),
                    'max_distance': problem_data.get('max_distance'),
                    'service_time': problem_data.get('service_time'),
                    'vehicles': problem_data.get('vehicles'),
                    'depots': problem_data.get('depots'),
                    'periods': problem_data.get('periods'),
                    'has_time_windows': problem_data.get('has_time_windows'),
                    'has_pickup_delivery': problem_data.get('has_pickup_delivery')
                }
                all_problems.append(problem_record)
                problem_name_to_temp_id[problem_data['name']] = temp_id
                
                # Collect nodes with temp_id reference
                for node in result.get('nodes', []):
                    node_record = {
                        'temp_problem_id': temp_id,
                        'node_id': node.get('node_id'),
                        'x': node.get('x'),
                        'y': node.get('y'),
                        'z': node.get('z'),
                        'demand': node.get('demand', 0),
                        'is_depot': node.get('is_depot', False),
                        'display_x': node.get('display_x'),
                        'display_y': node.get('display_y')
                    }
                    all_nodes.append(node_record)
                
                # Collect edge weights
                edge_weight_data = result.get('edge_weight_data')
                if edge_weight_data:
                    edge_record = {
                        'temp_problem_id': temp_id,
                        'dimension': edge_weight_data.get('dimension'),
                        'matrix_format': edge_weight_data.get('matrix_format'),
                        'is_symmetric': edge_weight_data.get('is_symmetric'),
                        'matrix_json': edge_weight_data.get('matrix_json')
                    }
                    all_edge_weights.append(edge_record)
                
                # Collect solutions
                solution_data = result.get('solution_data')
                if solution_data:
                    solution_record = {
                        'temp_problem_id': temp_id,
                        'solution_name': solution_data.get('name'),
                        'solution_type': solution_data.get('type'),
                        'cost': solution_data.get('cost'),
                        'routes': solution_data.get('routes', [])
                    }
                    all_solutions.append(solution_record)
                
                # Collect file tracking
                file_path = result.get('file_path')
                if file_path:
                    from pathlib import Path
                    file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
                    tracking_record = {
                        'temp_problem_id': temp_id,
                        'file_path': file_path,
                        'checksum': result.get('checksum'),
                        'file_size': file_size
                    }
                    all_file_tracking.append(tracking_record)
                
            except Exception as e:
                problem_name = result.get('problem_data', {}).get('name', 'unknown')
                failed.append({'name': problem_name, 'error': f"Data collection failed: {e}"})
                self.logger.error(f"Failed to collect data for {problem_name}: {e}")
        
        collect_time = time.time() - collect_start
        self.logger.info(f"Data collection: {len(all_problems)} problems, {len(all_nodes)} nodes in {collect_time:.2f}s")
        
        # Step 2: Convert to pandas DataFrames (fast columnar operation)
        df_start = time.time()
        problems_df = pd.DataFrame(all_problems)
        nodes_df = pd.DataFrame(all_nodes) if all_nodes else None
        edge_weights_df = pd.DataFrame(all_edge_weights) if all_edge_weights else None
        solutions_df = pd.DataFrame(all_solutions) if all_solutions else None
        file_tracking_df = pd.DataFrame(all_file_tracking) if all_file_tracking else None
        df_time = time.time() - df_start
        
        self.logger.info(f"DataFrame creation: {df_time:.2f}s")
        
        # Step 3: Bulk insert via DuckDB (FAST columnar engine)
        insert_start = time.time()
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute("BEGIN TRANSACTION")
            
            try:
                # Insert problems from DataFrame
                conn.register('problems_temp', problems_df)
                conn.execute("""
                    INSERT INTO problems (name, type, comment, dimension, capacity,
                                         edge_weight_type, edge_weight_format,
                                         capacity_vol, capacity_weight, max_distance,
                                         service_time, vehicles, depots, periods,
                                         has_time_windows, has_pickup_delivery)
                    SELECT name, type, comment, dimension, capacity,
                           edge_weight_type, edge_weight_format,
                           capacity_vol, capacity_weight, max_distance,
                           service_time, vehicles, depots, periods,
                           has_time_windows, has_pickup_delivery
                    FROM problems_temp
                """)
                
                # Create mapping from temp_id to real problem_id using name as key
                conn.execute("""
                    CREATE TEMP TABLE problem_id_mapping AS
                    SELECT pt.temp_id, p.id as real_id
                    FROM problems_temp pt
                    JOIN problems p ON pt.name = p.name
                """)
                
                # Insert nodes with real problem IDs
                if nodes_df is not None:
                    conn.register('nodes_temp', nodes_df)
                    conn.execute("""
                        INSERT INTO nodes (problem_id, node_id, x, y, z, demand, is_depot, display_x, display_y)
                        SELECT m.real_id, n.node_id, n.x, n.y, n.z, n.demand, n.is_depot, n.display_x, n.display_y
                        FROM nodes_temp n
                        JOIN problem_id_mapping m ON n.temp_problem_id = m.temp_id
                    """)
                
                # Insert edge weights
                if edge_weights_df is not None:
                    conn.register('edges_temp', edge_weights_df)
                    conn.execute("""
                        INSERT INTO edge_weight_matrices (problem_id, dimension, matrix_format, is_symmetric, matrix_json)
                        SELECT m.real_id, e.dimension, e.matrix_format, e.is_symmetric, e.matrix_json
                        FROM edges_temp e
                        JOIN problem_id_mapping m ON e.temp_problem_id = m.temp_id
                    """)
                
                # Insert solutions
                if solutions_df is not None:
                    conn.register('solutions_temp', solutions_df)
                    conn.execute("""
                        INSERT INTO solutions (problem_id, solution_name, solution_type, cost, routes)
                        SELECT m.real_id, s.solution_name, s.solution_type, s.cost, s.routes
                        FROM solutions_temp s
                        JOIN problem_id_mapping m ON s.temp_problem_id = m.temp_id
                    """)
                
                # Insert file tracking
                if file_tracking_df is not None:
                    conn.register('tracking_temp', file_tracking_df)
                    conn.execute("""
                        INSERT INTO file_tracking (file_path, problem_id, checksum, file_size)
                        SELECT f.file_path, m.real_id, f.checksum, f.file_size
                        FROM tracking_temp f
                        JOIN problem_id_mapping m ON f.temp_problem_id = m.temp_id
                        ON CONFLICT (file_path) DO UPDATE SET
                            problem_id = EXCLUDED.problem_id,
                            checksum = EXCLUDED.checksum,
                            last_processed = now(),
                            file_size = EXCLUDED.file_size
                    """)
                
                conn.execute("COMMIT")
                successful = [row['name'] for row in all_problems]
                
            except Exception as e:
                conn.execute("ROLLBACK")
                self.logger.error(f"Batch insert failed: {e}")
                failed = [{'name': row['name'], 'error': str(e)} for row in all_problems]
        
        insert_time = time.time() - insert_start
        batch_total = time.time() - batch_start
        
        self.logger.info(
            f"Batch insert complete: {len(successful)} successful, {len(failed)} failed"
        )
        self.logger.info(
            f"Timing breakdown: Collect={collect_time:.2f}s, DataFrame={df_time:.2f}s, "
            f"Insert={insert_time:.2f}s, Total={batch_total:.2f}s"
        )
        
        return {
            'successful': successful,
            'failed': failed,
            'total_inserted': len(successful),
            'total_failed': len(failed)
        }


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
        
        query += " LIMIT ?"  # Parameterized to prevent SQL injection
        params.append(limit)
        
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
                raise DatabaseError(
                    f"Problem {problem_id} not found",
                    operation="get_problem_with_nodes"
                )
            
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
