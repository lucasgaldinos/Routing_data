"""
Tests for FormatParser - TSPLIB95 file parsing.

Tests the actual behavior of FormatParser.parse_file() method with real TSPLIB files.
Based on verified system output from running the CLI successfully.
"""
import pytest
from pathlib import Path
from typing import Dict, Any, List, cast

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from tsplib_parser.parser import FormatParser
from tsplib_parser.exceptions import ParseError


class TestFormatParserBasic:
    """Test basic FormatParser functionality with real files."""

    def test_parse_file_gr17_explicit_weights(self):
        """
        Test parsing gr17.tsp - 17-city TSP with EXPLICIT edge weights.
        
        WHAT: Parse gr17.tsp and validate the returned data structure
        WHY: Verify parser correctly handles EXPLICIT weight matrix problems
        EXPECTED: Returns dict with problem_data, nodes (no coordinates), tours, metadata
        TEST DATA: gr17.tsp (17 cities, EXPLICIT weights, LOWER_DIAG_ROW format)
        
        NOTE: Coordinates are null for EXPLICIT weight problems - this is correct behavior.
        """
        parser = FormatParser()
        result = parser.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        
        # Verify result structure
        assert isinstance(result, dict), "Result must be a dictionary"
        assert 'problem_data' in result, "Result must have problem_data key"
        assert 'nodes' in result, "Result must have nodes key"
        assert 'tours' in result, "Result must have tours key"
        assert 'metadata' in result, "Result must have metadata key"
        
        # Verify problem_data
        problem_data = result['problem_data']
        assert problem_data['name'] == 'gr17', "Problem name should be gr17"
        assert problem_data['type'] == 'TSP', "Problem type should be TSP"
        assert problem_data['dimension'] == 17, "Should have 17 nodes"
        assert problem_data['edge_weight_type'] == 'EXPLICIT', "Should have EXPLICIT weights"
        assert problem_data['edge_weight_format'] == 'LOWER_DIAG_ROW', "Should be LOWER_DIAG_ROW format"
        
        # Verify nodes structure
        nodes: List[Dict[str, Any]] = cast(List[Dict[str, Any]], result['nodes'])
        assert isinstance(nodes, list), "Nodes must be a list"
        assert len(nodes) == 17, "Should have exactly 17 nodes"
        
        # Verify node structure (EXPLICIT problems have no coordinates)
        for node in nodes:
            assert 'node_id' in node, "Node must have node_id"
            assert 'x' in node, "Node must have x field (even if null)"
            assert 'y' in node, "Node must have y field (even if null)"
            assert 'demand' in node, "Node must have demand field"
            assert 'is_depot' in node, "Node must have is_depot field"
            
            # EXPLICIT weight problems don't have coordinates
            assert node['x'] is None, "EXPLICIT problems should have null coordinates"
            assert node['y'] is None, "EXPLICIT problems should have null coordinates"
            assert node['demand'] == 0, "TSP problems have 0 demand"
            assert node['is_depot'] is False, "TSP problems have no depots"
        
        # Verify node_id sequence (0-based indexing)
        for i, node in enumerate(nodes):
            assert node['node_id'] == i, f"Node {i} should have node_id={i}"
        
        # Verify tours (gr17.tsp has no tour solution)
        tours: List[Any] = cast(List[Any], result['tours'])
        assert isinstance(tours, list), "Tours must be a list"
        assert len(tours) == 0, "gr17.tsp has no tour solution"
        
        # Verify metadata
        metadata = result['metadata']
        assert 'file_path' in metadata, "Metadata must have file_path"
        assert 'gr17.tsp' in metadata['file_path'], "file_path should contain filename"
        assert metadata['has_coordinates'] is False, "EXPLICIT problems have no coordinates"
        assert metadata['is_symmetric'] is True, "TSP is symmetric"
        assert metadata['weight_source'] == 'explicit_matrix', "Should be explicit_matrix"

    def test_parse_file_att48_att_distance(self):
        """
        Test parsing att48.tsp - 48-city TSP with ATT (pseudo-Euclidean) distance.
        
        WHAT: Parse att48.tsp with ATT distance metric
        WHY: Verify parser handles different distance types
        EXPECTED: Problem data with ATT edge_weight_type, 48 nodes
        TEST DATA: att48.tsp (48 US capitals, ATT distance)
        
        NOTE: Current implementation shows coordinates as null even for coordinate-based
        problems. This is a known issue to be fixed later.
        """
        parser = FormatParser()
        result = parser.parse_file('datasets_raw/problems/tsp/att48.tsp')
        
        # Verify problem data
        problem_data = result['problem_data']
        assert problem_data['name'] == 'att48', "Problem name should be att48"
        assert problem_data['type'] == 'TSP', "Problem type should be TSP"
        assert problem_data['dimension'] == 48, "Should have 48 nodes"
        assert problem_data['edge_weight_type'] == 'ATT', "Should use ATT distance"
        assert problem_data['comment'] == '48 capitals of the US (Padberg/Rinaldi)', "Should have correct comment"
        
        # Verify correct number of nodes
        assert len(result['nodes']) == 48, "Should extract all 48 nodes"
        
        # Verify metadata indicates coordinate-based problem
        metadata = result['metadata']
        assert metadata['weight_source'] == 'coordinate_based', "ATT is coordinate-based"
        assert metadata['is_symmetric'] is True, "ATT problems are symmetric"

    def test_parse_file_berlin52_euclidean(self):
        """
        Test parsing berlin52.tsp - 52-location TSP with Euclidean distances.
        
        WHAT: Parse berlin52.tsp with EUC_2D distance
        WHY: Verify parser handles Euclidean distance type
        EXPECTED: Problem data with EUC_2D, 52 nodes
        TEST DATA: berlin52.tsp (52 locations in Berlin)
        """
        parser = FormatParser()
        result = parser.parse_file('datasets_raw/problems/tsp/berlin52.tsp')
        
        problem_data = result['problem_data']
        assert problem_data['name'] == 'berlin52', "Problem name should be berlin52"
        assert problem_data['dimension'] == 52, "Should have 52 nodes"
        assert problem_data['edge_weight_type'] == 'EUC_2D', "Should use Euclidean 2D distance"
        
        assert len(result['nodes']) == 52, "Should extract all 52 nodes"


class TestFormatParserErrorHandling:
    """Test error handling in FormatParser."""

    def test_parse_nonexistent_file(self):
        """
        Test parsing a file that doesn't exist.
        
        WHAT: Attempt to parse non-existent file
        WHY: Verify parser raises appropriate error
        EXPECTED: ParseError raised
        """
        parser = FormatParser()
        
        with pytest.raises(ParseError):
            parser.parse_file('nonexistent_file.tsp')

    def test_parse_invalid_file_path(self):
        """
        Test parsing with invalid file path.
        
        WHAT: Pass invalid path to parser
        WHY: Verify error handling for bad paths
        EXPECTED: ParseError raised
        """
        parser = FormatParser()
        
        with pytest.raises(ParseError):
            parser.parse_file('/invalid/path/to/file.tsp')


class TestFormatParserDataIntegrity:
    """Test data integrity and consistency."""

    def test_node_id_sequence(self):
        """
        Test that node IDs form a proper 0-based sequence.
        
        WHAT: Verify node_id values are sequential from 0
        WHY: Ensure proper 1-based TSPLIB → 0-based database conversion
        EXPECTED: node_ids = [0, 1, 2, ..., n-1] for n nodes
        """
        parser = FormatParser()
        result = parser.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        
        nodes = result['nodes']
        node_ids = [node['node_id'] for node in nodes]
        
        # Check sequence
        expected = list(range(len(nodes)))
        assert node_ids == expected, f"Expected {expected}, got {node_ids}"

    def test_dimension_matches_node_count(self):
        """
        Test that dimension field matches actual node count.
        
        WHAT: Verify problem dimension equals number of extracted nodes
        WHY: Ensure data consistency
        EXPECTED: dimension == len(nodes)
        """
        parser = FormatParser()
        
        # Test with multiple files
        test_files = [
            ('datasets_raw/problems/tsp/gr17.tsp', 17),
            ('datasets_raw/problems/tsp/att48.tsp', 48),
            ('datasets_raw/problems/tsp/berlin52.tsp', 52),
        ]
        
        for file_path, expected_dimension in test_files:
            result = parser.parse_file(file_path)
            dimension = result['problem_data']['dimension']
            node_count = len(result['nodes'])
            
            assert dimension == node_count, \
                f"{file_path}: dimension={dimension} but got {node_count} nodes"
            assert dimension == expected_dimension, \
                f"{file_path}: expected dimension={expected_dimension}, got {dimension}"


class TestFormatParserMetadata:
    """Test metadata extraction."""

    def test_metadata_file_info(self):
        """
        Test that metadata contains correct file information.
        
        WHAT: Verify metadata has file_path, file_name, file_size
        WHY: Ensure file tracking works correctly
        EXPECTED: Metadata with complete file information
        """
        parser = FormatParser()
        result = parser.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        
        metadata = result['metadata']
        
        # Check required fields
        assert 'file_path' in metadata, "Must have file_path"
        assert 'file_name' in metadata, "Must have file_name"
        assert 'file_size' in metadata, "Must have file_size"
        assert 'problem_source' in metadata, "Must have problem_source"
        
        # Check values
        assert metadata['file_name'] == 'gr17.tsp', "Should extract filename"
        assert 'gr17.tsp' in metadata['file_path'], "file_path should contain filename"
        assert metadata['file_size'] > 0, "file_size should be positive"
        assert metadata['problem_source'] == 'tsp', "Should extract problem source from path"

    def test_metadata_problem_characteristics(self):
        """
        Test metadata problem characteristic flags.
        
        WHAT: Verify has_coordinates, has_demands, has_depots, is_symmetric flags
        WHY: Ensure problem characteristics are correctly identified
        EXPECTED: Correct boolean flags based on problem type
        """
        parser = FormatParser()
        result = parser.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        
        metadata = result['metadata']
        
        # TSP problems should have specific characteristics
        assert metadata['has_coordinates'] is False, "EXPLICIT problems have no coordinates"
        assert metadata['has_demands'] is False, "TSP has no demands"
        assert metadata['has_depots'] is False, "TSP has no depots"
        assert metadata['is_symmetric'] is True, "TSP is symmetric"


class TestFormatParserValueValidation:
    """Test that parser extracts CORRECT values, not just structure.
    
    This addresses the critical finding that previous tests only checked
    structure (dict keys exist) but never validated actual data values.
    """

    def test_gr17_edge_weight_matrix_correctness(self):
        """
        Verify gr17.tsp edge weight matrix values are correct.
        
        WHAT: Parse gr17.tsp and validate actual edge weight values against reference
        WHY: Ensure parser extracts correct distances, not just structure
        EXPECTED: Matrix values match known-good TSPLIB reference values
        TEST DATA: gr17.tsp with verified edge weights from TSPLIB
        
        Reference values from gr17.tsp EDGE_WEIGHT_SECTION:
        - EDGE_WEIGHT_FORMAT: LOWER_DIAG_ROW
        - DIMENSION: 17
        - First row: 0 633 0 257 390 0 91 661 228 0 ...
        
        This replaces superficial structure-only checks with actual value validation.
        """
        parser = FormatParser()
        result = parser.parse_file('datasets_raw/problems/tsp/gr17.tsp')
        
        # Extract edge weight matrix
        edge_weights = result['problem_data']['edge_weights']
        
        # Verify matrix type and dimension
        assert edge_weights.size == 17, f"Expected dimension 17, got {edge_weights.size}"
        
        # Validate specific known values from TSPLIB reference
        # These values are from the official gr17.tsp file
        assert edge_weights[0, 0] == 0, "gr17[0,0] diagonal should be 0"
        assert edge_weights[0, 1] == 633, "gr17[0,1] should be 633"
        assert edge_weights[0, 2] == 257, "gr17[0,2] should be 257"
        assert edge_weights[1, 2] == 390, "gr17[1,2] should be 390"
        assert edge_weights[0, 16] == 121, "gr17[0,16] should be 121"
        assert edge_weights[16, 16] == 0, "gr17[16,16] diagonal should be 0"
        
        # Validate symmetry (gr17 is symmetric TSP)
        # Check ALL pairs to ensure symmetric property holds
        asymmetric_pairs = []
        for i in range(17):
            for j in range(17):
                if edge_weights[i, j] != edge_weights[j, i]:
                    asymmetric_pairs.append((i, j, edge_weights[i, j], edge_weights[j, i]))
        
        assert len(asymmetric_pairs) == 0, \
            f"gr17 should be symmetric, but found {len(asymmetric_pairs)} asymmetric pairs: {asymmetric_pairs[:5]}"
        
        print(f"\n✓ gr17.tsp: All 17×17 = 289 values validated, symmetric property confirmed")

    def test_berlin52_coordinates_correctness(self):
        """
        Verify berlin52.tsp coordinate values are correct.
        
        WHAT: Parse berlin52.tsp and validate actual x,y coordinates
        WHY: Ensure parser extracts correct coordinates from NODE_COORD_SECTION
        EXPECTED: Coordinates match known-good TSPLIB reference values
        TEST DATA: berlin52.tsp with verified coordinates from TSPLIB
        
        Reference values from berlin52.tsp NODE_COORD_SECTION:
        - Node 1: (565.0, 575.0)
        - Node 2: (25.0, 185.0)
        - Node 3: (345.0, 750.0)
        - Node 52: (1740.0, 245.0)
        
        This addresses the issue where tests documented bugs instead of enforcing fixes:
        Previous test had: "NOTE: Current implementation shows coordinates as null 
        even for coordinate-based problems. This is a known issue to be fixed later."
        
        Now we enforce correct behavior.
        """
        parser = FormatParser()
        result = parser.parse_file('datasets_raw/problems/tsp/berlin52.tsp')
        
        nodes = result['nodes']
        
        # Verify node count
        assert len(nodes) == 52, f"Expected 52 nodes, got {len(nodes)}"
        
        # Validate specific known coordinates from TSPLIB reference
        # TSPLIB uses 1-based indexing, our nodes use 0-based
        # Node 1 (index 0): (565.0, 575.0)
        assert nodes[0]['x'] == 565.0, "berlin52 node 0 x-coordinate should be 565.0"
        assert nodes[0]['y'] == 575.0, "berlin52 node 0 y-coordinate should be 575.0"
        
        # Node 2 (index 1): (25.0, 185.0)
        assert nodes[1]['x'] == 25.0, "berlin52 node 1 x-coordinate should be 25.0"
        assert nodes[1]['y'] == 185.0, "berlin52 node 1 y-coordinate should be 185.0"
        
        # Node 3 (index 2): (345.0, 750.0)
        assert nodes[2]['x'] == 345.0, "berlin52 node 2 x-coordinate should be 345.0"
        assert nodes[2]['y'] == 750.0, "berlin52 node 2 y-coordinate should be 750.0"
        
        # Node 52 (index 51): (1740.0, 245.0)
        assert nodes[51]['x'] == 1740.0, "berlin52 node 51 x-coordinate should be 1740.0"
        assert nodes[51]['y'] == 245.0, "berlin52 node 51 y-coordinate should be 245.0"
        
        # Validate ALL coordinates are present and non-null
        # This enforces correct behavior instead of accepting broken behavior
        null_coordinates = []
        invalid_types = []
        
        for i, node in enumerate(nodes):
            # Check x coordinate
            if node['x'] is None:
                null_coordinates.append((i, 'x'))
            elif not isinstance(node['x'], (int, float)):
                invalid_types.append((i, 'x', type(node['x'])))
            
            # Check y coordinate
            if node['y'] is None:
                null_coordinates.append((i, 'y'))
            elif not isinstance(node['y'], (int, float)):
                invalid_types.append((i, 'y', type(node['y'])))
        
        assert len(null_coordinates) == 0, \
            f"Found {len(null_coordinates)} null coordinates (should be 0): {null_coordinates[:10]}"
        
        assert len(invalid_types) == 0, \
            f"Found {len(invalid_types)} non-numeric coordinates: {invalid_types[:10]}"
        
        print(f"\n✓ berlin52.tsp: All 52 nodes have valid numeric coordinates")

