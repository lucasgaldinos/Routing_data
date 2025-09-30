from typing import Dict, Any, List

def validate_problem_data(data: Dict[str, Any]) -> List[str]:
    """Validate extracted problem data. Returns list of error messages."""
    errors = []
    
    # Required fields
    if not data.get('name'):
        errors.append("Problem name is required")
    if not data.get('type'):
        errors.append("Problem type is required")
    if not isinstance(data.get('dimension'), int) or data['dimension'] <= 0:
        errors.append("Dimension must be positive integer")
    
    # Type-specific validation
    problem_type = data.get('type', '').upper()
    # Support standard TSPLIB types plus CVRP
    if problem_type not in ['TSP', 'VRP', 'CVRP', 'ATSP', 'HCP', 'SOP', 'TOUR']:
        errors.append(f"Unknown problem type: {problem_type}")
    
    return errors

def validate_coordinates(coords: List[tuple]) -> bool:
    """Validate coordinate data."""
    if not coords:
        return True  # Empty coordinates are valid
    
    return all(
        isinstance(coord, (tuple, list)) and len(coord) >= 2 and 
        all(isinstance(x, (int, float)) for x in coord[:2])
        for coord in coords
    )

def validate_file_path(file_path: str) -> List[str]:
    """Validate file accessibility and basic properties."""
    errors = []
    from pathlib import Path
    
    path = Path(file_path)
    if not path.exists():
        errors.append(f"File does not exist: {file_path}")
    elif not path.is_file():
        errors.append(f"Path is not a file: {file_path}")
    elif path.stat().st_size == 0:
        errors.append(f"File is empty: {file_path}")
    elif path.stat().st_size > 100 * 1024 * 1024:  # 100MB limit
        errors.append(f"File too large (>100MB): {file_path}")
    
    return errors
