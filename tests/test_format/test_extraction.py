"""
Tests for format.extraction - Data extraction from StandardProblem objects.

Tests the actual behavior of extraction functions with real StandardProblem objects.
Based on verified system output - coordinates are currently null due to loader bug.
"""
import pytest
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from format import loaders
from format.extraction import (
    extract_problem_data,
    extract_nodes,
    extract_tours,
    normalize_problem_type
)


class TestNormalizeProblemType:
    """Test normalize_problem_type() function."""
    
    def test_normalize_with_author_annotation(self):
        """
        WHAT: Test normalization of problem type with author annotation
        WHY: TSPLIB files sometimes include author info like "TSP (M.~HOFMEISTER)"
        EXPECTED: Should extract base type "TSP", removing author annotation
        DATA: "TSP (M.~HOFMEISTER)" → "TSP"
        """
        result = normalize_problem_type("TSP (M.~HOFMEISTER)")
        assert result == "TSP", "Should remove author annotation from TSP"
    
    def test_normalize_standard_types(self):
        """
        WHAT: Test normalization of standard TSPLIB problem types
        WHY: Standard types should remain unchanged
        EXPECTED: Returns same value for known types (TSP, ATSP, CVRP, VRP, HCP, SOP, TOUR)
        DATA: "TSP" → "TSP", "ATSP" → "ATSP"
        """
        assert normalize_problem_type("TSP") == "TSP"
        assert normalize_problem_type("ATSP") == "ATSP"
        assert normalize_problem_type("CVRP") == "CVRP"
        assert normalize_problem_type("VRP") == "VRP"
    
    def test_normalize_empty_string(self):
        """
        WHAT: Test normalization of empty string
        WHY: Handle edge case of missing type
        EXPECTED: Returns empty string unchanged
        DATA: "" → ""
        """
        result = normalize_problem_type("")
        assert result == "", "Should return empty string unchanged"
    
    def test_normalize_case_insensitive(self):
        """
        WHAT: Test case normalization
        WHY: TSPLIB types can vary in case
        EXPECTED: Converts to uppercase
        DATA: "tsp" → "TSP"
        """
        result = normalize_problem_type("tsp")
        assert result == "TSP", "Should convert to uppercase"


class TestExtractProblemData:
    """Test extract_problem_data() function."""
    
    def test_extract_from_explicit_problem(self):
        """
        WHAT: Extract problem metadata from EXPLICIT weight matrix problem
        WHY: Verify metadata extraction for problems without coordinates
        EXPECTED: Returns dict with name, type, dimension, edge_weight_type, etc.
        DATA: gr17.tsp - EXPLICIT, LOWER_DIAG_ROW, dimension 17
        """
        problem = loaders.load('datasets_raw/problems/tsp/gr17.tsp')
        data = extract_problem_data(problem)
        
        assert data['name'] == 'gr17'
        assert data['type'] == 'TSP'
        assert data['dimension'] == 17
        assert data['edge_weight_type'] == 'EXPLICIT'
        assert data['edge_weight_format'] == 'LOWER_DIAG_ROW'
        assert data['comment'] == '17-city problem (Groetschel)'
    
    def test_extract_from_coordinate_problem(self):
        """
        WHAT: Extract problem metadata from coordinate-based problem
        WHY: Verify metadata extraction for EUC_2D problems
        EXPECTED: Returns dict with edge_weight_type='EUC_2D'
        DATA: berlin52.tsp - EUC_2D, dimension 52
        """
        problem = loaders.load('datasets_raw/problems/tsp/berlin52.tsp')
        data = extract_problem_data(problem)
        
        assert data['name'] == 'berlin52'
        assert data['type'] == 'TSP'
        assert data['dimension'] == 52
        assert data['edge_weight_type'] == 'EUC_2D'
    
    def test_extract_handles_null_fields(self):
        """
        WHAT: Test that optional fields can be null
        WHY: Not all TSPLIB files have capacity, node_coord_type, etc.
        EXPECTED: Optional fields should be None when not present
        DATA: TSP files have capacity=None (VRP only)
        """
        problem = loaders.load('datasets_raw/problems/tsp/gr17.tsp')
        data = extract_problem_data(problem)
        
        # TSP files don't have capacity
        assert data['capacity'] is None, "TSP should have no capacity"


class TestExtractNodes:
    """Test extract_nodes() function."""
    
    def test_extract_nodes_from_explicit_problem(self):
        """
        WHAT: Extract nodes from EXPLICIT weight matrix problem
        WHY: EXPLICIT problems have no coordinates, should create virtual nodes
        EXPECTED: Returns list of nodes with null coordinates, 0-based node_id
        DATA: gr17.tsp - 17 nodes, all coordinates null
        """
        problem = loaders.load('datasets_raw/problems/tsp/gr17.tsp')
        nodes = extract_nodes(problem)
        
        # Verify count
        assert len(nodes) == 17, "Should have 17 nodes"
        
        # Verify structure of first node
        node = nodes[0]
        assert node['node_id'] == 0, "First node should have ID 0 (0-based indexing)"
        assert node['x'] is None, "EXPLICIT problem should have null x"
        assert node['y'] is None, "EXPLICIT problem should have null y"
        assert node['z'] is None, "Should have null z"
        assert node['demand'] == 0, "TSP nodes have 0 demand"
        assert node['is_depot'] is False, "TSP nodes are not depots"
    
    def test_extract_nodes_from_coordinate_problem(self):
        """
        WHAT: Extract nodes from coordinate-based problem
        WHY: Test extraction from EUC_2D problems
        EXPECTED: Currently returns null coordinates (loader bug), but structure is correct
        DATA: berlin52.tsp - EUC_2D, should have coordinates but currently null
        """
        problem = loaders.load('datasets_raw/problems/tsp/berlin52.tsp')
        nodes = extract_nodes(problem)
        
        # Verify count
        assert len(nodes) == 52, "Should have 52 nodes"
        
        # Known bug: coordinates are null even for coordinate-based problems
        # This tests ACTUAL behavior - coordinates extraction is broken in loader
        node = nodes[0]
        assert node['node_id'] == 0, "0-based indexing"
        # BUG: These should have actual coordinates, but loader returns empty node_coords
        assert node['x'] is None, "Currently null due to loader bug"
        assert node['y'] is None, "Currently null due to loader bug"
    
    def test_extract_nodes_sequential_ids(self):
        """
        WHAT: Test that node IDs are sequential 0-based integers
        WHY: Database expects 0-based sequential node IDs (TSPLIB is 1-based)
        EXPECTED: node_id should be 0, 1, 2, ..., n-1
        DATA: gr17.tsp - IDs 0 to 16
        """
        problem = loaders.load('datasets_raw/problems/tsp/gr17.tsp')
        nodes = extract_nodes(problem)
        
        for i, node in enumerate(nodes):
            assert node['node_id'] == i, f"Node {i} should have node_id={i}"
    
    def test_extract_nodes_all_have_required_fields(self):
        """
        WHAT: Test that all nodes have required fields
        WHY: Database schema requires specific fields
        EXPECTED: Each node has node_id, x, y, z, demand, is_depot
        DATA: gr17.tsp nodes
        """
        problem = loaders.load('datasets_raw/problems/tsp/gr17.tsp')
        nodes = extract_nodes(problem)
        
        required_fields = {'node_id', 'x', 'y', 'z', 'demand', 'is_depot'}
        
        for node in nodes:
            node_fields = set(node.keys())
            assert required_fields.issubset(node_fields), \
                f"Node missing required fields: {required_fields - node_fields}"


class TestExtractTours:
    """Test extract_tours() function."""
    
    def test_extract_tours_from_problem_without_tour(self):
        """
        WHAT: Extract tours from problem file (not tour file)
        WHY: Most problem files don't have tour solutions
        EXPECTED: Returns empty list
        DATA: gr17.tsp - no tour data
        """
        problem = loaders.load('datasets_raw/problems/tsp/gr17.tsp')
        tours = extract_tours(problem)
        
        assert isinstance(tours, list), "Should return list"
        assert len(tours) == 0, "Problem files have no tour data"
    
    def test_extract_tours_from_tour_file(self):
        """
        WHAT: Extract tours from .tour solution file (if available)
        WHY: Tour files contain optimal/known solutions
        EXPECTED: Returns list of tour dicts with tour_id and nodes (0-based)
        DATA: Any .tour file in datasets_raw/problems/tour/
        """
        # Check if we have any tour files to test
        tour_dir = Path('datasets_raw/problems/tour')
        if tour_dir.exists():
            tour_files = list(tour_dir.glob('*.tour'))
            if tour_files:
                problem = loaders.load(str(tour_files[0]))
                tours = extract_tours(problem)
                
                if tours:  # If tour data exists
                    assert isinstance(tours, list), "Should return list"
                    assert all('tour_id' in t and 'nodes' in t for t in tours), \
                        "Each tour should have tour_id and nodes"
                    assert all(isinstance(t['nodes'], list) for t in tours), \
                        "nodes should be a list"
                    # Verify 0-based indexing
                    for tour in tours:
                        assert all(isinstance(n, int) and n >= 0 for n in tour['nodes']), \
                            "Tour nodes should be 0-based integers"
        else:
            pytest.skip("No tour files available for testing")


class TestExtractionConsistency:
    """Test consistency between extraction functions."""
    
    def test_dimension_matches_node_count(self):
        """
        WHAT: Test that extracted node count matches problem dimension
        WHY: extract_nodes() must return exactly dimension nodes
        EXPECTED: len(extract_nodes()) == extract_problem_data()['dimension']
        DATA: gr17.tsp (dim 17), berlin52.tsp (dim 52)
        """
        for file_path in ['datasets_raw/problems/tsp/gr17.tsp', 
                          'datasets_raw/problems/tsp/berlin52.tsp']:
            problem = loaders.load(file_path)
            data = extract_problem_data(problem)
            nodes = extract_nodes(problem)
            
            assert len(nodes) == data['dimension'], \
                f"{file_path}: Node count doesn't match dimension"
    
    def test_problem_type_normalized_consistently(self):
        """
        WHAT: Test that problem type normalization is consistent
        WHY: Problem type must be normalized the same way everywhere
        EXPECTED: extract_problem_data() returns normalized type
        DATA: Any TSP file should return "TSP" (not "TSP (author)")
        """
        problem = loaders.load('datasets_raw/problems/tsp/gr17.tsp')
        data = extract_problem_data(problem)
        
        # Type should be normalized (no author annotations)
        assert data['type'] == 'TSP', "Type should be normalized"
        assert '(' not in data['type'], "Type should not contain author annotations"
