import pytest
import tempfile
import logging
from pathlib import Path

from src.converter.utils.logging import setup_logging, get_logger
from src.converter.utils.exceptions import (
    ConverterError, ValidationError, ParsingError, 
    DatabaseError, ConfigurationError
)
from src.converter.utils.validation import (
    validate_problem_data, validate_coordinates, 
    validate_file_path, validate_node_data
)
from src.converter.config import ConverterConfig, load_config, save_config


def test_logging_setup():
    """Test logging configuration."""
    logger = setup_logging("DEBUG")
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) >= 1
    
    # Test component logger
    component_logger = get_logger("test")
    assert component_logger.name == "converter.test"


def test_exception_hierarchy():
    """Test exception inheritance."""
    assert issubclass(ValidationError, ConverterError)
    assert issubclass(ParsingError, ConverterError)
    assert issubclass(DatabaseError, ConverterError)
    
    # Test ParsingError with file path
    error = ParsingError("test.tsp", "Test error")
    assert "test.tsp" in str(error)


def test_problem_data_validation():
    """Test problem data validation."""
    # Valid data
    valid_data = {
        'name': 'test_problem',
        'type': 'TSP',
        'dimension': 10
    }
    errors = validate_problem_data(valid_data)
    assert len(errors) == 0
    
    # Invalid data
    invalid_data = {
        'name': '',  # Empty name
        'type': 'UNKNOWN',  # Invalid type
        'dimension': -5  # Invalid dimension
    }
    errors = validate_problem_data(invalid_data)
    assert len(errors) == 3


def test_coordinate_validation():
    """Test coordinate validation."""
    # Valid coordinates
    valid_coords = [(0, 0), (1, 1), (2, 2)]
    assert validate_coordinates(valid_coords) == True
    
    # Empty coordinates (valid)
    assert validate_coordinates([]) == True
    
    # Invalid coordinates
    invalid_coords = [(0,), (1, 'invalid')]  # Missing y, invalid type
    assert validate_coordinates(invalid_coords) == False


def test_file_validation():
    """Test file path validation."""
    # Test non-existent file
    errors = validate_file_path("nonexistent.tsp")
    assert len(errors) > 0
    assert "does not exist" in errors[0]
    
    # Test with real file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tsp', delete=False) as f:
        f.write("NAME: test\nTYPE: TSP\nDIMENSION: 3\n")
        f.flush()
        
        errors = validate_file_path(f.name)
        assert len(errors) == 0
        
        Path(f.name).unlink()  # Clean up


def test_configuration():
    """Test configuration management."""
    # Test default config
    config = ConverterConfig()
    errors = config.validate()
    assert len(errors) == 0
    
    # Test invalid config
    invalid_config = ConverterConfig(batch_size=-1, log_level="INVALID")
    errors = invalid_config.validate()
    assert len(errors) >= 2
    
    # Test save/load cycle
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = f"{temp_dir}/test_config.yaml"
        
        original_config = ConverterConfig(batch_size=50)
        save_config(original_config, config_path)
        
        loaded_config = load_config(config_path)
        assert loaded_config.batch_size == 50
