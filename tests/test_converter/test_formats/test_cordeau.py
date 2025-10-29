"""Tests for Cordeau MDVRP format converter."""
import logging
from pathlib import Path
import sys
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from tsplib_parser.cordeau import CordeauParser, CordeauConverter
from tsplib_parser.parser import FormatParser
from converter.core.transformer import DataTransformer
from converter.database.operations import DatabaseManager
from converter.output.json_writer import JSONWriter


# Test files specified by user
TEST_FILES = ['p01', 'p03', 'p08', 'pr05', 'p23']


@pytest.fixture
def cordeau_base_path():
    """Base path for Cordeau MDVRP test files."""
    return Path('datasets_raw/umalaga/mdvrp/C-mdvrp')


@pytest.fixture
def cordeau_parser():
    """Create Cordeau parser instance."""
    return CordeauParser(logger=logging.getLogger(__name__))


@pytest.fixture
def cordeau_converter():
    """Create Cordeau converter instance."""
    return CordeauConverter(logger=logging.getLogger(__name__))


@pytest.fixture
def format_parser():
    """Create TSPLIB95 format parser instance."""
    return FormatParser(logger=logging.getLogger(__name__))


@pytest.fixture
def temp_converted_dir(tmp_path):
    """Create temporary directory for converted files."""
    converted_dir = tmp_path / "converted"
    converted_dir.mkdir()
    return converted_dir


class TestCordeauParser:
    """Test Cordeau format parsing."""

    @pytest.mark.parametrize("filename", TEST_FILES)
    def test_parse_file(self, cordeau_base_path, cordeau_parser, filename):
        """Test parsing Cordeau file successfully."""
        file_path = cordeau_base_path / filename
        
        problem = cordeau_parser.parse_file(file_path)
        
        # Basic validation
        assert problem is not None
        assert problem.problem_type == 2  # MDVRP
        assert problem.num_vehicles > 0
        assert problem.num_customers > 0
        assert problem.num_depots > 0
        assert len(problem.nodes) == problem.num_customers + problem.num_depots
        assert len(problem.depot_constraints) == problem.num_depots

    def test_parse_p01_specific(self, cordeau_base_path, cordeau_parser):
        """Test p01 specific values."""
        problem = cordeau_parser.parse_file(cordeau_base_path / 'p01')
        
        # p01 is a well-known benchmark, verify key properties
        assert problem.num_vehicles == 4
        assert problem.num_customers == 50
        assert problem.num_depots == 4
        
        # Check customers have demands
        customers = problem.customer_nodes
        assert all(node.demand > 0 for node in customers)
        
        # Check depots have no demands
        depots = problem.depot_nodes
        assert all(node.demand == 0 for node in depots)
        assert all(node.is_depot for node in depots)

    def test_invalid_file(self, cordeau_parser, tmp_path):
        """Test parsing invalid file raises error."""
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("not a valid cordeau file\n")
        
        with pytest.raises(Exception):
            cordeau_parser.parse_file(invalid_file)


class TestCordeauConverter:
    """Test Cordeau to TSPLIB95 conversion."""

    @pytest.mark.parametrize("filename", TEST_FILES)
    def test_convert_to_tsplib95(self, cordeau_base_path, cordeau_parser, 
                                  cordeau_converter, filename):
        """Test conversion to TSPLIB95 format."""
        # Parse Cordeau file
        problem = cordeau_parser.parse_file(cordeau_base_path / filename)
        
        # Convert to TSPLIB95
        tsplib_content = cordeau_converter.to_tsplib95(problem)
        
        # Basic validation
        assert tsplib_content is not None
        assert "NAME" in tsplib_content
        assert "TYPE" in tsplib_content
        assert "DIMENSION" in tsplib_content
        assert "EDGE_WEIGHT_TYPE" in tsplib_content
        assert "CAPACITY" in tsplib_content
        assert "NODE_COORD_SECTION" in tsplib_content
        assert "DEMAND_SECTION" in tsplib_content
        assert "DEPOT_SECTION" in tsplib_content
        assert "EOF" in tsplib_content

    @pytest.mark.parametrize("filename", TEST_FILES)
    def test_convert_with_output_file(self, cordeau_base_path, cordeau_parser,
                                       cordeau_converter, temp_converted_dir, filename):
        """Test conversion with file output."""
        # Parse Cordeau file
        problem = cordeau_parser.parse_file(cordeau_base_path / filename)
        
        # Convert with output file
        output_path = temp_converted_dir / f"{filename}.vrp"
        tsplib_content = cordeau_converter.to_tsplib95(problem, output_path=output_path)
        
        # Check file was created
        assert output_path.exists()
        
        # Check file content matches returned content
        file_content = output_path.read_text()
        assert file_content == tsplib_content

    def test_convert_p01_specific(self, cordeau_base_path, cordeau_parser, 
                                    cordeau_converter):
        """Test p01 specific conversion details."""
        problem = cordeau_parser.parse_file(cordeau_base_path / 'p01')
        tsplib_content = cordeau_converter.to_tsplib95(problem)
        
        # Check dimension (customers + depots)
        assert f"DIMENSION : {problem.dimension}" in tsplib_content
        
        # Check depot section lists all depots
        lines = tsplib_content.split('\n')
        depot_section_start = None
        for i, line in enumerate(lines):
            if line.strip() == "DEPOT_SECTION":
                depot_section_start = i
                break
        
        assert depot_section_start is not None
        
        # Count depot entries (should be num_depots + terminator -1)
        depot_entries = []
        for line in lines[depot_section_start + 1:]:
            line = line.strip()
            if not line or line == "EOF":
                break
            try:
                depot_entries.append(int(line))
            except ValueError:
                break
        
        # Last entry should be -1
        assert depot_entries[-1] == -1
        # Number of actual depot IDs should match num_depots
        assert len(depot_entries) - 1 == problem.num_depots


class TestCordeauIntegration:
    """Test integration with existing pipeline."""

    @pytest.mark.parametrize("filename", TEST_FILES)
    def test_tsplib95_parser_accepts_converted(self, cordeau_base_path, cordeau_parser,
                                                 cordeau_converter, format_parser,
                                                 temp_converted_dir, filename):
        """Test that converted TSPLIB95 can be parsed by existing parser."""
        # Parse Cordeau file
        problem = cordeau_parser.parse_file(cordeau_base_path / filename)
        
        # Convert to TSPLIB95 file
        output_path = temp_converted_dir / f"{filename}.vrp"
        cordeau_converter.to_tsplib95(problem, output_path=output_path)
        
        # Parse with existing TSPLIB95 parser
        parsed_data = format_parser.parse_file(output_path)
        
        # Validate parsed data
        assert parsed_data is not None
        assert 'problem_data' in parsed_data
        assert parsed_data['problem_data']['name'] == filename
        assert parsed_data['problem_data']['type'] == 'CVRP'
        assert parsed_data['problem_data']['dimension'] == problem.dimension
        # Capacity: use max capacity from depot constraints
        expected_capacity = max(c.max_load for c in problem.depot_constraints)
        assert parsed_data['problem_data']['capacity'] == expected_capacity

    @pytest.mark.parametrize("filename", TEST_FILES)
    def test_transformer_processes_converted(self, cordeau_base_path, cordeau_parser,
                                               cordeau_converter, format_parser,
                                               temp_converted_dir, filename):
        """Test that transformer can process converted problem."""
        # Parse Cordeau file
        problem = cordeau_parser.parse_file(cordeau_base_path / filename)
        
        # Convert to TSPLIB95 file
        output_path = temp_converted_dir / f"{filename}.vrp"
        cordeau_converter.to_tsplib95(problem, output_path=output_path)
        
        # Parse with existing TSPLIB95 parser
        parsed_data = format_parser.parse_file(output_path)
        
        # Transform
        transformer = DataTransformer(logger=logging.getLogger(__name__))
        transformed = transformer.transform_problem(parsed_data)
        
        # Validate transformation
        assert transformed is not None
        assert 'problem_data' in transformed
        assert 'nodes' in transformed
        assert len(transformed['nodes']) == problem.dimension
        assert transformed['problem_data']['name'] == filename
        assert transformed['problem_data']['type'] == 'CVRP'
        assert transformed['problem_data']['dimension'] == problem.dimension

    def test_full_pipeline_p01(self, cordeau_base_path, cordeau_parser,
                                cordeau_converter, format_parser, in_memory_db,
                                temp_converted_dir):
        """Test full pipeline: Parse → Convert → Parse → Transform → DB."""
        filename = 'p01'
        
        # Step 1: Parse Cordeau file
        problem = cordeau_parser.parse_file(cordeau_base_path / filename)
        
        # Step 2: Convert to TSPLIB95 file
        output_path = temp_converted_dir / f"{filename}.vrp"
        cordeau_converter.to_tsplib95(problem, output_path=output_path)
        
        # Step 3: Parse with existing TSPLIB95 parser
        parsed_data = format_parser.parse_file(output_path)
        
        # Step 4: Transform
        transformer = DataTransformer(logger=logging.getLogger(__name__))
        transformed = transformer.transform_problem(parsed_data)
        
        # Step 5: Insert to database
        db_manager = DatabaseManager(
            db_path=in_memory_db,
            logger=logging.getLogger(__name__)
        )
        db_manager.insert_problem(transformed)
        
        # Step 6: Verify in database
        import duckdb
        conn = duckdb.connect(str(in_memory_db))
        result = conn.execute(
            "SELECT name, type, dimension, capacity, depots, vehicles FROM problems WHERE name = ?",
            [filename]
        ).fetchone()
        
        assert result is not None
        assert result[0] == filename  # name
        assert result[1] == 'CVRP'     # type
        assert result[2] == problem.dimension
        assert result[3] == problem.capacity
        assert result[4] == problem.num_depots
        assert result[5] == problem.num_vehicles
        
        conn.close()

    def test_json_output_p01(self, cordeau_base_path, cordeau_parser,
                              cordeau_converter, format_parser, temp_converted_dir):
        """Test JSON output generation."""
        filename = 'p01'
        
        # Parse and convert
        problem = cordeau_parser.parse_file(cordeau_base_path / filename)
        output_path = temp_converted_dir / f"{filename}.vrp"
        cordeau_converter.to_tsplib95(problem, output_path=output_path)
        
        # Parse with existing parser
        parsed_data = format_parser.parse_file(output_path)
        
        # Transform
        transformer = DataTransformer(logger=logging.getLogger(__name__))
        transformed = transformer.transform_problem(parsed_data)
        
        # Write JSON
        json_output_dir = temp_converted_dir / "json"
        json_output_dir.mkdir()
        json_writer = JSONWriter(
            output_dir=json_output_dir,
            logger=logging.getLogger(__name__)
        )
        json_writer.write_problem(transformed)
        
        # Verify JSON file created
        json_file = json_output_dir / f"{filename}.json"
        assert json_file.exists()
        
        # Verify JSON content
        import json
        with open(json_file) as f:
            json_data = json.load(f)
        
        assert json_data['name'] == filename
        assert json_data['type'] == 'CVRP'
        assert json_data['dimension'] == problem.dimension
        assert json_data['capacity'] == problem.capacity
