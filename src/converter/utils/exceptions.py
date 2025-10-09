"""Exception hierarchy for ETL converter operations.

This module defines converter-specific exceptions for the ETL pipeline phases:
extraction, transformation, database operations, and output generation.

Exception Hierarchy
-------------------
ConverterError (base)
├── ExtractionError - Data extraction failures from parsed TSPLIB
├── TransformError - Data transformation/normalization failures  
├── DatabaseError - DuckDB operations failures
└── OutputError - JSON/file output failures

These exceptions are separate from format.exceptions (parsing errors) to maintain
clean separation between parsing (format/) and ETL conversion (converter/).
"""

from typing import Optional


class ConverterError(Exception):
    """Base exception for all ETL converter operations.
    
    This is the base class for all converter-specific exceptions. Use subclasses
    for specific error types (extraction, transformation, database, output).
    
    Parameters
    ----------
    message : str
        Human-readable error description
    *args : Any
        Additional positional arguments passed to Exception base class
        
    Examples
    --------
    >>> raise ConverterError("Generic converter failure")
    Traceback (most recent call last):
    ...
    ConverterError: Generic converter failure
    
    >>> try:
    ...     raise ConverterError("Failed to process")
    ... except ConverterError as e:
    ...     print(f"Caught: {e}")
    Caught: Failed to process
    
    Notes
    -----
    Prefer using specific subclasses (ExtractionError, TransformError, etc.) 
    rather than raising ConverterError directly.
    """
    
    def __init__(self, message: str, *args: object) -> None:
        """Initialize converter error with message."""
        super().__init__(message, *args)
        self.message = message


class ExtractionError(ConverterError):
    """Exception raised during data extraction from parsed TSPLIB problems.
    
    Raised when extracting nodes, edges, or tours from StandardProblem fails
    due to missing data, invalid structure, or extraction logic errors.
    
    Parameters
    ----------
    message : str
        Description of extraction failure
    problem_name : str, optional
        Name of the problem that failed extraction
    *args : Any
        Additional arguments
        
    Attributes
    ----------
    problem_name : str or None
        Problem name if provided
        
    Examples
    --------
    >>> raise ExtractionError("Missing node coordinates", problem_name="gr17")
    Traceback (most recent call last):
    ...
    ExtractionError: Missing node coordinates
    
    >>> try:
    ...     raise ExtractionError("Failed to extract edges", "att532")
    ... except ExtractionError as e:
    ...     print(f"{e.problem_name}: {e}")
    att532: Failed to extract edges
    
    Notes
    -----
    Used in extraction logic that converts StandardProblem data to database format.
    Distinct from format.ParseError which occurs during file parsing.
    """
    
    def __init__(self, message: str, problem_name: Optional[str] = None, *args: object) -> None:
        """Initialize extraction error with optional problem context."""
        if problem_name:
            full_message = f"[{problem_name}] {message}"
        else:
            full_message = message
        super().__init__(full_message, *args)
        self.problem_name = problem_name


class TransformError(ConverterError):
    """Exception raised during data transformation operations.
    
    Raised when normalizing data, converting indices (1-based to 0-based),
    or applying transformations to extracted data fails.
    
    Parameters
    ----------
    message : str
        Description of transformation failure
    field_name : str, optional
        Name of the field that failed transformation
    *args : Any
        Additional arguments
        
    Attributes
    ----------
    field_name : str or None
        Field name if provided
        
    Examples
    --------
    >>> raise TransformError("Invalid dimension value", field_name="dimension")
    Traceback (most recent call last):
    ...
    TransformError: Invalid dimension value (field: dimension)
    
    >>> try:
    ...     raise TransformError("Index conversion failed", "edge_weights")
    ... except TransformError as e:
    ...     print(f"Transform error: {e}")
    Transform error: Index conversion failed (field: edge_weights)
    
    Notes
    -----
    Used in DataTransformer for normalization, validation, and conversion logic.
    """
    
    def __init__(self, message: str, field_name: Optional[str] = None, *args: object) -> None:
        """Initialize transform error with optional field context."""
        if field_name:
            full_message = f"{message} (field: {field_name})"
        else:
            full_message = message
        super().__init__(full_message, *args)
        self.field_name = field_name


class DatabaseError(ConverterError):
    """Exception raised during DuckDB database operations.
    
    Raised when database creation, connection, insertion, query, or other
    DuckDB operations fail.
    
    Parameters
    ----------
    message : str
        Description of database operation failure
    operation : str, optional
        The database operation that failed (e.g., 'INSERT', 'CREATE TABLE')
    *args : Any
        Additional arguments
        
    Attributes
    ----------
    operation : str or None
        Database operation if provided
        
    Examples
    --------
    >>> raise DatabaseError("Connection failed", operation="CONNECT")
    Traceback (most recent call last):
    ...
    DatabaseError: Connection failed (operation: CONNECT)
    
    >>> try:
    ...     raise DatabaseError("Duplicate key violation", "INSERT")
    ... except DatabaseError as e:
    ...     print(f"DB error during {e.operation}: {e}")
    DB error during INSERT: Duplicate key violation (operation: INSERT)
    
    Notes
    -----
    Used in DatabaseManager for all DuckDB-related operations.
    """
    
    def __init__(self, message: str, operation: Optional[str] = None, *args: object) -> None:
        """Initialize database error with optional operation context."""
        if operation:
            full_message = f"{message} (operation: {operation})"
        else:
            full_message = message
        super().__init__(full_message, *args)
        self.operation = operation


class OutputError(ConverterError):
    """Exception raised during output file generation.
    
    Raised when writing JSON files, creating output directories, or other
    file I/O operations fail.
    
    Parameters
    ----------
    message : str
        Description of output operation failure
    file_path : str, optional
        Path to the file that failed
    *args : Any
        Additional arguments
        
    Attributes
    ----------
    file_path : str or None
        File path if provided
        
    Examples
    --------
    >>> raise OutputError("Write failed", file_path="/tmp/output.json")
    Traceback (most recent call last):
    ...
    OutputError: Write failed (file: /tmp/output.json)
    
    >>> try:
    ...     raise OutputError("Directory creation failed", "/output/dir")
    ... except OutputError as e:
    ...     print(f"Output error: {e}")
    Output error: Directory creation failed (file: /output/dir)
    
    Notes
    -----
    Used in JSONWriter and other output generation components.
    """
    
    def __init__(self, message: str, file_path: Optional[str] = None, *args: object) -> None:
        """Initialize output error with optional file path context."""
        if file_path:
            full_message = f"{message} (file: {file_path})"
        else:
            full_message = message
        super().__init__(full_message, *args)
        self.file_path = file_path


__all__ = [
    'ConverterError',
    'ExtractionError',
    'TransformError',
    'DatabaseError',
    'OutputError',
]
