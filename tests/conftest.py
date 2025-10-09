"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from typing import Generator, Dict, List, Any
import tempfile
import shutil


@pytest.fixture
def test_data_dir() -> Path:
    """Path to test data directory containing TSPLIB files."""
    return Path(__file__).parent.parent / 'datasets_raw' / 'problems'


@pytest.fixture
def tsp_files_small(test_data_dir: Path) -> Dict[str, Path]:
    """Small TSP test files (< 100 nodes) with different characteristics."""
    return {
        'gr17': test_data_dir / 'tsp' / 'gr17.tsp',        # 17 nodes, EUC_2D
        'att48': test_data_dir / 'tsp' / 'att48.tsp',      # 48 nodes, ATT distance
        'berlin52': test_data_dir / 'tsp' / 'berlin52.tsp', # 52 nodes, EUC_2D
    }


@pytest.fixture
def tsp_files_medium(test_data_dir: Path) -> Dict[str, Path]:
    """Medium TSP test files (100-1000 nodes)."""
    return {
        'a280': test_data_dir / 'tsp' / 'a280.tsp',        # 280 nodes
        'att532': test_data_dir / 'tsp' / 'att532.tsp',    # 532 nodes
    }


@pytest.fixture
def atsp_files(test_data_dir: Path) -> Dict[str, Path]:
    """ATSP test files (asymmetric TSP)."""
    return {
        'br17': test_data_dir / 'atsp' / 'br17.atsp',      # 17 nodes, small
        'p43': test_data_dir / 'atsp' / 'p43.atsp',        # 43 nodes
        'ftv170': test_data_dir / 'atsp' / 'ftv170.atsp',  # 170 nodes, medium
    }


@pytest.fixture
def vrp_files(test_data_dir: Path) -> Dict[str, Path]:
    """VRP test files with demands."""
    return {
        'eil7': test_data_dir / 'vrp' / 'eil7.vrp',        # 7 nodes, tiny
        'eil13': test_data_dir / 'vrp' / 'eil13.vrp',      # 13 nodes, small
        'eil51': test_data_dir / 'vrp' / 'eil51.vrp',      # 51 nodes, medium
    }


@pytest.fixture
def gr17_tsp(test_data_dir: Path) -> str:
    """Path to gr17.tsp test file (17-city TSP, symmetric, EUC_2D)."""
    tsp_path = test_data_dir / 'tsp' / 'gr17.tsp'
    if not tsp_path.exists():
        pytest.skip(f"Test file not found: {tsp_path}")
    return str(tsp_path)


@pytest.fixture
def temp_output_dir() -> Generator[str, None, None]:
    """Temporary output directory for test file operations."""
    temp_dir = tempfile.mkdtemp(prefix='test_routing_')
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def in_memory_db():
    """In-memory DuckDB database for testing without file I/O."""
    from src.converter.database.operations import DatabaseManager
    # Use :memory: for in-memory database
    db = DatabaseManager(':memory:')
    yield db
    # Database automatically cleaned up when object is destroyed


@pytest.fixture
def sample_problem_data() -> Dict[str, Any]:
    """Sample TSPLIB problem data for testing."""
    return {
        'name': 'test_problem',
        'type': 'TSP',
        'comment': 'Test problem for unit tests',
        'dimension': 5,
        'edge_weight_type': 'EUC_2D',
        'node_coord_type': 'TWOD_COORDS'
    }


@pytest.fixture
def sample_nodes() -> List[Dict[str, Any]]:
    """Sample node coordinates for testing."""
    return [
        {'node_id': 1, 'x': 0.0, 'y': 0.0},
        {'node_id': 2, 'x': 1.0, 'y': 0.0},
        {'node_id': 3, 'x': 1.0, 'y': 1.0},
        {'node_id': 4, 'x': 0.0, 'y': 1.0},
        {'node_id': 5, 'x': 0.5, 'y': 0.5},
    ]


@pytest.fixture
def malformed_tsp_content() -> str:
    """Malformed TSPLIB content for error handling tests."""
    return """NAME: malformed
TYPE: TSP
DIMENSION: 3
NODE_COORD_SECTION
1 invalid data here
2 3.0
This is not a valid line
EOF
"""
