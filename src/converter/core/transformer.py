"""Data transformation for TSPLIB converter."""

from typing import Dict, Any, List, Optional
import logging


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
        edges = problem_data.get('edges', [])
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
        
        # Ensure all edges have required fields
        normalized_edges = self._normalize_edges(edges)
        
        # Build final structure
        result = {
            'problem_data': self._enrich_problem_data(problem_meta, metadata),
            'nodes': normalized_nodes,
            'edges': normalized_edges,
            'tours': tours,
            'metadata': metadata
        }
        
        return result
    
    def _normalize_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize node data with consistent field structure.
        
        Args:
            nodes: List of node dictionaries
            
        Returns:
            List of normalized node dictionaries
        """
        normalized = []
        
        for node in nodes:
            normalized_node = {
                'node_id': node.get('node_id', 0),
                'x': node.get('x'),
                'y': node.get('y'),
                'z': node.get('z'),
                'demand': node.get('demand', 0),
                'is_depot': node.get('is_depot', False),
                'display_x': node.get('display_x'),
                'display_y': node.get('display_y')
            }
            normalized.append(normalized_node)
        
        return normalized
    
    def _normalize_edges(self, edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize edge data with consistent field structure.
        
        Args:
            edges: List of edge dictionaries
            
        Returns:
            List of normalized edge dictionaries
        """
        normalized = []
        
        for edge in edges:
            normalized_edge = {
                'from_node': edge.get('from_node', 0),
                'to_node': edge.get('to_node', 0),
                'weight': edge.get('weight', 0.0),
                'is_fixed': edge.get('is_fixed', False)
            }
            normalized.append(normalized_edge)
        
        return normalized
    
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
        # Create flattened structure for JSON
        json_data = {
            'problem': data.get('problem_data', {}),
            'nodes': data.get('nodes', []),
            'edges': data.get('edges', []),
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
        
        # Check required fields in problem_data
        problem_data = data.get('problem_data', {})
        if not problem_data.get('name'):
            errors.append("Problem name is required")
        if not problem_data.get('type'):
            errors.append("Problem type is required")
        if not problem_data.get('dimension'):
            errors.append("Problem dimension is required")
        
        # Validate node IDs are sequential
        nodes = data.get('nodes', [])
        if nodes:
            node_ids = [node.get('node_id') for node in nodes]
            if node_ids != list(range(len(node_ids))):
                errors.append("Node IDs are not sequential starting from 0")
        
        # Validate edge node references
        edges = data.get('edges', [])
        nodes = data.get('nodes', [])
        
        # Only validate edge references if we have nodes
        # (some problems like gr17.tsp have edges but no coordinate nodes)
        if nodes:
            max_node_id = len(nodes) - 1
            for idx, edge in enumerate(edges):
                from_node = edge.get('from_node', -1)
                to_node = edge.get('to_node', -1)
                
                if from_node < 0 or from_node > max_node_id:
                    errors.append(f"Edge {idx}: from_node {from_node} out of range")
                if to_node < 0 or to_node > max_node_id:
                    errors.append(f"Edge {idx}: to_node {to_node} out of range")
        
        return errors
