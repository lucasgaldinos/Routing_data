import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .utils.exceptions import ConfigurationError


@dataclass
class ConverterConfig:
    """Configuration settings for TSPLIB converter."""
    
    # Input settings
    input_path: str = "./datasets_raw/problems"
    file_patterns: List[str] = field(default_factory=lambda: [
        "*.tsp", "*.vrp", "*.atsp", "*.hcp", "*.sop", "*.tour"
    ])
    
    # Output settings  
    database_path: str = "./datasets/db/routing.duckdb"
    
    # Processing settings
    batch_size: int = 100
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = "./logs/converter.log"
    
    def validate(self) -> List[str]:
        """Validate configuration settings."""
        errors = []
        
        # Validate paths
        if not self.input_path:
            errors.append("input_path cannot be empty")
        
        if not self.database_path:
            errors.append("database_path cannot be empty")
            
        # Validate batch size
        if self.batch_size <= 0:
            errors.append("batch_size must be positive")
        elif self.batch_size > 10000:
            errors.append("batch_size too large (max: 10,000)")
            
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_levels:
            errors.append(f"Invalid log_level: {self.log_level} (valid: {', '.join(valid_levels)})")
            
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'input_path': self.input_path,
            'file_patterns': self.file_patterns,
            'database_path': self.database_path,
            'batch_size': self.batch_size,
            'log_level': self.log_level,
            'log_file': self.log_file
        }


def load_config(config_path: str = "config.yaml") -> ConverterConfig:
    """
    Load configuration from YAML file with validation.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Validated configuration object
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    config_path_obj = Path(config_path)
    
    if config_path_obj.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {config_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error reading config file {config_path}: {e}")
        
        # Merge with defaults
        default_config = ConverterConfig()
        merged_config = {}
        
        for key, default_value in default_config.to_dict().items():
            merged_config[key] = config_dict.get(key, default_value)
            
        config = ConverterConfig(**merged_config)
    else:
        # Use defaults if no config file exists
        config = ConverterConfig()
    
    # Validate configuration
    errors = config.validate()
    if errors:
        raise ConfigurationError(f"Configuration validation failed: {'; '.join(errors)}")
    
    return config


def save_config(config: ConverterConfig, config_path: str = "config.yaml") -> None:
    """
    Save configuration to YAML file.
    
    Args:
        config: Configuration object to save
        config_path: Path where to save configuration
    """
    config_path_obj = Path(config_path)
    config_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                config.to_dict(), 
                f, 
                default_flow_style=False, 
                indent=2,
                sort_keys=True
            )
    except Exception as e:
        raise ConfigurationError(f"Error saving configuration to {config_path}: {e}")
