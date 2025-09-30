import yaml
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, field

@dataclass
class ConverterConfig:
    """Configuration for TSPLIB converter."""
    # Input settings
    input_path: str = "./datasets_raw/problems"
    file_patterns: List[str] = field(default_factory=lambda: ["*.tsp", "*.vrp", "*.atsp", "*.hcp", "*.sop", "*.tour"])
    
    # Output settings  
    database_path: str = "./datasets/db/routing.duckdb"
    
    # Processing settings
    batch_size: int = 100
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/converter.log"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'input_path': self.input_path,
            'file_patterns': self.file_patterns,
            'database_path': self.database_path,
            'batch_size': self.batch_size,
            'log_level': self.log_level,
            'log_file': self.log_file
        }

def load_config(config_path: str = "config.yaml") -> ConverterConfig:
    """Load configuration from YAML file."""
    if Path(config_path).exists():
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Handle missing keys gracefully
        valid_config = {}
        default_config = ConverterConfig()
        
        for key, default_value in default_config.to_dict().items():
            valid_config[key] = config_dict.get(key, default_value)
            
        return ConverterConfig(**valid_config)
    
    return ConverterConfig()

def save_config(config: ConverterConfig, config_path: str = "config.yaml"):
    """Save configuration to YAML file."""
    config_path_obj = Path(config_path)
    config_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        yaml.safe_dump(config.to_dict(), f, default_flow_style=False, indent=2)
