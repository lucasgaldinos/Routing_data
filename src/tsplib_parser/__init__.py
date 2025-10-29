# -*- coding: utf-8 -*-

"""
TSPLIB95 Format Parsing Module

Unified parsing system for TSPLIB95 routing problem files.
Provides both high-level (FormatParser) and low-level (StandardProblem) APIs.

Architecture
------------
**Primary API** (Recommended):
    - parser.py: FormatParser class - High-level ETL parsing with validation
    
**Low-level API** (Internal/Advanced):
    - models.py: StandardProblem, Field system - Raw TSPLIB95 parsing
    - loaders.py: File loading functions (load, parse_tsplib)
    - extraction.py: Data extraction utilities
    - validation.py: Validation functions

**Support Modules**:
    - exceptions.py: FormatError, ParseError, ValidationError hierarchy

Primary Usage (Recommended)
----------------------------
```python
from src.format.parser import FormatParser

parser = FormatParser(logger)
data = parser.parse_file('problem.vrp')
# Returns: {'problem_data': {...}, 'nodes': [...], 'tours': [...]}
```

Alternative Usage (Low-level)
------------------------------
```python
from src.format import parse_tsplib, StandardProblem

# Direct parsing
problem = parse_tsplib('problem.tsp')  # Returns StandardProblem
data_dict = problem.as_name_dict()     # Convert to dict
```

Version & Metadata
------------------
"""

__version__ = '2.0.0'  # Updated for FormatParser refactoring
__author__ = 'TCC Routing Data Project'

# ============================================================================
# Public API Exports
# ============================================================================

# Core parsing components (internal modules)
from . import models
from . import exceptions
from . import validation

# Primary exports (recommended for external use)
from .models import StandardProblem
from .exceptions import FormatError, ParseError, ValidationError

# Validation utilities
from .validation import validate_problem_data, validate_coordinates


# ========================================================================
# DEPRECATED: Legacy Loader Functions
# ========================================================================
# These functions are deprecated and will be removed in a future version.
# Use FormatParser instead (see parser.py).
#
# Migration guide:
#   OLD: from tsplib_parser import parse_tsplib, load
#   NEW: from tsplib_parser.parser import FormatParser
#        parser = FormatParser()
#        result = parser.parse_file('file.tsp')
# ========================================================================

import warnings
from pathlib import Path
from typing import Union, Optional, Callable

def parse_tsplib(
    filepath: Union[str, Path],
    problem_class: Optional[type] = None,
    special: Optional[Callable] = None
) -> StandardProblem:
    """
    DEPRECATED: Use FormatParser instead.
    
    Parse a TSPLIB95 format file.
    
    .. deprecated:: 1.0
        Use :class:`FormatParser` instead. This function will be removed in version 2.0.
    """
    warnings.warn(
        "parse_tsplib() is deprecated. Use FormatParser.parse_file() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    Problem = problem_class or StandardProblem
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    return Problem.parse(text, special=special)


def load(filepath, problem_class=None, special=None):
    """
    DEPRECATED: Use FormatParser instead.
    
    Load a problem at the given filepath.
    
    .. deprecated:: 1.0
        Use :class:`FormatParser` instead. This function will be removed in version 2.0.
    """
    warnings.warn(
        "load() is deprecated. Use FormatParser.parse_file() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return parse_tsplib(filepath, problem_class=problem_class, special=special)


__all__ = [
    # ========================================================================
    # PRIMARY API (Recommended)
    # ========================================================================
    'StandardProblem',        # Core data structure
    'FormatError',            # Base exception
    'ParseError',             # Parsing errors
    'ValidationError',        # Validation errors
    
    # ========================================================================
    # VALIDATION (Public utilities)
    # ========================================================================
    'validate_problem_data',  
    'validate_coordinates',
    
    # ========================================================================
    # LEGACY (DEPRECATED - for backward compatibility only)
    # ========================================================================
    'load',                   # DEPRECATED: use parse_tsplib (kept for compatibility)
]

# Note: FormatParser is imported separately to avoid circular imports:
#   from src.format.parser import FormatParser
# This is the RECOMMENDED high-level API for ETL operations.