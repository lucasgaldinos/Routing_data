"""Data transformation for TSPLIB converter."""

from typing import Dict, Any, List, Optional
import logging
import re
import itertools
from pathlib import Path

from tsplib_parser import matrix

class DataTransformer:
    """
    Data transformation for TSPLIB converter.
    
    Features:
    - Normalize data for database/JSON storage
    - Format conversion and validation
    - Metadata enrichment
    - Index normalization (1-based to 0-based)
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize transformer.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def transform_problem(
        self,
        problem_data: Dict[str, Any],
        file_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Transform parsed problem data for storage.
        
        Args:
            problem_data: Parsed problem data from parser
            file_info: Optional file metadata
            
        Returns:
            Transformed data ready for storage
        """
        # Extract components
        problem_meta = problem_data.get('problem_data', {})
        nodes = problem_data.get('nodes', [])
        tours = problem_data.get('tours', [])
        metadata = problem_data.get('metadata', {})
        
        # Add file info to metadata if provided
        if file_info:
            metadata.update({
                'scanned_file_path': file_info.get('file_path'),
                'scanned_file_size': file_info.get('file_size'),
                'detected_type': file_info.get('problem_type')
            })
        
        # Ensure all nodes have required fields
        normalized_nodes = self._normalize_nodes(nodes)
        
        # Process edge weights if present (EXPLICIT problems)
        edge_weight_matrix = None
        if 'edge_weights' in problem_meta and problem_meta['edge_weights']:
            try:
                edge_weight_matrix = self._convert_edge_weights_to_matrix(
                    edge_weights=problem_meta['edge_weights'],
                    edge_weight_format=problem_meta.get('edge_weight_format'),
                    dimension=problem_meta.get('dimension')
                )
                self.logger.info(
                    f"Converted edge weights to {len(edge_weight_matrix)}×"
                    f"{len(edge_weight_matrix[0])} matrix"
                )
            except Exception as e:
                self.logger.warning(f"Failed to convert edge weights: {e}")
                # Re-raise in debug mode for troubleshooting
                import traceback
                self.logger.debug(traceback.format_exc())
                edge_weight_matrix = None
            
            # Remove raw edge_weights from problem_meta (don't store parsed data)
            del problem_meta['edge_weights']
        
        # Build final structure
        result = {
            'problem_data': self._enrich_problem_data(problem_meta, metadata),
            'nodes': normalized_nodes,
            'tours': tours,
            'metadata': metadata
        }
        
        # Add edge weight matrix if converted successfully
        if edge_weight_matrix is not None:
            result['edge_weight_matrix'] = edge_weight_matrix
        
        return result
    
    def _normalize_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize node data with consistent field structure.
        
        Args:
            nodes: List of node dictionaries
            
        Returns:
            List of normalized node dictionaries
        """
        return [
            {
                'node_id': node.get('node_id', 0),
                'x': node.get('x'),
                'y': node.get('y'),
                'z': node.get('z'),
                'demand': node.get('demand', 0),
                'is_depot': node.get('is_depot', False),
                'display_x': node.get('display_x'),
                'display_y': node.get('display_y')
            }
            for node in nodes
        ]
    
    def _convert_edge_weights_to_matrix(
        self,
        edge_weights,
        edge_weight_format: str,
        dimension: int
    ) -> List[List[float]]:
        """Convert edge weights to full 2D matrix.
        
        Args:
            edge_weights: Matrix object or List[List[float]] from parser
            edge_weight_format: Matrix format (FULL_MATRIX, LOWER_DIAG_ROW, etc.)
            dimension: Problem dimension (number of nodes)
            
        Returns:
            Full 2D matrix as list of lists (dimension × dimension)
        """
        # If already a Matrix object, extract full 2D matrix directly
        if isinstance(edge_weights, matrix.Matrix):
            # Use the matrix's actual size (may differ from dimension for VRP customer-only matrices)
            matrix_size = edge_weights.size
            matrix_2d = [
                [edge_weights.value_at(i, j) for j in range(matrix_size)]
                for i in range(matrix_size)
            ]
            self.logger.debug(
                f"Extracted matrix from Matrix object: format={edge_weight_format}, "
                f"problem_dimension={dimension}, matrix_size={matrix_size}"
            )
            return matrix_2d
        
        # Otherwise, handle List[List] (legacy path)
        weights = list(itertools.chain(*edge_weights))
        
        self.logger.debug(
            f"Converting edge weights: format={edge_weight_format}, "
            f"dimension={dimension}, total_weights={len(weights)}"
        )
        
        # Get appropriate Matrix class for format
        if edge_weight_format not in matrix.TYPES:
            raise ValueError(
                f"Unsupported edge weight format: {edge_weight_format}. "
                f"Supported: {list(matrix.TYPES.keys())}"
            )
        
        MatrixClass = matrix.TYPES[edge_weight_format]
        
        # Create Matrix instance (0-based indexing for database)
        m = MatrixClass(weights, dimension, min_index=0)
        
        # Extract full 2D matrix
        matrix_2d = [
            [m.value_at(i, j) for j in range(dimension)]
            for i in range(dimension)
        ]
        
        self.logger.debug(
            f"Successfully converted to {dimension}×{dimension} matrix"
        )
        
        return matrix_2d

    
    def _enrich_problem_data(
        self,
        problem_meta: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich problem metadata with additional information.
        
        Args:
            problem_meta: Basic problem metadata
            metadata: File and processing metadata
            
        Returns:
            Enriched problem metadata
        """
        enriched = problem_meta.copy()
        
        # Add file path and size from metadata
        if 'file_path' in metadata:
            enriched['file_path'] = metadata['file_path']
        if 'file_size' in metadata:
            enriched['file_size'] = metadata['file_size']
        
        return enriched
    
    def to_json_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert data to flattened JSON format.
        
        Args:
            data: Transformed problem data
            
        Returns:
            Data in JSON-friendly format
        """
        # Create flattened structure for JSON - NO EDGES
        json_data = {
            'problem': data.get('problem_data', {}),
            'nodes': data.get('nodes', []),
            'tours': data.get('tours', []),
            'metadata': data.get('metadata', {})
        }
        
        return json_data
    
    def validate_transformation(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate transformed data.
        
        Args:
            data: Transformed data
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields in problem_data using comprehension
        problem_data = data.get('problem_data', {})
        required_fields = {
            'name': "Problem name is required",
            'type': "Problem type is required",
            'dimension': "Problem dimension is required"
        }
        errors.extend(
            msg for field, msg in required_fields.items()
            if not problem_data.get(field)
        )
        
        # Validate node IDs are sequential
        nodes = data.get('nodes', [])
        if nodes:
            node_ids = [node.get('node_id') for node in nodes]
            if node_ids != list(range(len(node_ids))):
                errors.append("Node IDs are not sequential starting from 0")
        
        # NO EDGE VALIDATION - edges are not precomputed
        
        return errors
    
    def find_solution_file(self, problem_file_path: str) -> Optional[str]:
        """
        Find associated solution file (.opt.tour or .sol) for a problem file.
        
        Args:
            problem_file_path: Path to problem file
            
        Returns:
            Path to solution file if found, None otherwise
        """
        problem_path = Path(problem_file_path)
        problem_stem = problem_path.stem
        
        # Check for .opt.tour file (priority for TSP)
        # Structure: datasets_raw/zips/all_problems/{tsp,vrp,atsp}/file.tsp
        #            datasets_raw/zips/all_problems/tour/file.opt.tour
        parent_dir = problem_path.parent.parent  # all_problems directory
        tour_dir = parent_dir / "tour"
        tour_file = tour_dir / f"{problem_stem}.opt.tour"
        
        if tour_file.exists():
            self.logger.info(f"Found .opt.tour solution: {tour_file}")
            return str(tour_file)
        
        # Check for .sol file (VRP multi-route solutions)
        # Structure: datasets_raw/cvrplib/VRP-set-XXX/file.vrp
        #            datasets_raw/cvrplib/VRP-set-XXX/file.sol
        sol_file = problem_path.with_suffix('.sol')
        if sol_file.exists():
            self.logger.info(f"Found .sol solution: {sol_file}")
            return str(sol_file)
        
        return None
    
    def parse_solution_data(self, solution_file_path: str, parser) -> Optional[Dict[str, Any]]:
        """
        Parse solution file (.opt.tour or .sol) and extract solution data.
        
        Args:
            solution_file_path: Path to solution file
            parser: FormatParser instance
            
        Returns:
            Dictionary with solution data (routes as list of lists) or None if parsing fails
        """
        solution_path = Path(solution_file_path)
        
        # Check file extension to determine format
        if solution_path.suffix == '.sol':
            return self._parse_sol_file(solution_file_path)
        elif solution_path.suffix == '.tour':
            return self._parse_tour_file(solution_file_path, parser)
        else:
            self.logger.warning(f"Unknown solution format: {solution_path.suffix}")
            return None
    
    def _parse_tour_file(self, tour_file_path: str, parser) -> Optional[Dict[str, Any]]:
        """
        Parse .opt.tour file (TSPLIB single-tour format).
        
        Args:
            tour_file_path: Path to .opt.tour file
            parser: FormatParser instance
            
        Returns:
            Dictionary with routes (as [[tour]]) or None
        """
        try:
            # Parse TOUR file using format parser
            tour_data = parser.parse_file(tour_file_path)
            
            # Extract solution information
            problem_data = tour_data.get('problem_data', {})
            tours = tour_data.get('tours', [])
            
            if not tours:
                self.logger.warning(f"No tours found in {tour_file_path}")
                return None
            
            # Extract cost from comment if available
            comment = problem_data.get('comment', '')
            cost = self._extract_cost_from_comment(comment)
            
            # Get first tour - tours is list of dicts with 'tour_id' and 'nodes'
            first_tour = tours[0] if tours else {}
            tour_nodes = first_tour.get('nodes', []) if isinstance(first_tour, dict) else first_tour
            
            # CRITICAL: Convert from 1-based to 0-based indexing
            if tour_nodes:
                tour_nodes = [node - 1 for node in tour_nodes]
            
            # Wrap single tour in list to match multi-route format: [[tour]]
            routes = [tour_nodes] if tour_nodes else []
            
            solution_data = {
                'name': problem_data.get('name'),
                'type': problem_data.get('type'),
                'cost': cost,
                'routes': routes
            }
            
            self.logger.info(f"Parsed .opt.tour: {len(tour_nodes)} nodes, cost={cost}")
            return solution_data
            
        except Exception as e:
            self.logger.error(f"Failed to parse .opt.tour file {tour_file_path}: {e}")
            return None
    
    def _parse_sol_file(self, sol_file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse .sol file (CVRPLIB multi-route format).
        
        Format:
            Route #1: node1 node2 node3 ...
            Route #2: node4 node5 node6 ...
            ...
            Cost value
        
        Args:
            sol_file_path: Path to .sol file
            
        Returns:
            Dictionary with routes (as [[route1], [route2], ...]) or None
        """
        try:
            with open(sol_file_path, 'r') as f:
                content = f.read()
            
            # Extract all routes using regex
            route_pattern = r'Route #\d+:\s*([\d\s]+)'
            route_matches = re.findall(route_pattern, content)
            
            if not route_matches:
                self.logger.warning(f"No routes found in {sol_file_path}")
                return None
            
            # Parse each route (convert space-separated nodes to list of ints)
            # CRITICAL: Convert from 1-based to 0-based indexing
            routes = []
            for route_str in route_matches:
                nodes = [int(n) - 1 for n in route_str.split()]  # Subtract 1 for 0-based indexing
                routes.append(nodes)
            
            # Extract cost
            cost = None
            cost_match = re.search(r'Cost\s+([\d.]+)', content)
            if cost_match:
                cost = float(cost_match.group(1))
            
            solution_data = {
                'name': Path(sol_file_path).stem,
                'type': 'VRP',
                'cost': cost,
                'routes': routes
            }
            
            total_nodes = sum(len(route) for route in routes)
            self.logger.info(f"Parsed .sol: {len(routes)} routes, {total_nodes} nodes, cost={cost}")
            return solution_data
            
        except Exception as e:
            self.logger.error(f"Failed to parse .sol file {sol_file_path}: {e}")
            return None
    
    def _extract_cost_from_comment(self, comment: str) -> Optional[float]:
        """
        Extract cost from TOUR comment field.
        
        Args:
            comment: Comment string (e.g., "Optimal solution of gr666 (294358)")
            
        Returns:
            Extracted cost or None
        """
        if not comment:
            return None
        
        # Match pattern: "...(number)"
        match = re.search(r'\((\d+(?:\.\d+)?)\)', comment)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        
        return None
