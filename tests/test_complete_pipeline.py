"""End-to-end integration test for complete ETL pipeline."""

import pytest
import tempfile
from pathlib import Path

from src.converter.core.parser import TSPLIBParser
from src.converter.core.scanner import FileScanner
from src.converter.core.transformer import DataTransformer
from src.converter.database.operations import DatabaseManager
from src.converter.output.json_writer import JSONWriter
from src.converter.utils.logging import setup_logging


def test_complete_etl_pipeline():
    """
    End-to-end test of complete ETL workflow.
    
    Tests the full pipeline:
    1. Scanner finds files
    2. Parser extracts data from TSPLIB files
    3. Transformer normalizes data
    4. DatabaseManager stores in DuckDB
    5. JSONWriter outputs to JSON
    """
    # Setup
    test_file = Path("datasets_raw/problems/tsp/gr17.tsp")
    if not test_file.exists():
        pytest.skip("Test file gr17.tsp not found")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        logger = setup_logging("INFO")
        
        # Initialize all components
        scanner = FileScanner(logger=logger)
        parser = TSPLIBParser(logger)
        transformer = DataTransformer(logger)
        db_manager = DatabaseManager(f"{temp_dir}/routing.duckdb", logger)
        json_writer = JSONWriter(f"{temp_dir}/json", logger=logger)
        
        # Step 1: Scan for files
        files = scanner.scan_files("datasets_raw/problems/tsp", patterns=["gr17.tsp"], recursive=True)
        assert len(files) == 1
        assert "gr17.tsp" in files[0]
        
        # Step 2: Parse file
        problem_data = parser.parse_file(files[0])
        assert problem_data['problem_data']['name'] == 'gr17'
        assert problem_data['problem_data']['type'] == 'TSP'
        assert problem_data['problem_data']['dimension'] == 17
        
        # Step 3: Transform data
        transformed_data = transformer.transform_problem(problem_data)
        
        # Validate transformation
        errors = transformer.validate_transformation(transformed_data)
        assert len(errors) == 0, f"Validation errors: {errors}"
        
        # Step 4: Store in database
        problem_id = db_manager.insert_problem(transformed_data['problem_data'])
        assert problem_id is not None
        assert problem_id > 0
        
        # Insert nodes (if any)
        if transformed_data['nodes']:
            node_count = db_manager.insert_nodes(problem_id, transformed_data['nodes'])
            assert node_count == len(transformed_data['nodes'])
        
        # Insert edges
        assert len(transformed_data['edges']) > 0
        edge_count = db_manager.insert_edges(problem_id, transformed_data['edges'])
        assert edge_count == len(transformed_data['edges'])
        
        # Step 5: Write JSON
        json_path = json_writer.write_problem(transformed_data)
        assert Path(json_path).exists()
        
        # Verify JSON content
        import json
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        
        assert json_data['problem']['name'] == 'gr17'
        assert json_data['problem']['dimension'] == 17
        assert 'edges' in json_data
        assert len(json_data['edges']) > 0
        
        # Step 6: Query database to verify
        stats = db_manager.get_problem_stats()
        assert stats['total_problems'] == 1
        
        problems = db_manager.query_problems(limit=10)
        assert len(problems) == 1
        assert problems[0]['name'] == 'gr17'
        assert problems[0]['dimension'] == 17
        
        # Export problem
        exported = db_manager.export_problem(problem_id)
        assert exported['problem']['name'] == 'gr17'
        assert 'edges' in exported
        assert len(exported['edges']) > 0


def test_berlin52_with_coordinates():
    """Test pipeline with file that has coordinates."""
    test_file = Path("datasets_raw/problems/tsp/berlin52.tsp")
    if not test_file.exists():
        pytest.skip("Test file berlin52.tsp not found")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        logger = setup_logging("INFO")
        
        parser = TSPLIBParser(logger)
        transformer = DataTransformer(logger)
        db_manager = DatabaseManager(f"{temp_dir}/routing.duckdb", logger)
        
        # Parse
        problem_data = parser.parse_file(str(test_file))
        assert problem_data['problem_data']['name'] == 'berlin52'
        assert len(problem_data['nodes']) == 52
        
        # Check nodes have coordinates
        for node in problem_data['nodes']:
            assert 'x' in node
            assert 'y' in node
            assert node['x'] is not None
            assert node['y'] is not None
        
        # Transform
        transformed_data = transformer.transform_problem(problem_data)
        
        # Store
        problem_id = db_manager.insert_problem(transformed_data['problem_data'])
        node_count = db_manager.insert_nodes(problem_id, transformed_data['nodes'])
        
        assert node_count == 52


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
