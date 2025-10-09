"""Data validation functions for converter operations.

Re-exports validation functions from src.format for converter use.
These are primarily for validating extracted/transformed data before database insertion.
"""

from format.validation import (
    validate_problem_data,
    validate_coordinates,
)


def validate_problem_type(problem_type: str) -> bool:
    """Validate problem type is supported.
    
    Parameters
    ----------
    problem_type : str
        Problem type to validate (e.g., 'TSP', 'VRP', 'ATSP')
    
    Returns
    -------
    bool
        True if problem type is supported, False otherwise
        
    Examples
    --------
    >>> validate_problem_type('TSP')
    True
    >>> validate_problem_type('INVALID')
    False
    """
    known_types = {'TSP', 'VRP', 'ATSP', 'HCP', 'SOP', 'TOUR', 'CVRP'}
    return problem_type.upper() in known_types


def validate_file_size(file_path: str, max_size_mb: int = 100) -> bool:
    """Validate file size is within acceptable limits.
    
    Parameters
    ----------
    file_path : str
        Path to file to validate
    max_size_mb : int, optional
        Maximum file size in megabytes (default: 100)
    
    Returns
    -------
    bool
        True if file size is acceptable, False otherwise
        
    Examples
    --------
    >>> validate_file_size('small.tsp', max_size_mb=10)  # doctest: +SKIP
    True
    """
    from pathlib import Path
    
    path = Path(file_path)
    if not path.exists():
        return False
    
    size_mb = path.stat().st_size / (1024 * 1024)
    return size_mb <= max_size_mb


__all__ = [
    'validate_problem_data',
    'validate_problem_type',
    'validate_coordinates',
    'validate_file_size',
]
