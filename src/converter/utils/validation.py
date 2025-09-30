"""Data validation functions for converter operations."""

from typing import Dict, Any, List


def validate_problem_data(data: Dict[str, Any]) -> List[str]:
    """
    Validate extracted problem data.
    
    Args:
        data: Problem data dictionary
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Required fields
    if not data.get('name'):
        errors.append("Problem name is required")
    if not data.get('type'):
        errors.append("Problem type is required")
    if not isinstance(data.get('dimension'), int) or data.get('dimension', 0) <= 0:
        errors.append("Dimension must be positive integer")
    
    # Type-specific validation
    problem_type = data.get('type', '').upper()
    if problem_type not in ['TSP', 'VRP', 'ATSP', 'HCP', 'SOP', 'TOUR']:
        errors.append(f"Unknown problem type: {problem_type}")
    
    return errors


def validate_coordinates(coords: List[tuple]) -> bool:
    """
    Validate coordinate data.
    
    Args:
        coords: List of coordinate tuples
        
    Returns:
        True if coordinates are valid
    """
    return all(
        isinstance(coord, (tuple, list)) and len(coord) >= 2
        for coord in coords
    )


def validate_file_size(file_path: str, max_size_mb: int = 100) -> bool:
    """
    Validate file size is within limits.
    
    Args:
        file_path: Path to file
        max_size_mb: Maximum file size in MB
        
    Returns:
        True if file size is acceptable
    """
    import os
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return size_mb <= max_size_mb
    except OSError:
        return False
