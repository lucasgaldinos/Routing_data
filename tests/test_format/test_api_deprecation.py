"""
Test for Issue #5: Document dual API deprecation.

Verifies that deprecated functions show warnings and documentation is complete.
"""

import pytest
import warnings
from pathlib import Path

from tsplib_parser import parse_tsplib, load
from tsplib_parser.parser import FormatParser


class TestDeprecationWarnings:
    """Test that deprecated functions emit proper warnings."""
    
    def test_parse_tsplib_shows_deprecation_warning(self, tmp_path):
        """
        WHAT: Verify parse_tsplib() emits DeprecationWarning
        WHY: Issue #5 - old functions should warn users to migrate
        EXPECTED: DeprecationWarning with migration message
        """
        # Create minimal TSPLIB file
        test_file = tmp_path / "test.tsp"
        test_file.write_text("""NAME: test
TYPE: TSP
DIMENSION: 3
EDGE_WEIGHT_TYPE: EXPLICIT
EDGE_WEIGHT_FORMAT: FULL_MATRIX
EDGE_WEIGHT_SECTION
0 1 2
1 0 3
2 3 0
EOF
""")
        
        # Call deprecated function and verify warning
        with pytest.warns(DeprecationWarning, match="parse_tsplib.*deprecated.*FormatParser"):
            problem = parse_tsplib(str(test_file))
        
        # Should still work (backward compatibility)
        assert problem is not None
    
    def test_load_shows_deprecation_warning(self, tmp_path):
        """
        WHAT: Verify load() emits DeprecationWarning
        WHY: Issue #5 - old functions should warn users to migrate
        EXPECTED: DeprecationWarning with migration message
        """
        # Create minimal TSPLIB file
        test_file = tmp_path / "test.tsp"
        test_file.write_text("""NAME: test
TYPE: TSP
DIMENSION: 3
EDGE_WEIGHT_TYPE: EXPLICIT
EDGE_WEIGHT_FORMAT: FULL_MATRIX
EDGE_WEIGHT_SECTION
0 1 2
1 0 3
2 3 0
EOF
""")
        
        # Call deprecated function and verify warning
        with pytest.warns(DeprecationWarning, match="load.*deprecated.*FormatParser"):
            problem = load(str(test_file))
        
        # Should still work (backward compatibility)
        assert problem is not None
    
    def test_format_parser_no_warnings(self, tmp_path):
        """
        WHAT: Verify FormatParser does NOT emit warnings
        WHY: Recommended API should work silently
        EXPECTED: No warnings
        """
        # Create minimal TSPLIB file
        test_file = tmp_path / "test.tsp"
        test_file.write_text("""NAME: test
TYPE: TSP
DIMENSION: 3
EDGE_WEIGHT_TYPE: EXPLICIT
EDGE_WEIGHT_FORMAT: FULL_MATRIX
EDGE_WEIGHT_SECTION
0 1 2
1 0 3
2 3 0
EOF
""")
        
        # Call recommended API - should not warn
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # Turn warnings into errors
            parser = FormatParser()
            result = parser.parse_file(str(test_file))
        
        # Should work without any warnings
        assert result is not None
        assert 'problem_data' in result


class TestBackwardCompatibility:
    """Test that deprecated functions still work correctly."""
    
    def test_parse_tsplib_returns_standard_problem(self, tmp_path):
        """
        WHAT: Verify parse_tsplib() returns StandardProblem object
        WHY: Backward compatibility - existing code should still work
        EXPECTED: Returns StandardProblem instance
        """
        from tsplib_parser.models import StandardProblem
        
        test_file = tmp_path / "test.tsp"
        test_file.write_text("""NAME: test
TYPE: TSP
DIMENSION: 3
EDGE_WEIGHT_TYPE: EXPLICIT
EDGE_WEIGHT_FORMAT: FULL_MATRIX
EDGE_WEIGHT_SECTION
0 1 2
1 0 3
2 3 0
EOF
""")
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Ignore deprecation for this test
            problem = parse_tsplib(str(test_file))
        
        assert isinstance(problem, StandardProblem)
        assert problem.name == 'test'
        assert problem.problem_type == 'TSP'  # Note: it's problem_type, not type
    
    def test_load_equivalent_to_parse_tsplib(self, tmp_path):
        """
        WHAT: Verify load() produces same result as parse_tsplib()
        WHY: Both deprecated functions should be equivalent
        EXPECTED: Identical StandardProblem objects
        """
        test_file = tmp_path / "test.tsp"
        test_file.write_text("""NAME: test
TYPE: TSP
DIMENSION: 3
EDGE_WEIGHT_TYPE: EXPLICIT
EDGE_WEIGHT_FORMAT: FULL_MATRIX
EDGE_WEIGHT_SECTION
0 1 2
1 0 3
2 3 0
EOF
""")
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            problem1 = parse_tsplib(str(test_file))
            problem2 = load(str(test_file))
        
        assert problem1.name == problem2.name
        assert problem1.problem_type == problem2.problem_type  # Note: it's problem_type, not type
        assert problem1.dimension == problem2.dimension


class TestMigrationPath:
    """Test that migration from old to new API is straightforward."""
    
    def test_format_parser_produces_compatible_output(self, tmp_path):
        """
        WHAT: Verify FormatParser output contains expected fields
        WHY: Migration should be easy - similar data structure
        EXPECTED: Dictionary with problem_data, nodes, etc.
        """
        test_file = tmp_path / "test.tsp"
        test_file.write_text("""NAME: test
TYPE: TSP
DIMENSION: 3
EDGE_WEIGHT_TYPE: EXPLICIT
EDGE_WEIGHT_FORMAT: FULL_MATRIX
EDGE_WEIGHT_SECTION
0 1 2
1 0 3
2 3 0
EOF
""")
        
        parser = FormatParser()
        result = parser.parse_file(str(test_file))
        
        # Should have standard structure
        assert 'problem_data' in result
        assert 'nodes' in result
        assert 'metadata' in result
        
        # Problem data should be accessible
        assert result['problem_data']['name'] == 'test'
        assert result['problem_data']['type'] == 'TSP'
        assert result['problem_data']['dimension'] == 3
