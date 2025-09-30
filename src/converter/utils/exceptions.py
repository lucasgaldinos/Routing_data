"""Exception hierarchy for converter operations."""

class ConverterError(Exception):
    """Base exception for all converter operations."""
    pass

class FileProcessingError(ConverterError):
    """Raised when file processing fails."""
    def __init__(self, file_path: str, message: str):
        self.file_path = file_path
        super().__init__(f"Error processing {file_path}: {message}")

class ValidationError(ConverterError):
    """Raised when data validation fails."""
    pass

class DatabaseError(ConverterError):
    """Raised when database operations fail."""
    pass

class ParsingError(FileProcessingError):
    """Raised when TSPLIB parsing fails."""
    pass
