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
