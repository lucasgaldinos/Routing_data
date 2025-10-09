"""
Tests for converter.api.SimpleConverter - High-level API for TSPLIB parsing and conversion.

Tests the actual behavior of SimpleConverter which integrates FormatParser with DataTransformer.
Based on verified system output.
"""
import pytest
import json
import tempfile
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from converter.api import SimpleConverter
from format.exceptions import ParseError


class TestSimpleConverterParsing:
    """Test SimpleConverter.parse_file() method."""
    
    @pytest.fixture
    def converter(self):
        """Create SimpleConverter instance for testing."""
        return SimpleConverter()
    
    def test_parse_file_returns_expected_structure(self, converter):
        """
        WHAT: Test that parse_file returns correct data structure
        WHY: SimpleConverter should return transformed data with all required keys
        EXPECTED: Returns dict with 'problem_data', 'nodes', 'tours', 'metadata' keys
        DATA: gr17.tsp
        """
        result = converter.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        
        # Verify top-level keys
        assert isinstance(result, dict), "Should return dictionary"
        required_keys = {'problem_data', 'nodes', 'tours', 'metadata'}
        assert set(result.keys()) == required_keys, f"Should have keys: {required_keys}"
    
    def test_parse_file_problem_data_structure(self, converter):
        """
        WHAT: Test problem_data structure from parse_file
        WHY: Problem data should contain all metadata fields plus file info
        EXPECTED: Contains name, type, dimension, edge_weight_type, file_path, file_size, etc.
        DATA: gr17.tsp - EXPLICIT, 17 nodes
        """
        result = converter.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        problem_data = result['problem_data']
        
        # Verify essential fields
        assert problem_data['name'] == 'gr17'
        assert problem_data['type'] == 'TSP'
        assert problem_data['dimension'] == 17
        assert problem_data['edge_weight_type'] == 'EXPLICIT'
        
        # Verify file metadata added by transformer
        assert 'file_path' in problem_data
        assert 'file_size' in problem_data
        assert isinstance(problem_data['file_size'], int)
    
    def test_parse_file_nodes_structure(self, converter):
        """
        WHAT: Test nodes structure from parse_file
        WHY: Nodes should have all required fields including display coordinates
        EXPECTED: Each node has node_id, x, y, z, demand, is_depot, display_x, display_y
        DATA: gr17.tsp - 17 nodes
        """
        result = converter.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        nodes = result['nodes']
        
        assert len(nodes) == 17, "Should have 17 nodes"
        
        # Verify node structure (transformer adds display_x, display_y)
        node = nodes[0]
        required_fields = {'node_id', 'x', 'y', 'z', 'demand', 'is_depot', 'display_x', 'display_y'}
        assert set(node.keys()) == required_fields, f"Node should have fields: {required_fields}"
        
        # Verify values
        assert node['node_id'] == 0, "First node should have ID 0"
        assert node['display_x'] is None, "EXPLICIT problem has no display coordinates"
        assert node['display_y'] is None
    
    def test_parse_file_metadata_structure(self, converter):
        """
        WHAT: Test metadata structure from parse_file
        WHY: Metadata should contain file info and problem characteristics
        EXPECTED: Contains file_path, file_name, has_coordinates, is_symmetric, weight_source, etc.
        DATA: gr17.tsp
        """
        result = converter.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        metadata = result['metadata']
        
        # Verify metadata fields
        assert 'file_path' in metadata
        assert 'file_name' in metadata
        assert 'file_size' in metadata
        assert 'has_coordinates' in metadata
        assert 'has_demands' in metadata
        assert 'has_depots' in metadata
        assert 'is_symmetric' in metadata
        assert 'weight_source' in metadata
        
        # Verify values for gr17.tsp
        assert metadata['file_name'] == 'gr17.tsp'
        assert metadata['has_coordinates'] is False  # EXPLICIT matrix
        assert metadata['has_demands'] is False  # TSP has no demands
        assert metadata['has_depots'] is False  # TSP has no depots
    
    def test_parse_file_with_coordinate_problem(self, converter):
        """
        WHAT: Test parsing coordinate-based problem
        WHY: Verify SimpleConverter handles EUC_2D problems correctly
        EXPECTED: Returns same structure with edge_weight_type='EUC_2D'
        DATA: berlin52.tsp - EUC_2D, 52 nodes
        """
        result = converter.parse_file('datasets_raw/problems/tsp/berlin52.tsp')
        
        assert result['problem_data']['name'] == 'berlin52'
        assert result['problem_data']['type'] == 'TSP'
        assert result['problem_data']['dimension'] == 52
        assert result['problem_data']['edge_weight_type'] == 'EUC_2D'
        assert len(result['nodes']) == 52


class TestSimpleConverterErrorHandling:
    """Test SimpleConverter error handling."""
    
    @pytest.fixture
    def converter(self):
        """Create SimpleConverter instance for testing."""
        return SimpleConverter()
    
    def test_parse_nonexistent_file_raises_error(self, converter):
        """
        WHAT: Test that parsing nonexistent file raises ParseError
        WHY: Should handle file not found gracefully
        EXPECTED: Raises ParseError with descriptive message
        DATA: nonexistent.tsp (file does not exist)
        """
        with pytest.raises(ParseError) as exc_info:
            converter.parse_file('nonexistent.tsp')
        
        assert 'nonexistent.tsp' in str(exc_info.value)
        assert 'No such file or directory' in str(exc_info.value)
    
    def test_parse_invalid_path_raises_error(self, converter):
        """
        WHAT: Test that parsing with invalid path raises ParseError
        WHY: Should validate file path
        EXPECTED: Raises ParseError for invalid paths
        DATA: /invalid/path/file.tsp
        """
        with pytest.raises(ParseError):
            converter.parse_file('/invalid/path/file.tsp')


class TestSimpleConverterJSONConversion:
    """Test SimpleConverter.to_json() and to_json_format() methods."""
    
    @pytest.fixture
    def converter(self):
        """Create SimpleConverter instance for testing."""
        return SimpleConverter()
    
    @pytest.fixture
    def sample_data(self, converter):
        """Parse sample data for JSON conversion tests."""
        return converter.parse_file('datasets_raw/problems/tsp/gr17.tsp')
    
    def test_to_json_format_structure(self, converter, sample_data):
        """
        WHAT: Test to_json_format() transformation
        WHY: Should convert to JSON-friendly format
        EXPECTED: Returns dict with 'problem', 'nodes', 'tours', 'metadata' keys
        DATA: gr17.tsp parsed data
        """
        json_format = converter.transformer.to_json_format(sample_data)
        
        # Verify structure
        assert isinstance(json_format, dict)
        required_keys = {'problem', 'nodes', 'tours', 'metadata'}
        assert set(json_format.keys()) == required_keys
        
        # Verify types
        assert isinstance(json_format['problem'], dict)
        assert isinstance(json_format['nodes'], list)
        assert isinstance(json_format['tours'], list)
        assert isinstance(json_format['metadata'], dict)
    
    def test_to_json_format_preserves_data(self, converter, sample_data):
        """
        WHAT: Test that to_json_format preserves essential data
        WHY: Transformation should not lose information
        EXPECTED: Problem name, dimension, node count remain the same
        DATA: gr17.tsp
        """
        json_format = converter.transformer.to_json_format(sample_data)
        
        assert json_format['problem']['name'] == 'gr17'
        assert json_format['problem']['dimension'] == 17
        assert len(json_format['nodes']) == 17
    
    def test_to_json_writes_valid_file(self, converter, sample_data):
        """
        WHAT: Test to_json() writes valid JSON file
        WHY: Should create readable JSON file
        EXPECTED: Creates JSON file that can be parsed back
        DATA: gr17.tsp -> temp JSON file
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'test_output.json'
            
            # Write JSON
            converter.to_json(sample_data, str(output_path))
            
            # Verify file exists
            assert output_path.exists(), "JSON file should be created"
            
            # Verify valid JSON
            with open(output_path) as f:
                loaded_data = json.load(f)
            
            assert loaded_data['problem']['name'] == 'gr17'
            assert loaded_data['problem']['dimension'] == 17
            assert len(loaded_data['nodes']) == 17
    
    def test_to_json_creates_output_directory(self, converter, sample_data):
        """
        WHAT: Test that to_json() creates output directory if needed
        WHY: Should handle missing directories automatically
        EXPECTED: Creates nested directories and writes file
        DATA: gr17.tsp -> nested/path/output.json
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'nested' / 'path' / 'output.json'
            
            # Write JSON (directory doesn't exist yet)
            converter.to_json(sample_data, str(output_path))
            
            # Verify directory and file created
            assert output_path.parent.exists(), "Parent directory should be created"
            assert output_path.exists(), "JSON file should be created"


class TestSimpleConverterIntegration:
    """Test SimpleConverter end-to-end integration."""
    
    @pytest.fixture
    def converter(self):
        """Create SimpleConverter instance for testing."""
        return SimpleConverter()
    
    def test_parse_transform_json_pipeline(self, converter):
        """
        WHAT: Test complete parse → transform → JSON pipeline
        WHY: Verify SimpleConverter integrates all components correctly
        EXPECTED: Parse file, transform data, write JSON successfully
        DATA: gr17.tsp → parse → transform → JSON
        """
        # Parse
        data = converter.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        
        # Transform to JSON format
        json_format = converter.transformer.to_json_format(data)
        
        # Write to temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'output.json'
            converter.to_json(data, str(output_path))
            
            # Verify
            assert output_path.exists()
            with open(output_path) as f:
                loaded = json.load(f)
            
            assert loaded['problem']['name'] == 'gr17'
            assert loaded['problem']['type'] == 'TSP'
            assert len(loaded['nodes']) == 17
    
    def test_consistency_across_multiple_files(self, converter):
        """
        WHAT: Test that SimpleConverter handles multiple files consistently
        WHY: Should produce consistent output format for different problems
        EXPECTED: All files return same structure (keys, types)
        DATA: gr17.tsp, berlin52.tsp
        """
        files = [
            'datasets_raw/problems/tsp/gr17.tsp',
            'datasets_raw/problems/tsp/berlin52.tsp'
        ]
        
        results = [converter.parse_file(f) for f in files]
        
        # Verify all have same structure
        for result in results:
            assert set(result.keys()) == {'problem_data', 'nodes', 'tours', 'metadata'}
            assert isinstance(result['problem_data'], dict)
            assert isinstance(result['nodes'], list)
            assert isinstance(result['tours'], list)
            assert isinstance(result['metadata'], dict)
        
        # Verify dimensions match node counts
        for result in results:
            assert result['problem_data']['dimension'] == len(result['nodes'])
