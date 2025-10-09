# -*- coding: utf-8 -*-
"""Unified TSPLIB95 file loader - single clear interface."""

from pathlib import Path
from typing import Union, Optional, Callable

from . import models


def parse_tsplib(
    filepath: Union[str, Path],
    problem_class: Optional[type] = None,
    special: Optional[Callable] = None
) -> models.StandardProblem:
    """
    Parse a TSPLIB95 format file.
    
    Single unified function following Unix philosophy: do one thing well.
    Replaces the confusing trio of load(), read(), parse().
    
    Parameters
    ----------
    filepath : str or Path
        Path to TSPLIB95 problem file (.tsp, .vrp, .atsp, etc.)
    problem_class : type, optional
        Custom problem class (defaults to StandardProblem)
    special : callable, optional
        Custom distance function for SPECIAL edge weight types
        
    Returns
    -------
    StandardProblem
        Parsed problem instance with nodes, edges, and metadata
        
    Raises
    ------
    FileNotFoundError
        If file doesn't exist
    IOError
        If file can't be read
    ParseError
        If TSPLIB format is invalid
        
    Examples
    --------
    >>> from format import parse_tsplib
    >>> problem = parse_tsplib('datasets/gr17.tsp')
    >>> problem.dimension
    17
    
    >>> # With custom distance function
    >>> def custom_distance(a, b):
    ...     return abs(a - b)
    >>> problem = parse_tsplib('special.tsp', special=custom_distance)
    """
    Problem = problem_class or models.StandardProblem
    
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    return Problem.parse(text, special=special)


# Backward compatibility - will be deprecated
def load(filepath, problem_class=None, special=None):
    """
    DEPRECATED: Use parse_tsplib() instead.
    
    Load a problem at the given filepath.
    """
    return parse_tsplib(filepath, problem_class=problem_class, special=special)

