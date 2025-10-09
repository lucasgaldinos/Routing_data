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
from . import loaders
from . import exceptions
from . import validation
from . import extraction

# Primary exports (recommended for external use)
from .loaders import parse_tsplib
from .models import StandardProblem
from .exceptions import FormatError, ParseError, ValidationError

# Validation utilities
from .validation import validate_problem_data, validate_coordinates

# Extraction utilities (for advanced use)
from .extraction import (
    extract_problem_data,
    extract_nodes,
    extract_tours,
    extract_metadata,
    normalize_problem_type,
    check_symmetry,
    identify_weight_source,
)

# Legacy compatibility - keep load() for backward compatibility
from .loaders import load

__all__ = [
    # ========================================================================
    # PRIMARY API (Recommended)
    # ========================================================================
    'parse_tsplib',           # Main parsing function - use this!
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
    # EXTRACTION (Advanced use)
    # ========================================================================
    'extract_problem_data',
    'extract_nodes',
    'extract_tours',
    'extract_metadata',
    'normalize_problem_type',
    'check_symmetry',
    'identify_weight_source',
    
    # ========================================================================
    # LEGACY (DEPRECATED - for backward compatibility only)
    # ========================================================================
    'load',                   # DEPRECATED: use parse_tsplib (kept for compatibility)
]

# Note: FormatParser is imported separately to avoid circular imports:
#   from src.format.parser import FormatParser
# This is the RECOMMENDED high-level API for ETL operations.