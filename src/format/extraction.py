"""Data extraction utilities for TSPLIB95 StandardProblem instances.

This module provides pure functions to extract structured data from parsed
TSPLIB95 problems. Extracts nodes, edges, tours, and metadata in database-ready
format with proper 1-based to 0-based index conversion.

Key Features
------------
- Pure functions (no side effects, no state)
- 1-based TSPLIB → 0-based database index conversion
- Type-safe with complete type hints
- NumPy-style documentation

Usage
-----
>>> from format import parse_tsplib
>>> from format.extraction import extract_nodes, extract_problem_data
>>> 
>>> problem = parse_tsplib('gr17.tsp')
>>> nodes = extract_nodes(problem)
>>> metadata = extract_problem_data(problem)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import StandardProblem


def extract_problem_data(problem: StandardProblem) -> dict[str, Any]:
    """Extract basic problem metadata from StandardProblem.
    
    Extracts core TSPLIB95 metadata including problem type, dimension, capacity,
    and edge weight information. Normalizes problem types (e.g., "TSP (AUTHOR)" → "TSP").
    
    Parameters
    ----------
    problem : StandardProblem
        Parsed TSPLIB95 problem instance
    
    Returns
    -------
    dict of str to any
        Problem metadata with keys:
        - name : str - Problem name
        - type : str - Normalized problem type (TSP, VRP, ATSP, etc.)
        - comment : str - Problem description/comment
        - dimension : int - Number of nodes
        - capacity : int - Vehicle capacity (VRP only)
        - edge_weight_type : str - Distance calculation method
        - edge_weight_format : str - Weight matrix format
        - node_coord_type : str - Coordinate type (2D, 3D, etc.)
        - display_data_type : str - Display coordinate type
    
    Examples
    --------
    >>> problem = parse_tsplib('gr17.tsp')
    >>> data = extract_problem_data(problem)
    >>> data['name']
    'gr17'
    >>> data['type']
    'TSP'
    >>> data['dimension']
    17
    
    Notes
    -----
    Uses StandardProblem.as_name_dict() for clean data extraction.
    Normalizes problem types to remove author annotations.
    """
    # Use as_name_dict() to get clean data (excludes defaults)
    data = problem.as_name_dict()
    
    # Normalize problem type to handle variations like "TSP (M.~HOFMEISTER)"
    raw_type = data.get('type', '')
    normalized_type = normalize_problem_type(raw_type)
    
    # Base problem data
    result = {
        'name': data.get('name'),
        'type': normalized_type,
        'comment': data.get('comment'),
        'dimension': data.get('dimension'),
        'capacity': data.get('capacity'),
        'edge_weight_type': data.get('edge_weight_type'),
        'edge_weight_format': data.get('edge_weight_format'),
        'node_coord_type': data.get('node_coord_type'),
        'display_data_type': data.get('display_data_type'),
    }
    
    return result


def normalize_problem_type(raw_type: str) -> str:
    """Normalize problem type strings to standard TSPLIB95 types.
    
    Removes author annotations and standardizes type names.
    
    Parameters
    ----------
    raw_type : str
        Raw problem type string from TSPLIB95 file
    
    Returns
    -------
    str
        Normalized problem type (TSP, ATSP, CVRP, VRP, HCP, SOP, TOUR)
    
    Examples
    --------
    >>> normalize_problem_type("TSP (M.~HOFMEISTER)")
    'TSP'
    >>> normalize_problem_type("ATSP")
    'ATSP'
    >>> normalize_problem_type("CVRP")
    'CVRP'
    >>> normalize_problem_type("")
    ''
    
    Notes
    -----
    Extracts base type from parenthetical variations.
    Returns original string if not a known type.
    """
    if not raw_type:
        return raw_type
    
    # Extract base type from parenthetical variations
    base_type = raw_type.split('(')[0].strip().upper()
    
    # Map to standard types
    known_types = {'TSP', 'ATSP', 'CVRP', 'VRP', 'HCP', 'SOP', 'TOUR'}
    
    if base_type in known_types:
        return base_type
    
    # Return original if no normalization needed
    return raw_type


def extract_nodes(problem: 'StandardProblem') -> list[dict[str, Any]]:
    """Extract node data with coordinates, demands, and depot information.
    
    Converts TSPLIB95 1-based node indices to 0-based database indices.
    Handles both coordinate-based and explicit weight matrix problems.
    
    Parameters
    ----------
    problem : StandardProblem
        Parsed TSPLIB95 problem instance
    
    Returns
    -------
    list of dict of str to any
        List of node dictionaries, each containing:
        - node_id : int - 0-based node index
        - x : float or None - X coordinate (None for explicit matrix)
        - y : float or None - Y coordinate
        - z : float or None - Z coordinate (3D problems only)
        - demand : int - Node demand (VRP, 0 for TSP)
        - is_depot : bool - True if depot node (VRP)
        - display_x : float or None - Display X coordinate (if different from actual)
        - display_y : float or None - Display Y coordinate
    
    Examples
    --------
    >>> problem = parse_tsplib('gr17.tsp')
    >>> nodes = extract_nodes(problem)
    >>> len(nodes)
    17
    >>> nodes[0]['node_id']
    0
    >>> nodes[0]['x'] is not None
    True
    
    Notes
    -----
    CRITICAL: Converts from 1-based TSPLIB indexing to 0-based database indexing.
    For explicit weight matrices (no coordinates), creates virtual nodes with None coords.
    """
    
    nodes = []
    
    # Check if we have node coordinates  
    has_coordinates = hasattr(problem, 'node_coords') and problem.node_coords
    
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
    
    if has_coordinates:
        # Process coordinate-based problems (TSP with coordinates)
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
    else:
        # Process explicit weight matrix problems (no coordinates)
        # Create virtual nodes based on dimension
        dimension = getattr(problem, 'dimension', 0)
        if dimension > 0:
            for i in range(dimension):
                tsplib_node_id = i + 1  # TSPLIB uses 1-based indexing
                node = {
                    'node_id': i,  # 0-based for database
                    'x': None,     # No coordinates available
                    'y': None,
                    'z': None,
                    'demand': demands.get(tsplib_node_id, 0),
                    'is_depot': tsplib_node_id in depots,
                }
                nodes.append(node)
    
    return nodes


def extract_tours(problem: 'StandardProblem') -> list[dict[str, Any]]:
    """Extract tour data from solution files (.tour).
    
    Converts TSPLIB95 1-based tour indices to 0-based database indices.
    Removes -1 tour terminators.
    
    Parameters
    ----------
    problem : StandardProblem
        Parsed TSPLIB95 problem instance (typically from .tour file)
    
    Returns
    -------
    list of dict of str to any
        List of tour dictionaries, each containing:
        - tour_id : int - Tour index (0-based)
        - nodes : list of int - Node sequence (0-based indices)
    
    Examples
    --------
    >>> problem = parse_tsplib('gr17.opt.tour')
    >>> tours = extract_tours(problem)
    >>> len(tours)
    1
    >>> tours[0]['tour_id']
    0
    >>> all(isinstance(n, int) and n >= 0 for n in tours[0]['nodes'])
    True
    
    Notes
    -----
    CRITICAL: Converts from 1-based TSPLIB indexing to 0-based database indexing.
    Removes -1 terminators that indicate tour end in TSPLIB95 format.
    """
    
    tours = []
    
    if hasattr(problem, 'tours') and problem.tours:
        for idx, tour in enumerate(problem.tours):
            # Remove -1 terminators if present and convert to 0-based
            tour_nodes = [node - 1 for node in tour if node != -1]
            tours.append({
                'tour_id': idx,
                'nodes': tour_nodes
            })
    
    return tours


def extract_metadata(problem: 'StandardProblem', file_path: str) -> dict[str, Any]:
    """Extract comprehensive file and processing metadata.
    
    Provides metadata about the source file, data availability, and problem structure.
    
    Parameters
    ----------
    problem : StandardProblem
        Parsed TSPLIB95 problem instance
    file_path : str
        Path to the source TSPLIB95 file
    
    Returns
    -------
    dict of str to any
        Metadata dictionary with keys:
        - file_path : str - Full path to source file
        - file_size : int - File size in bytes
        - file_name : str - File name only
        - problem_source : str - Parent directory name
        - has_coordinates : bool - Whether problem has node coordinates
        - has_demands : bool - Whether problem has node demands (VRP)
        - has_depots : bool - Whether problem has depot nodes (VRP)
        - is_symmetric : bool - Whether problem has symmetric distances
        - weight_source : str - Source of edge weights (coordinates, explicit, etc.)
    
    Examples
    --------
    >>> problem = parse_tsplib('datasets/tsp/gr17.tsp')
    >>> metadata = extract_metadata(problem, 'datasets/tsp/gr17.tsp')
    >>> metadata['file_name']
    'gr17.tsp'
    >>> metadata['problem_source']
    'tsp'
    >>> metadata['has_coordinates']
    True
    
    Notes
    -----
    Useful for tracking data lineage and understanding problem characteristics.
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
        'is_symmetric': check_symmetry(problem),
        'weight_source': identify_weight_source(problem)
    }


def check_symmetry(problem: 'StandardProblem') -> bool:
    """Determine if problem has symmetric distances.
    
    Parameters
    ----------
    problem : StandardProblem
        Parsed TSPLIB95 problem instance
    
    Returns
    -------
    bool
        True if problem has symmetric distances, False otherwise
    
    Examples
    --------
    >>> problem = parse_tsplib('gr17.tsp')  # TSP is symmetric
    >>> check_symmetry(problem)
    True
    
    >>> problem = parse_tsplib('br17.atsp')  # ATSP is asymmetric
    >>> check_symmetry(problem)
    False
    
    Notes
    -----
    Based on problem type: TSP/CVRP/VRP are symmetric, ATSP is asymmetric.
    """
    
    problem_type = getattr(problem, 'type', '').upper()
    asymmetric_types = {'ATSP', 'SOP'}
    return problem_type not in asymmetric_types


def identify_weight_source(problem: 'StandardProblem') -> str:
    """Identify the source of edge weights in the problem.
    
    Parameters
    ----------
    problem : StandardProblem
        Parsed TSPLIB95 problem instance
    
    Returns
    -------
    str
        Weight source type:
        - 'coordinates' - Computed from node coordinates
        - 'explicit' - Provided as explicit weight matrix
        - 'function' - Computed by special distance function
        - 'unknown' - Cannot determine
    
    Examples
    --------
    >>> problem = parse_tsplib('gr17.tsp')
    >>> identify_weight_source(problem)
    'coordinates'
    
    >>> problem = parse_tsplib('br17.atsp')
    >>> identify_weight_source(problem)
    'explicit'
    
    Notes
    -----
    Helps determine how to compute/retrieve edge weights for algorithms.
    """
    
    if hasattr(problem, 'node_coords') and problem.node_coords:
        return 'coordinates'
    elif hasattr(problem, 'edge_weights') and problem.edge_weights:
        return 'explicit'
    elif hasattr(problem, 'edge_weight_type'):
        edge_type = problem.edge_weight_type.upper()
        if edge_type in {'EXPLICIT', 'FULL_MATRIX', 'UPPER_ROW', 'LOWER_ROW'}:
            return 'explicit'
        elif edge_type == 'SPECIAL':
            return 'function'
        else:
            return 'coordinates'
    
    return 'unknown'


__all__ = [
    'extract_problem_data',
    'extract_nodes',
    'extract_tours',
    'extract_metadata',
    'normalize_problem_type',
    'check_symmetry',
    'identify_weight_source',
]
