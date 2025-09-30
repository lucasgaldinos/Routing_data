#!/usr/bin/env python3
"""
Direct test script for Phase 1 functionality.
This bypasses pytest import issues and tests the core functionality directly.
"""

import sys
import tempfile
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, '.')

def test_phase1_functionality():
    """Test the complete Phase 1 workflow directly."""
    print("=== Phase 1 Integration Test ===")
    
    # Import all components
    try:
        from src.converter.core.parser import TSPLIBParser
        from src.converter.database.operations import DatabaseManager
        from src.converter.config import ConverterConfig
        from src.converter.utils.logging import setup_logging
        print("✓ All imports successful")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False
    
    # Setup test file
    test_file = Path("datasets_raw/problems/tsp/gr17.tsp")
    if not test_file.exists():
        print(f"✗ Test file {test_file} not found")
        return False
    print(f"✓ Test file found: {test_file}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Configure components
        config = ConverterConfig(
            database_path=f"{temp_dir}/test.duckdb",
            log_level="INFO"
        )
        
        logger = setup_logging(config.log_level)
        parser = TSPLIBParser(logger)
        db_manager = DatabaseManager(config.database_path, logger)
        
        print("✓ Components initialized")
        
        # Parse file
        try:
            problem_data = parser.parse_file(str(test_file))
            print("✓ File parsed successfully")
        except Exception as e:
            print(f"✗ Parsing failed: {e}")
            return False
        
        # Validate parsed data structure
        required_keys = ['problem_data', 'nodes', 'edges', 'metadata']
        for key in required_keys:
            if key not in problem_data:
                print(f"✗ Missing key in parsed data: {key}")
                return False
        print("✓ Parsed data structure valid")
        
        # Validate problem data content
        problem_info = problem_data['problem_data']
        if problem_info['name'] != 'gr17':
            print(f"✗ Wrong problem name: {problem_info['name']}")
            return False
        if problem_info['type'] != 'TSP':
            print(f"✗ Wrong problem type: {problem_info['type']}")
            return False
        if problem_info['dimension'] != 17:
            print(f"✗ Wrong dimension: {problem_info['dimension']}")
            return False
        print("✓ Problem metadata correct")
        
        # Validate nodes
        nodes = problem_data['nodes']
        if len(nodes) != 17:
            print(f"✗ Wrong number of nodes: {len(nodes)}")
            return False
        
        node_ids = [node['node_id'] for node in nodes]
        if set(node_ids) != set(range(1, 18)):  # TSPLIB uses 1-based indexing
            print(f"✗ Wrong node IDs: {node_ids}")
            return False
        print("✓ Node data correct")
        
        # Validate edges
        edges = problem_data['edges']
        print(f"✓ Found {len(edges)} edges")
        
        # Test database insertion
        try:
            problem_id = db_manager.insert_complete_problem(problem_data)
            print(f"✓ Database insertion successful, problem ID: {problem_id}")
        except Exception as e:
            print(f"✗ Database insertion failed: {e}")
            return False
        
        # Test database retrieval
        try:
            retrieved_problem = db_manager.get_problem_by_name('gr17')
            if not retrieved_problem:
                print("✗ Failed to retrieve problem from database")
                return False
            if retrieved_problem['name'] != 'gr17':
                print(f"✗ Retrieved wrong problem: {retrieved_problem['name']}")
                return False
            print("✓ Database retrieval successful")
        except Exception as e:
            print(f"✗ Database retrieval failed: {e}")
            return False
        
        # Test database statistics
        try:
            stats = db_manager.get_problem_statistics()
            if stats['total_problems'] != 1:
                print(f"✗ Wrong problem count: {stats['total_problems']}")
                return False
            if stats['total_nodes'] != 17:
                print(f"✗ Wrong node count: {stats['total_nodes']}")
                return False
            print("✓ Database statistics correct")
        except Exception as e:
            print(f"✗ Database statistics failed: {e}")
            return False
        
        # Test database integrity
        try:
            issues = db_manager.validate_data_integrity()
            if issues:
                print(f"✗ Database integrity issues: {issues}")
                return False
            print("✓ Database integrity validation passed")
        except Exception as e:
            print(f"✗ Database integrity check failed: {e}")
            return False
    
    print("\n=== ALL TESTS PASSED ===")
    print("Phase 1 implementation is fully functional!")
    return True

if __name__ == "__main__":
    success = test_phase1_functionality()
    sys.exit(0 if success else 1)