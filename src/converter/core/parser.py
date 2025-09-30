"""TSPLIB95 parser integration for ETL converter."""

from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import logging

from tsplib95 import loaders
from tsplib95.models import StandardProblem
from ..utils.exceptions import ParsingError, ValidationError
from ..utils.validation import validate_problem_data


class TSPLIBParser:
    """
    Parser for TSPLIB format files with complete extraction capabilities.
    
    Features:
    - Parse all TSPLIB problem types (TSP, VRP, ATSP, HCP, SOP, TOUR)
    - Handle SPECIAL distance types with custom functions
    - Extract nodes, edges, and metadata in normalized format
    - Convert 1-based TSPLIB indices to 0-based database format
    - Validate data integrity and problem structure
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize parser.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def parse_file(self, file_path: str, special_func: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Parse TSPLIB file and return complete normalized data structure.
        
        Args:
            file_path: Path to TSPLIB file
            special_func: Optional special distance function for SPECIAL edge types
            
        Returns:
            Dictionary with structure:
            {
                'problem_data': {...},  # Basic problem metadata
                'nodes': [...],         # Node coordinates and properties
                'edges': [...],         # Edge weights and properties 
                'tours': [...],         # Tour data if available
                'metadata': {...}       # File and processing metadata
            }
            
        Raises:
            ParsingError: If parsing fails
        """
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
                'tours': self._extract_tours(problem),
                'metadata': self._extract_metadata(problem, file_path)
            }
            
            self.logger.info(f"Successfully parsed {file_path}: {result['problem_data'].get('type')} "
                           f"with {len(result['nodes'])} nodes, {len(result['edges'])} edges")
            return result
            
        except Exception as e:
            raise ParsingError(file_path, str(e))
    
    def _extract_problem_data(self, problem: StandardProblem) -> Dict[str, Any]:
        """
        Extract basic problem metadata using as_name_dict() for clean data.
        
        Args:
            problem: StandardProblem instance
            
        Returns:
            Dictionary with problem metadata
        """
        # Use as_name_dict() to get clean data (excludes defaults)
        data = problem.as_name_dict()
        
        return {
            'name': data.get('name'),
            'type': data.get('type'),
            'comment': data.get('comment'),
            'dimension': data.get('dimension'),
            'capacity': data.get('capacity'),
            'edge_weight_type': data.get('edge_weight_type'),
            'edge_weight_format': data.get('edge_weight_format'),
            'node_coord_type': data.get('node_coord_type'),
            'display_data_type': data.get('display_data_type'),
        }
    
    def _extract_nodes(self, problem: StandardProblem) -> List[Dict[str, Any]]:
        """
        Extract node data with coordinates, demands, and depot information.
        
        Args:
            problem: StandardProblem instance
            
        Returns:
            List of node dictionaries with structure:
            {
                'node_id': int,      # 0-based index for database
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
        
        # Check if we have node coordinates
        if not hasattr(problem, 'node_coords') or not problem.node_coords:
            return nodes
        
        # Extract demands if available (VRP)
        demands = {}
        if hasattr(problem, 'demands') and problem.demands:
            demands = problem.demands
        
        # Extract depot information (VRP)
        depots = set()
        if hasattr(problem, 'depots') and problem.depots:
            depots = set(problem.depots) if isinstance(problem.depots, list) else {problem.depots}
        
        # Extract display data if available
        display_data = {}
        if hasattr(problem, 'display_data') and problem.display_data:
            display_data = problem.display_data
        
        # Iterate through node coordinates
        # TSPLIB uses 1-based indexing, convert to 0-based for database
        for tsplib_node_id, coords in problem.node_coords.items():
            node_id = tsplib_node_id - 1  # Convert to 0-based
            
            node = {
                'node_id': node_id,
                'x': coords[0] if len(coords) > 0 else None,
                'y': coords[1] if len(coords) > 1 else None,
                'z': coords[2] if len(coords) > 2 else None,
                'demand': demands.get(tsplib_node_id, 0),
                'is_depot': tsplib_node_id in depots,
            }
            
            # Add display coordinates if available
            if tsplib_node_id in display_data:
                display_coords = display_data[tsplib_node_id]
                node['display_x'] = display_coords[0] if len(display_coords) > 0 else None
                node['display_y'] = display_coords[1] if len(display_coords) > 1 else None
            
            nodes.append(node)
        
        return nodes
    
    def _extract_edges(self, problem: StandardProblem) -> List[Dict[str, Any]]:
        """
        Extract edge weights in normalized format.
        
        Args:
            problem: StandardProblem instance
            
        Returns:
            List of edge dictionaries with structure:
            {
                'from_node': int,    # 0-based normalized source node
                'to_node': int,      # 0-based normalized target node
                'weight': float,     # Edge weight/distance
                'is_fixed': bool     # True if edge is fixed
            }
        """
        edges = []
        
        try:
            # Get graph with normalized (0-based) node IDs
            graph = problem.get_graph(normalize=True)
            
            # Extract edges with data
            for from_node, to_node, edge_data in graph.edges(data=True):
                edge = {
                    'from_node': from_node,
                    'to_node': to_node,
                    'weight': edge_data.get('weight', 0),
                    'is_fixed': edge_data.get('is_fixed', False)
                }
                edges.append(edge)
        
        except Exception as e:
            self.logger.warning(f"Could not extract edges: {e}")
        
        return edges
    
    def _extract_tours(self, problem: StandardProblem) -> List[Dict[str, Any]]:
        """
        Extract tour data if available (from .tour files).
        
        Args:
            problem: StandardProblem instance
            
        Returns:
            List of tour dictionaries
        """
        tours = []
        
        if hasattr(problem, 'tours') and problem.tours:
            for idx, tour in enumerate(problem.tours):
                # Remove -1 terminators if present
                tour_nodes = [node - 1 for node in tour if node != -1]  # Convert to 0-based
                tours.append({
                    'tour_id': idx,
                    'nodes': tour_nodes
                })
        
        return tours
    
    def _extract_metadata(self, problem: StandardProblem, file_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive file and processing metadata.
        
        Args:
            problem: StandardProblem instance
            file_path: Path to file
            
        Returns:
            Dictionary with metadata
        """
        file_path_obj = Path(file_path)
        
        return {
            'file_path': str(file_path),
            'file_size': file_path_obj.stat().st_size if file_path_obj.exists() else 0,
            'file_name': file_path_obj.name,
            'problem_source': file_path_obj.parent.name,
            'has_coordinates': hasattr(problem, 'node_coords') and bool(problem.node_coords),
            'has_demands': hasattr(problem, 'demands') and bool(problem.demands),
            'has_depots': hasattr(problem, 'depots') and bool(problem.depots),
            'is_symmetric': self._check_symmetry(problem),
            'weight_source': self._identify_weight_source(problem)
        }
    
    def _check_symmetry(self, problem: StandardProblem) -> bool:
        """
        Determine if problem has symmetric distances.
        
        Args:
            problem: StandardProblem instance
            
        Returns:
            True if symmetric, False otherwise
        """
        # ATSP is explicitly asymmetric
        if hasattr(problem, 'type') and problem.type == 'ATSP':
            return False
        
        # Check edge weight format for symmetry indicators
        if hasattr(problem, 'edge_weight_format'):
            symmetric_formats = ['LOWER_DIAG_ROW', 'UPPER_DIAG_ROW', 'LOWER_ROW', 'UPPER_ROW']
            if problem.edge_weight_format in symmetric_formats:
                return True
        
        # Most TSP, VRP, HCP, SOP are symmetric by default
        return True
    
    def _identify_weight_source(self, problem: StandardProblem) -> str:
        """
        Identify how edge weights are determined.
        
        Args:
            problem: StandardProblem instance
            
        Returns:
            Source type: 'explicit_matrix', 'coordinate_based', or 'special_function'
        """
        if hasattr(problem, 'edge_weight_type'):
            edge_type = problem.edge_weight_type
            
            if edge_type == 'EXPLICIT':
                return 'explicit_matrix'
            elif edge_type == 'SPECIAL':
                return 'special_function'
            elif edge_type in ['EUC_2D', 'EUC_3D', 'MAX_2D', 'MAX_3D', 'MAN_2D', 'MAN_3D', 
                              'CEIL_2D', 'GEO', 'ATT', 'XRAY1', 'XRAY2']:
                return 'coordinate_based'
        
        return 'unknown'
    
    def validate_problem(self, problem: StandardProblem) -> None:
        """
        Comprehensive problem validation with specific error messages.
        
        Args:
            problem: StandardProblem instance
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(problem, StandardProblem):
            raise ValidationError("Not a valid StandardProblem")
        
        # Extract data for validation
        data = problem.as_name_dict()
        errors = validate_problem_data(data)
        
        # Additional structural validation
        if hasattr(problem, 'dimension') and problem.dimension:
            if hasattr(problem, 'node_coords') and problem.node_coords:
                if len(problem.node_coords) != problem.dimension:
                    errors.append(f"Node coordinate count {len(problem.node_coords)} "
                                f"doesn't match dimension {problem.dimension}")
        
        if errors:
            raise ValidationError(f"Validation errors: {'; '.join(errors)}")
    
    def detect_special_distance_type(self, file_path: str) -> bool:
        """
        Detect if file requires special distance function.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if SPECIAL distance type detected
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                return 'EDGE_WEIGHT_TYPE' in content and 'SPECIAL' in content
        except Exception:
            return False
