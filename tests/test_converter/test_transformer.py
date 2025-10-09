"""
Tests for converter.core.transformer.DataTransformer - Data transformation logic.

Tests the actual behavior of DataTransformer which normalizes and enriches parsed data.
Based on verified system output.
"""
import pytest
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from format.parser import FormatParser
from converter.core.transformer import DataTransformer


class TestDataTransformerBasic:
    """Test basic DataTransformer functionality."""
    
    @pytest.fixture
    def transformer(self):
        """Create DataTransformer instance."""
        return DataTransformer()
    
    @pytest.fixture
    def parsed_data(self):
        """Parse sample data for transformation tests."""
        parser = FormatParser()
        return parser.parse_file('datasets_raw/problems/tsp/gr17.tsp')
    
    def test_transform_problem_returns_expected_keys(self, transformer, parsed_data):
        """
        WHAT: Test that transform_problem returns expected structure
        WHY: Should return dict with problem_data, nodes, tours, metadata
        EXPECTED: Returns same keys as input (transformed in place)
        DATA: gr17.tsp parsed data
        """
        result = transformer.transform_problem(parsed_data)
        
        required_keys = {'problem_data', 'nodes', 'tours', 'metadata'}
        assert set(result.keys()) == required_keys
    
    def test_transform_problem_enriches_problem_data(self, transformer, parsed_data):
        """
        WHAT: Test that transform_problem enriches problem_data with file info
        WHY: Should add file_path and file_size from metadata to problem_data
        EXPECTED: problem_data contains file_path and file_size
        DATA: gr17.tsp
        """
        result = transformer.transform_problem(parsed_data)
        problem_data = result['problem_data']
        
        assert 'file_path' in problem_data, "Should add file_path to problem_data"
        assert 'file_size' in problem_data, "Should add file_size to problem_data"
        assert isinstance(problem_data['file_size'], int)
    
    def test_transform_problem_normalizes_nodes(self, transformer, parsed_data):
        """
        WHAT: Test that transform_problem normalizes node structure
        WHY: All nodes should have consistent fields including display coordinates
        EXPECTED: Each node has node_id, x, y, z, demand, is_depot, display_x, display_y
        DATA: gr17.tsp nodes
        """
        result = transformer.transform_problem(parsed_data)
        nodes = result['nodes']
        
        required_fields = {'node_id', 'x', 'y', 'z', 'demand', 'is_depot', 'display_x', 'display_y'}
        
        for node in nodes:
            assert set(node.keys()) == required_fields, \
                f"Each node should have exactly these fields: {required_fields}"
    
    def test_transform_problem_preserves_node_count(self, transformer, parsed_data):
        """
        WHAT: Test that transformation preserves node count
        WHY: Normalization should not add or remove nodes
        EXPECTED: Output node count equals input node count
        DATA: gr17.tsp - 17 nodes
        """
        input_count = len(parsed_data['nodes'])
        result = transformer.transform_problem(parsed_data)
        output_count = len(result['nodes'])
        
        assert output_count == input_count, "Node count should be preserved"
    
    def test_transform_problem_with_file_info(self, transformer, parsed_data):
        """
        WHAT: Test transform_problem with additional file_info parameter
        WHY: Should merge file_info into metadata
        EXPECTED: Metadata contains scanned_file_path, scanned_file_size, detected_type
        DATA: gr17.tsp with custom file_info
        """
        file_info = {
            'file_path': '/custom/path/problem.tsp',
            'file_size': 12345,
            'problem_type': 'TSP'
        }
        
        result = transformer.transform_problem(parsed_data, file_info=file_info)
        metadata = result['metadata']
        
        assert metadata['scanned_file_path'] == '/custom/path/problem.tsp'
        assert metadata['scanned_file_size'] == 12345
        assert metadata['detected_type'] == 'TSP'


class TestDataTransformerJSONFormat:
    """Test DataTransformer.to_json_format() method."""
    
    @pytest.fixture
    def transformer(self):
        """Create DataTransformer instance."""
        return DataTransformer()
    
    @pytest.fixture
    def transformed_data(self, transformer):
        """Get transformed data for JSON format tests."""
        parser = FormatParser()
        parsed = parser.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        return transformer.transform_problem(parsed)
    
    def test_to_json_format_renames_problem_data(self, transformer, transformed_data):
        """
        WHAT: Test that to_json_format renames 'problem_data' to 'problem'
        WHY: JSON format uses shorter key name
        EXPECTED: Returns dict with 'problem' key instead of 'problem_data'
        DATA: gr17.tsp transformed data
        """
        json_format = transformer.to_json_format(transformed_data)
        
        assert 'problem' in json_format, "Should have 'problem' key"
        assert 'problem_data' not in json_format, "Should not have 'problem_data' key"
        assert json_format['problem'] == transformed_data['problem_data']
    
    def test_to_json_format_preserves_nodes_tours_metadata(self, transformer, transformed_data):
        """
        WHAT: Test that to_json_format preserves nodes, tours, metadata unchanged
        WHY: Only problem_data key name changes
        EXPECTED: nodes, tours, metadata are identical
        DATA: gr17.tsp
        """
        json_format = transformer.to_json_format(transformed_data)
        
        assert json_format['nodes'] == transformed_data['nodes']
        assert json_format['tours'] == transformed_data['tours']
        assert json_format['metadata'] == transformed_data['metadata']
    
    def test_to_json_format_returns_expected_keys(self, transformer, transformed_data):
        """
        WHAT: Test that to_json_format returns correct keys
        WHY: JSON format has specific key structure
        EXPECTED: Returns dict with 'problem', 'nodes', 'tours', 'metadata'
        DATA: gr17.tsp
        """
        json_format = transformer.to_json_format(transformed_data)
        
        expected_keys = {'problem', 'nodes', 'tours', 'metadata'}
        assert set(json_format.keys()) == expected_keys


class TestDataTransformerValidation:
    """Test DataTransformer.validate_transformation() method."""
    
    @pytest.fixture
    def transformer(self):
        """Create DataTransformer instance."""
        return DataTransformer()
    
    def test_validate_transformation_valid_data(self, transformer):
        """
        WHAT: Test validation with valid transformed data
        WHY: Valid data should pass all validation checks
        EXPECTED: Returns empty list (no errors)
        DATA: Valid problem with name, type, dimension, sequential node IDs
        """
        valid_data = {
            'problem_data': {
                'name': 'test',
                'type': 'TSP',
                'dimension': 3
            },
            'nodes': [
                {'node_id': 0},
                {'node_id': 1},
                {'node_id': 2}
            ],
            'tours': [],
            'metadata': {}
        }
        
        errors = transformer.validate_transformation(valid_data)
        assert errors == [], "Valid data should have no errors"
    
    def test_validate_transformation_missing_name(self, transformer):
        """
        WHAT: Test validation when problem name is missing
        WHY: Name is required field
        EXPECTED: Returns error about missing name
        DATA: Problem data without name field
        """
        invalid_data = {
            'problem_data': {
                'type': 'TSP',
                'dimension': 1
            },
            'nodes': [{'node_id': 0}],
            'tours': [],
            'metadata': {}
        }
        
        errors = transformer.validate_transformation(invalid_data)
        assert any('name' in err.lower() for err in errors), \
            "Should report missing name"
    
    def test_validate_transformation_missing_type(self, transformer):
        """
        WHAT: Test validation when problem type is missing
        WHY: Type is required field
        EXPECTED: Returns error about missing type
        DATA: Problem data without type field
        """
        invalid_data = {
            'problem_data': {
                'name': 'test',
                'dimension': 1
            },
            'nodes': [{'node_id': 0}],
            'tours': [],
            'metadata': {}
        }
        
        errors = transformer.validate_transformation(invalid_data)
        assert any('type' in err.lower() for err in errors), \
            "Should report missing type"
    
    def test_validate_transformation_missing_dimension(self, transformer):
        """
        WHAT: Test validation when dimension is missing
        WHY: Dimension is required field
        EXPECTED: Returns error about missing dimension
        DATA: Problem data without dimension field
        """
        invalid_data = {
            'problem_data': {
                'name': 'test',
                'type': 'TSP'
            },
            'nodes': [{'node_id': 0}],
            'tours': [],
            'metadata': {}
        }
        
        errors = transformer.validate_transformation(invalid_data)
        assert any('dimension' in err.lower() for err in errors), \
            "Should report missing dimension"
    
    def test_validate_transformation_non_sequential_node_ids(self, transformer):
        """
        WHAT: Test validation with non-sequential node IDs
        WHY: Node IDs must be sequential starting from 0
        EXPECTED: Returns error about non-sequential IDs
        DATA: Nodes with IDs [0, 2, 3] (missing 1)
        """
        invalid_data = {
            'problem_data': {
                'name': 'test',
                'type': 'TSP',
                'dimension': 3
            },
            'nodes': [
                {'node_id': 0},
                {'node_id': 2},  # Non-sequential!
                {'node_id': 3}
            ],
            'tours': [],
            'metadata': {}
        }
        
        errors = transformer.validate_transformation(invalid_data)
        assert any('sequential' in err.lower() for err in errors), \
            "Should report non-sequential node IDs"
    
    def test_validate_transformation_multiple_errors(self, transformer):
        """
        WHAT: Test validation with multiple errors
        WHY: Should report all validation issues
        EXPECTED: Returns list with multiple error messages
        DATA: Invalid problem missing name, type, dimension, with bad node IDs
        """
        invalid_data = {
            'problem_data': {},  # Missing all required fields
            'nodes': [
                {'node_id': 5},  # Non-sequential
                {'node_id': 10}
            ],
            'tours': [],
            'metadata': {}
        }
        
        errors = transformer.validate_transformation(invalid_data)
        
        # Should have at least 4 errors (name, type, dimension, sequential)
        assert len(errors) >= 4, f"Should report multiple errors, got: {errors}"
        assert any('name' in err.lower() for err in errors)
        assert any('type' in err.lower() for err in errors)
        assert any('dimension' in err.lower() for err in errors)
        assert any('sequential' in err.lower() for err in errors)


class TestDataTransformerNodeNormalization:
    """Test node normalization logic."""
    
    @pytest.fixture
    def transformer(self):
        """Create DataTransformer instance."""
        return DataTransformer()
    
    def test_normalize_nodes_adds_missing_fields(self, transformer):
        """
        WHAT: Test that _normalize_nodes adds missing fields with defaults
        WHY: Ensures all nodes have complete structure
        EXPECTED: Nodes with missing fields get default values (0, False, None)
        DATA: Minimal nodes with only node_id
        """
        minimal_nodes = [
            {'node_id': 0},
            {'node_id': 1}
        ]
        
        normalized = transformer._normalize_nodes(minimal_nodes)
        
        for node in normalized:
            assert 'x' in node
            assert 'y' in node
            assert 'z' in node
            assert 'demand' in node
            assert 'is_depot' in node
            assert 'display_x' in node
            assert 'display_y' in node
            
            # Check defaults
            assert node['demand'] == 0, "Missing demand should default to 0"
            assert node['is_depot'] is False, "Missing is_depot should default to False"
    
    def test_normalize_nodes_preserves_existing_values(self, transformer):
        """
        WHAT: Test that _normalize_nodes preserves existing field values
        WHY: Should not overwrite valid data
        EXPECTED: Existing values remain unchanged
        DATA: Nodes with all fields populated
        """
        complete_nodes = [
            {
                'node_id': 0,
                'x': 10.5,
                'y': 20.3,
                'z': None,
                'demand': 15,
                'is_depot': True,
                'display_x': 11.0,
                'display_y': 21.0
            }
        ]
        
        normalized = transformer._normalize_nodes(complete_nodes)
        node = normalized[0]
        
        assert node['node_id'] == 0
        assert node['x'] == 10.5
        assert node['y'] == 20.3
        assert node['demand'] == 15
        assert node['is_depot'] is True
        assert node['display_x'] == 11.0
        assert node['display_y'] == 21.0


class TestDataTransformerIntegration:
    """Test DataTransformer with real parsed data."""
    
    @pytest.fixture
    def transformer(self):
        """Create DataTransformer instance."""
        return DataTransformer()
    
    def test_full_transformation_pipeline(self, transformer):
        """
        WHAT: Test complete transformation pipeline with real data
        WHY: Verify transformer works end-to-end
        EXPECTED: Parse → transform → JSON format → validate all work together
        DATA: gr17.tsp
        """
        # Parse
        parser = FormatParser()
        parsed = parser.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        
        # Transform
        transformed = transformer.transform_problem(parsed)
        
        # Validate
        errors = transformer.validate_transformation(transformed)
        assert errors == [], f"Transformed data should be valid, errors: {errors}"
        
        # Convert to JSON format
        json_format = transformer.to_json_format(transformed)
        
        # Verify JSON format
        assert json_format['problem']['name'] == 'gr17'
        assert json_format['problem']['type'] == 'TSP'
        assert len(json_format['nodes']) == 17
