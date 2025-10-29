"""Tests for database connection leak fix (Issue #6)."""

import pytest
import duckdb
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from converter.database.operations import DatabaseManager
from converter.utils.logging import setup_logging


class TestConnectionLeakFix:
    """Test suite for verifying connection resource management in insert_problem_atomic()."""
    
    def test_insert_problem_atomic_success(self, temp_output_dir):
        """Test normal transaction completes successfully and connection is closed."""
        db_path = Path(temp_output_dir) / "test_success.duckdb"
        db_manager = DatabaseManager(str(db_path), logger=setup_logging())
        
        problem_data = {
            'name': 'test_problem',
            'type': 'TSP',
            'comment': 'Test problem',
            'dimension': 3,
            'capacity': None,
            'edge_weight_type': 'EUC_2D',
            'edge_weight_format': None
        }
        
        nodes = [
            {'node_id': 0, 'x': 0.0, 'y': 0.0, 'demand': 0, 'is_depot': True},
            {'node_id': 1, 'x': 1.0, 'y': 1.0, 'demand': 10, 'is_depot': False},
            {'node_id': 2, 'x': 2.0, 'y': 2.0, 'demand': 20, 'is_depot': False}
        ]
        
        # Insert should succeed
        problem_id = db_manager.insert_problem_atomic(
            problem_data=problem_data,
            nodes=nodes,
            file_path='test.tsp',
            checksum='abc123'
        )
        
        assert problem_id is not None
        assert problem_id > 0
        
        # Verify data persisted
        with duckdb.connect(str(db_path)) as conn:
            problem_count = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
            node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            
            assert problem_count == 1
            assert node_count == 3
    
    def test_insert_problem_atomic_rollback_on_invalid_data(self, temp_output_dir):
        """Test transaction rolls back when invalid data causes failure."""
        db_path = Path(temp_output_dir) / "test_rollback.duckdb"
        db_manager = DatabaseManager(str(db_path), logger=setup_logging())
        
        # Invalid problem data (dimension is None, violates NOT NULL constraint)
        invalid_problem_data = {
            'name': 'invalid_problem',
            'type': 'TSP',
            'comment': 'Should fail',
            'dimension': None,  # This will cause failure
            'capacity': None,
            'edge_weight_type': 'EUC_2D',
            'edge_weight_format': None
        }
        
        nodes = [{'node_id': 0, 'x': 0.0, 'y': 0.0}]
        
        # Should raise exception due to NULL constraint violation
        with pytest.raises(Exception):
            db_manager.insert_problem_atomic(
                problem_data=invalid_problem_data,
                nodes=nodes,
                file_path='invalid.tsp',
                checksum='def456'
            )
        
        # Verify transaction was rolled back - no data should exist
        with duckdb.connect(str(db_path)) as conn:
            problem_count = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
            node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            
            assert problem_count == 0, "Transaction should have rolled back"
            assert node_count == 0, "Transaction should have rolled back"
    
    def test_connection_cleanup_after_failure(self, temp_output_dir):
        """Verify connection is closed even when transaction fails."""
        db_path = Path(temp_output_dir) / "test_cleanup.duckdb"
        db_manager = DatabaseManager(str(db_path), logger=setup_logging())
        
        # Create a valid problem first
        valid_problem_data = {
            'name': 'valid_problem',
            'type': 'TSP',
            'dimension': 2,
            'edge_weight_type': 'EUC_2D'
        }
        
        db_manager.insert_problem_atomic(
            problem_data=valid_problem_data,
            nodes=[],
            file_path='valid.tsp',
            checksum='valid123'
        )
        
        # Now try invalid insert - should fail but not leak connection
        invalid_problem_data = {
            'name': 'invalid',
            'type': 'TSP',
            'dimension': None  # Violates NOT NULL
        }
        
        with pytest.raises(Exception):
            db_manager.insert_problem_atomic(
                problem_data=invalid_problem_data,
                nodes=[],
                file_path='invalid.tsp',
                checksum='invalid456'
            )
        
        # Database should still be accessible (no leaked connections blocking it)
        # This would fail if connection was leaked and not closed
        with duckdb.connect(str(db_path)) as conn:
            result = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
            assert result == 1  # Only the valid problem exists
            
            # Try writing to verify no lock issues - delete file_tracking first due to FK
            conn.execute("DELETE FROM file_tracking WHERE problem_id = 1")
            conn.execute("DELETE FROM problems WHERE name = 'valid_problem'")
            result = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
            assert result == 0
    
    def test_parallel_inserts_no_connection_leak(self, temp_output_dir):
        """Test multiple parallel inserts don't accumulate leaked connections."""
        from concurrent.futures import ThreadPoolExecutor
        
        db_path = Path(temp_output_dir) / "test_parallel.duckdb"
        db_manager = DatabaseManager(str(db_path), logger=setup_logging())
        
        def insert_problem(index):
            """Insert a problem - some succeed, some fail."""
            problem_data = {
                'name': f'problem_{index}',
                'type': 'TSP',
                'dimension': index if index % 2 == 0 else None,  # Even succeed, odd fail
                'edge_weight_type': 'EUC_2D'
            }
            
            try:
                return db_manager.insert_problem_atomic(
                    problem_data=problem_data,
                    nodes=[],
                    file_path=f'problem_{index}.tsp',
                    checksum=f'checksum_{index}'
                )
            except Exception:
                return None
        
        # Run 20 inserts in parallel (10 succeed, 10 fail)
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(insert_problem, range(20)))
        
        # Verify half succeeded, half failed
        successful = [r for r in results if r is not None]
        assert len(successful) == 10
        
        # Verify database is still accessible (no connection leaks)
        with duckdb.connect(str(db_path)) as conn:
            problem_count = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
            assert problem_count == 10
            
            # Can still perform operations (no locks from leaked connections)
            conn.execute("SELECT * FROM problems")
    
    def test_edge_weight_insertion_with_transaction(self, temp_output_dir):
        """Test edge weight matrix insertion within transaction."""
        import json
        
        db_path = Path(temp_output_dir) / "test_edge_weights.duckdb"
        db_manager = DatabaseManager(str(db_path), logger=setup_logging())
        
        problem_data = {
            'name': 'br17',
            'type': 'ATSP',
            'dimension': 3,
            'edge_weight_type': 'EXPLICIT',
            'edge_weight_format': 'FULL_MATRIX'
        }
        
        nodes = [
            {'node_id': 0, 'x': None, 'y': None},
            {'node_id': 1, 'x': None, 'y': None},
            {'node_id': 2, 'x': None, 'y': None}
        ]
        
        edge_weight_data = {
            'dimension': 3,
            'matrix_format': 'FULL_MATRIX',
            'is_symmetric': False,
            'matrix_json': json.dumps([[0, 10, 15], [20, 0, 25], [30, 35, 0]])
        }
        
        # Insert with edge weights
        problem_id = db_manager.insert_problem_atomic(
            problem_data=problem_data,
            nodes=nodes,
            file_path='br17.atsp',
            checksum='br17_checksum',
            edge_weight_data=edge_weight_data
        )
        
        assert problem_id is not None
        
        # Verify edge weights stored
        with duckdb.connect(str(db_path)) as conn:
            result = conn.execute(
                "SELECT matrix_json FROM edge_weight_matrices WHERE problem_id = ?",
                [problem_id]
            ).fetchone()
            
            assert result is not None
            stored_matrix = json.loads(result[0])
            assert stored_matrix == [[0, 10, 15], [20, 0, 25], [30, 35, 0]]
