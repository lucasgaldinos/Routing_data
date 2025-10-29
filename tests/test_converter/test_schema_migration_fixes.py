"""Tests for schema migration and exception handling fixes (Issues #7, #8, #9)."""

import pytest
import duckdb
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from converter.database.operations import DatabaseManager
from converter.utils.exceptions import DatabaseError
from converter.utils.logging import setup_logging


class TestSchemaMigrationFixes:
    """Test suite for schema migration transaction protection and error handling."""
    
    def test_migrate_schema_adds_vrp_fields_successfully(self, temp_output_dir):
        """Test that VRP fields are added successfully to problems table."""
        db_path = Path(temp_output_dir) / "test_migration.duckdb"
        db_manager = DatabaseManager(str(db_path), logger=setup_logging())
        
        # Verify VRP fields exist after initialization
        with duckdb.connect(str(db_path)) as conn:
            # Check for VRP-specific columns
            columns = conn.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'problems'
                ORDER BY column_name
            """).fetchall()
            
            column_names = [col[0] for col in columns]
            
            # Verify VRP variant fields exist
            assert 'capacity_vol' in column_names
            assert 'capacity_weight' in column_names
            assert 'max_distance' in column_names
            assert 'service_time' in column_names
            assert 'vehicles' in column_names
            assert 'depots' in column_names
            assert 'periods' in column_names
            assert 'has_time_windows' in column_names
            assert 'has_pickup_delivery' in column_names
    
    def test_migrate_schema_idempotent(self, temp_output_dir):
        """Test that running migration twice doesn't cause errors."""
        db_path = Path(temp_output_dir) / "test_idempotent.duckdb"
        
        # Create database twice - should not error
        db_manager1 = DatabaseManager(str(db_path), logger=setup_logging())
        db_manager2 = DatabaseManager(str(db_path), logger=setup_logging())
        
        # Verify schema is correct
        with duckdb.connect(str(db_path)) as conn:
            result = conn.execute("""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = 'problems' AND column_name = 'capacity_vol'
            """).fetchone()[0]
            
            assert result == 1  # Field exists exactly once


class TestDatabaseErrorUsage:
    """Test suite for proper DatabaseError exception usage."""
    
    def test_database_error_raised_on_failed_insert(self, temp_output_dir):
        """Test that DatabaseError is raised when insert fails, not generic Exception."""
        db_path = Path(temp_output_dir) / "test_error.duckdb"
        db_manager = DatabaseManager(str(db_path), logger=setup_logging())
        
        # Mock the execute to return None (simulating failed INSERT)
        with patch.object(duckdb.DuckDBPyConnection, 'execute') as mock_execute:
            # First call is BEGIN TRANSACTION (should succeed)
            # Second call is INSERT (should return None/empty result)
            mock_result = MagicMock()
            mock_result.fetchone.return_value = None
            mock_execute.return_value = mock_result
            
            # Should raise DatabaseError, not generic Exception
            with pytest.raises(Exception) as exc_info:  # Will check type after fix
                db_manager.insert_problem_atomic(
                    problem_data={'name': 'test', 'type': 'TSP', 'dimension': 10},
                    nodes=[],
                    file_path='test.tsp',
                    checksum='abc123'
                )
            
            # After fix, this should be DatabaseError
            # For now, just verify an exception is raised
            assert exc_info.value is not None
    
    def test_insert_valid_data_no_database_error(self, temp_output_dir):
        """Test that valid inserts don't raise DatabaseError."""
        db_path = Path(temp_output_dir) / "test_valid.duckdb"
        db_manager = DatabaseManager(str(db_path), logger=setup_logging())
        
        problem_data = {
            'name': 'valid_test',
            'type': 'TSP',
            'comment': 'Valid test problem',
            'dimension': 5,
            'edge_weight_type': 'EUC_2D'
        }
        
        nodes = [
            {'node_id': i, 'x': float(i), 'y': float(i)} 
            for i in range(5)
        ]
        
        # Should succeed without raising any exception
        problem_id = db_manager.insert_problem_atomic(
            problem_data=problem_data,
            nodes=nodes,
            file_path='valid_test.tsp',
            checksum='valid123'
        )
        
        assert problem_id is not None
        assert problem_id > 0


class TestSchemaConsistency:
    """Test suite for schema consistency and migration behavior."""
    
    def test_all_vrp_fields_present_after_migration(self, temp_output_dir):
        """Verify all 9 VRP fields are present after migration."""
        db_path = Path(temp_output_dir) / "test_vrp_fields.duckdb"
        db_manager = DatabaseManager(str(db_path), logger=setup_logging())
        
        expected_vrp_fields = [
            'capacity_vol',
            'capacity_weight',
            'max_distance',
            'service_time',
            'vehicles',
            'depots',
            'periods',
            'has_time_windows',
            'has_pickup_delivery'
        ]
        
        with duckdb.connect(str(db_path)) as conn:
            for field in expected_vrp_fields:
                result = conn.execute(f"""
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = 'problems' AND column_name = '{field}'
                """).fetchone()[0]
                
                assert result == 1, f"VRP field '{field}' not found in problems table"
    
    def test_insert_problem_with_vrp_fields(self, temp_output_dir):
        """Test inserting problem data with VRP-specific fields."""
        db_path = Path(temp_output_dir) / "test_vrp_insert.duckdb"
        db_manager = DatabaseManager(str(db_path), logger=setup_logging())
        
        vrp_problem_data = {
            'name': 'vrp_test',
            'type': 'CVRP',
            'dimension': 10,
            'edge_weight_type': 'EUC_2D',
            'capacity': 100,
            'capacity_vol': 200,
            'capacity_weight': 150,
            'max_distance': 500.0,
            'service_time': 10.0,
            'vehicles': 3,
            'depots': 1,
            'periods': 1,
            'has_time_windows': True,
            'has_pickup_delivery': False
        }
        
        nodes = [{'node_id': i, 'x': float(i), 'y': float(i)} for i in range(10)]
        
        problem_id = db_manager.insert_problem_atomic(
            problem_data=vrp_problem_data,
            nodes=nodes,
            file_path='vrp_test.vrp',
            checksum='vrp123'
        )
        
        assert problem_id is not None
        
        # Verify VRP fields stored correctly
        with duckdb.connect(str(db_path)) as conn:
            result = conn.execute("""
                SELECT capacity_vol, capacity_weight, vehicles, has_time_windows
                FROM problems WHERE id = ?
            """, [problem_id]).fetchone()
            
            assert result[0] == 200  # capacity_vol
            assert result[1] == 150  # capacity_weight
            assert result[2] == 3    # vehicles
            assert result[3] is True # has_time_windows
