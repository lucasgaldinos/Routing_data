from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple
import logging

from src.tsplib95 import loaders
from src.tsplib95.models import StandardProblem
from ..utils.exceptions import ParsingError, ValidationError
from ..utils.validation import validate_problem_data, validate_file_path

class TSPLIBParser:
    """
    Parser for TSPLIB format files with complete extraction capabilities.
    
    This is the core component that integrates with the vendored tsplib95 library
    to parse TSPLIB files and extract normalized data for database storage.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def parse_file(self, file_path: str, special_func: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Parse TSPLIB file and return complete normalized data structure.
        
        Args:
            file_path: Path to TSPLIB file
            special_func: Custom distance function for SPECIAL edge weight types
            
        Returns:
            Complete problem data ready for database insertion:
            {
                'problem_data': Dict[str, Any],  # Basic problem metadata
                'nodes': List[Dict[str, Any]],   # Node coordinates and properties
                'edges': List[Dict[str, Any]],   # Edge weights and properties 
                'metadata': Dict[str, Any]       # File and processing metadata
            }
        """
        # Validate file first
        file_errors = validate_file_path(file_path)
        if file_errors:
            raise ParsingError(file_path, f"File validation failed: {'; '.join(file_errors)}")
        
        try:
            # Load using tsplib95 with special distance handling
            problem = loaders.load(file_path, special=special_func)
            
            # Validate the loaded problem
            self.validate_problem(problem)
            
            # Extract all components
            result = {
                'problem_data': self._extract_problem_data(problem),
                'nodes': self._extract_nodes(problem),
                'edges': self._extract_edges(problem), 
                'metadata': self._extract_metadata(problem, file_path)
            }
            
            self.logger.info(f"Successfully parsed {file_path}: {result['problem_data'].get('type')} "
                           f"with {len(result['nodes'])} nodes, {len(result['edges'])} edges")
            return result
            
        except Exception as e:
            if isinstance(e, ParsingError):
                raise
            raise ParsingError(file_path, str(e))
    
    def _extract_problem_data(self, problem: StandardProblem) -> Dict[str, Any]:
        """Extract basic problem metadata using as_name_dict() for clean data."""
        # Get clean data (excludes defaults)
        data = problem.as_name_dict()
        
        # Ensure required fields are present
        if 'name' not in data:
            data['name'] = getattr(problem, 'name', 'unknown')
        if 'type' not in data:
            data['type'] = getattr(problem, 'type', 'UNKNOWN')
        if 'dimension' not in data:
            data['dimension'] = getattr(problem, 'dimension', 0)
            
        return data
    
    def _extract_nodes(self, problem: StandardProblem) -> List[Dict[str, Any]]:
        """
        Extract node data with coordinates, demands, and depot information.
        
        Returns list of nodes with structure:
        {
            'node_id': int,      # Original 1-based TSPLIB ID
            'x': float,          # X coordinate
            'y': float,          # Y coordinate  
            'z': float,          # Z coordinate (if 3D)
            'demand': int,       # Node demand (VRP)
            'is_depot': bool,    # True if depot node (VRP)
            'display_x': float,  # Display coordinates if different
            'display_y': float
        }
        """
        nodes = []
        
        # Get coordinates if available
        coords = getattr(problem, 'node_coords', None) or {}
        demands = getattr(problem, 'demands', None) or {}
        depots = getattr(problem, 'depots', None) or []
        display_coords = getattr(problem, 'display_data', None) or {}
        
        # Get dimension - this is the number of nodes
        dimension = getattr(problem, 'dimension', 0)
        
        # If dimension is set but we have no coordinates, still create nodes
        # (e.g., for EXPLICIT edge weight problems like gr17)
        if dimension > 0:
            for node_id in range(1, dimension + 1):
                coord = coords.get(node_id, [])
                display_coord = display_coords.get(node_id, [])
                
                node_data = {
                    'node_id': node_id,  # Keep original 1-based TSPLIB ID
                    'x': coord[0] if len(coord) > 0 else None,
                    'y': coord[1] if len(coord) > 1 else None,
                    'z': coord[2] if len(coord) > 2 else None,
                    'demand': demands.get(node_id, 0),
                    'is_depot': node_id in depots,
                    'display_x': display_coord[0] if len(display_coord) > 0 else None,
                    'display_y': display_coord[1] if len(display_coord) > 1 else None
                }
                nodes.append(node_data)
        
        return nodes
    
    def _extract_edges(self, problem: StandardProblem) -> List[Dict[str, Any]]:
        """
        Extract edge weights in normalized format.
        
        Returns list of edges with structure:
        {
            'from_node': int,    # 0-based normalized source node
            'to_node': int,      # 0-based normalized target node
            'weight': float,     # Edge weight/distance
            'is_fixed': bool     # True if edge is fixed (from FIXED_EDGES_SECTION)
        }
        """
        edges = []
        
        try:
            # Get normalized graph (0-based indexing)
            graph = problem.get_graph(normalize=True)
            
            # Extract edges from graph
            for from_node, to_node, edge_data in graph.edges(data=True):
                edge = {
                    'from_node': from_node,  # Already 0-based from normalize=True
                    'to_node': to_node,      # Already 0-based from normalize=True
                    'weight': edge_data.get('weight', 0.0),
                    'is_fixed': edge_data.get('is_fixed', False)
                }
                edges.append(edge)
                
        except Exception as e:
            self.logger.warning(f"Could not extract edges from graph: {e}")
            # For some problem types, edges might not be available
            
        return edges
    
    def _extract_metadata(self, problem: StandardProblem, file_path: str) -> Dict[str, Any]:
        """Extract comprehensive file and processing metadata."""
        file_path_obj = Path(file_path)
        
        return {
            'file_path': str(file_path),
            'file_size': file_path_obj.stat().st_size if file_path_obj.exists() else 0,
            'file_name': file_path_obj.name,
            'problem_source': file_path_obj.parent.name,
            'has_coordinates': hasattr(problem, 'node_coords') and bool(getattr(problem, 'node_coords', None)),
            'has_demands': hasattr(problem, 'demands') and bool(getattr(problem, 'demands', None)),
            'has_depots': hasattr(problem, 'depots') and bool(getattr(problem, 'depots', None)),
            'edge_weight_type': getattr(problem, 'edge_weight_type', None),
            'edge_weight_format': getattr(problem, 'edge_weight_format', None)
        }
    
    def validate_problem(self, problem: StandardProblem) -> None:
        """Comprehensive problem validation with specific error messages."""
        if not isinstance(problem, StandardProblem):
            raise ValidationError("Not a valid StandardProblem")
        
        # Extract data for validation
        data = problem.as_name_dict()
        errors = validate_problem_data(data)
        
        # Additional structural validation
        if hasattr(problem, 'dimension') and problem.dimension:
            if hasattr(problem, 'node_coords') and problem.node_coords:
                coord_count = len(problem.node_coords)
                if coord_count > 0 and coord_count != problem.dimension:
                    errors.append(f"Node coordinate count {coord_count} "
                                f"doesn't match dimension {problem.dimension}")
        
        if errors:
            raise ValidationError(f"Validation errors: {'; '.join(errors)}")
    
    def detect_special_distance_type(self, file_path: str) -> bool:
        """Detect if file requires special distance function."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().upper()
                return 'EDGE_WEIGHT_TYPE' in content and 'SPECIAL' in content
        except Exception:
            return False
