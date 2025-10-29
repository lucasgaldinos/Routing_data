"""
Migration script to extract and store EXPLICIT edge weight matrices.

This migration:
1. Finds all problems with edge_weight_type='EXPLICIT' in the database
2. Re-parses the original TSPLIB files to extract edge weight sections
3. Stores the distance matrices in the edge_weight_matrices table

Run after schema changes to backfill EXPLICIT edge weights.
"""

import sys
from pathlib import Path
import json
import duckdb
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from converter.utils.logging import setup_logging


def parse_edge_weights_from_file(file_path: Path) -> dict:
    """Parse EDGE_WEIGHT_SECTION from TSPLIB file.
    
    Args:
        file_path: Path to TSPLIB problem file
        
    Returns:
        Dictionary with:
        - dimension: int
        - matrix_format: str ('FULL_MATRIX', 'LOWER_ROW', etc.)
        - is_symmetric: bool
        - matrix: list of lists (full matrix)
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    lines = content.strip().split('\n')
    
    # Extract metadata
    dimension = None
    edge_weight_format = None
    problem_type = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('DIMENSION'):
            dimension = int(line.split(':')[1].strip())
        elif line.startswith('EDGE_WEIGHT_FORMAT'):
            edge_weight_format = line.split(':')[1].strip()
        elif line.startswith('TYPE'):
            problem_type = line.split(':')[1].strip()
    
    if not dimension or not edge_weight_format:
        raise ValueError(f"Could not find DIMENSION or EDGE_WEIGHT_FORMAT in {file_path}")
    
    # Find EDGE_WEIGHT_SECTION
    in_section = False
    weight_values = []
    
    for line in lines:
        line = line.strip()
        if line == 'EDGE_WEIGHT_SECTION':
            in_section = True
            continue
        elif line.endswith('_SECTION') or line == 'EOF':
            in_section = False
            continue
        
        if in_section and line:
            # Parse numbers from line
            values = [int(x) for x in line.split() if x.strip()]
            weight_values.extend(values)
    
    # Reconstruct full matrix from format
    if edge_weight_format == 'FULL_MATRIX':
        # Full n×n matrix stored row by row
        if len(weight_values) != dimension * dimension:
            raise ValueError(f"Expected {dimension * dimension} values, got {len(weight_values)}")
        
        matrix = []
        for i in range(dimension):
            row = weight_values[i * dimension:(i + 1) * dimension]
            matrix.append(row)
    
    elif edge_weight_format == 'LOWER_ROW':
        # Lower triangular matrix (row by row, excluding diagonal)
        # Row 0: nothing (0 elements)
        # Row 1: d[1,0] (1 element)
        # Row 2: d[2,0], d[2,1] (2 elements)
        # ...
        # Total: 0 + 1 + 2 + ... + (n-1) = n(n-1)/2
        expected_count = dimension * (dimension - 1) // 2
        if len(weight_values) != expected_count:
            raise ValueError(f"Expected {expected_count} values for LOWER_ROW, got {len(weight_values)}")
        
        # Build full symmetric matrix
        matrix = [[0] * dimension for _ in range(dimension)]
        idx = 0
        for i in range(1, dimension):
            for j in range(i):
                matrix[i][j] = weight_values[idx]
                matrix[j][i] = weight_values[idx]  # Symmetric
                idx += 1
    
    elif edge_weight_format == 'UPPER_ROW':
        # Upper triangular matrix (row by row, excluding diagonal)
        expected_count = dimension * (dimension - 1) // 2
        if len(weight_values) != expected_count:
            raise ValueError(f"Expected {expected_count} values for UPPER_ROW, got {len(weight_values)}")
        
        matrix = [[0] * dimension for _ in range(dimension)]
        idx = 0
        for i in range(dimension - 1):
            for j in range(i + 1, dimension):
                matrix[i][j] = weight_values[idx]
                matrix[j][i] = weight_values[idx]  # Symmetric
                idx += 1
    
    else:
        raise ValueError(f"Unsupported edge weight format: {edge_weight_format}")
    
    is_symmetric = problem_type in {'TSP', 'CVRP', 'VRP'}  # TSP variants are symmetric
    
    return {
        'dimension': dimension,
        'matrix_format': edge_weight_format,
        'is_symmetric': is_symmetric,
        'matrix': matrix
    }


def run_migration(db_path: str, logger: logging.Logger):
    """Execute migration to extract EXPLICIT edge weights.
    
    Args:
        db_path: Path to routing.duckdb
        logger: Logger instance
    """
    conn = duckdb.connect(db_path)
    
    # Find all EXPLICIT problems
    results = conn.execute("""
        SELECT p.id, p.name, p.type, p.dimension, p.edge_weight_format, ft.file_path
        FROM problems p
        JOIN file_tracking ft ON p.id = ft.problem_id
        WHERE p.edge_weight_type = 'EXPLICIT'
    """).fetchall()
    
    logger.info(f"Found {len(results)} EXPLICIT problems to process")
    
    processed = 0
    skipped = 0
    errors = 0
    
    for problem_id, name, ptype, dimension, edge_format, file_path in results:
        try:
            # Check if already processed
            existing = conn.execute("""
                SELECT problem_id FROM edge_weight_matrices WHERE problem_id = ?
            """, [problem_id]).fetchone()
            
            if existing:
                logger.debug(f"Skipping {name} - already has edge weights")
                skipped += 1
                continue
            
            # Parse edge weights from file
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.warning(f"File not found: {file_path}")
                errors += 1
                continue
            
            logger.info(f"Parsing edge weights for {name} ({dimension} nodes)")
            edge_data = parse_edge_weights_from_file(file_path_obj)
            
            # Verify dimension matches
            if edge_data['dimension'] != dimension:
                logger.error(f"Dimension mismatch for {name}: DB={dimension}, file={edge_data['dimension']}")
                errors += 1
                continue
            
            # Store in database
            matrix_json = json.dumps(edge_data['matrix'])
            conn.execute("""
                INSERT INTO edge_weight_matrices (problem_id, dimension, matrix_format, 
                                                  is_symmetric, matrix_json)
                VALUES (?, ?, ?, ?, ?)
            """, [
                problem_id,
                edge_data['dimension'],
                edge_data['matrix_format'],
                edge_data['is_symmetric'],
                matrix_json
            ])
            
            logger.info(f"✓ Stored edge weights for {name}")
            processed += 1
            
        except Exception as e:
            logger.error(f"Error processing {name}: {e}")
            errors += 1
            continue
    
    conn.close()
    
    logger.info("="*70)
    logger.info("Migration complete:")
    logger.info(f"  Processed: {processed}")
    logger.info(f"  Skipped: {skipped}")
    logger.info(f"  Errors: {errors}")
    logger.info("="*70)


if __name__ == '__main__':
    logger = setup_logging()
    
    # Database path
    db_path = 'datasets_processed/db/routing.duckdb'
    
    logger.info("Starting migration: Extract EXPLICIT edge weights")
    run_migration(db_path, logger)
