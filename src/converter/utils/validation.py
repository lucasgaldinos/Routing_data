from typing import Dict, Any, List
from pathlib import Path


def validate_problem_data(data: Dict[str, Any]) -> List[str]:
    """
    Validate extracted problem data structure.
    
    Args:
        data: Problem data dictionary from parser
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Required fields
    if not data.get('name'):
        errors.append("Problem name is required")
    if not data.get('type'):
        errors.append("Problem type is required")
        
    # Dimension validation
    dimension = data.get('dimension')
    if not isinstance(dimension, int) or dimension <= 0:
        errors.append("Dimension must be positive integer")
    elif dimension > 100000:  # Reasonable upper limit
        errors.append(f"Dimension too large: {dimension} (max: 100,000)")
    
    # Type-specific validation
    problem_type = data.get('type', '').upper()
    valid_types = ['TSP', 'VRP', 'ATSP', 'HCP', 'SOP', 'TOUR']
    if problem_type not in valid_types:
        errors.append(f"Unknown problem type: {problem_type} (valid: {', '.join(valid_types)})")
    
    return errors


def validate_coordinates(coords: List[tuple]) -> bool:
    """
    Validate coordinate data structure.
    
    Args:
        coords: List of coordinate tuples
        
    Returns:
        True if coordinates are valid
    """
    if not coords:
        return True  # Empty coordinates are valid
    
    return all(
        isinstance(coord, (tuple, list)) and 
        len(coord) >= 2 and 
        all(isinstance(x, (int, float)) for x in coord[:3])  # Support 2D and 3D
        for coord in coords
    )


def validate_file_path(file_path: str) -> List[str]:
    """
    Validate file accessibility and basic properties.
    
    Args:
        file_path: Path to file to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    try:
        path = Path(file_path)
        
        if not path.exists():
            errors.append(f"File does not exist: {file_path}")
            return errors  # No point checking further
            
        if not path.is_file():
            errors.append(f"Path is not a file: {file_path}")
            return errors
            
        # File size checks
        file_size = path.stat().st_size
        if file_size == 0:
            errors.append(f"File is empty: {file_path}")
        elif file_size > 100 * 1024 * 1024:  # 100MB limit
            errors.append(f"File too large (>100MB): {file_path}")
            
        # Check if file is readable
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1)  # Try to read first character
        except UnicodeDecodeError:
            errors.append(f"File encoding not supported (expected UTF-8): {file_path}")
        except PermissionError:
            errors.append(f"File not readable (permission denied): {file_path}")
            
    except Exception as e:
        errors.append(f"Error validating file {file_path}: {e}")
    
    return errors


def validate_node_data(nodes: List[Dict[str, Any]], expected_dimension: int) -> List[str]:
    """
    Validate node data consistency.
    
    Args:
        nodes: List of node dictionaries
        expected_dimension: Expected number of nodes
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    if len(nodes) != expected_dimension:
        errors.append(f"Node count {len(nodes)} doesn't match dimension {expected_dimension}")
    
    # Check for required fields and data types
    for i, node in enumerate(nodes):
        if not isinstance(node.get('node_id'), int):
            errors.append(f"Node {i}: node_id must be integer")
            
        # Coordinate validation (can be None)
        x, y = node.get('x'), node.get('y')
        if x is not None and not isinstance(x, (int, float)):
            errors.append(f"Node {i}: x coordinate must be numeric")
        if y is not None and not isinstance(y, (int, float)):
            errors.append(f"Node {i}: y coordinate must be numeric")
    
    return errors
