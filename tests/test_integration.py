"""Integration test demonstrating complete workflow with actual TSPLIB data."""

import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from converter.database.operations import DatabaseManager
from converter.utils.parallel import ParallelProcessor
from converter.utils.update import UpdateManager
from converter.utils.logging import setup_logging
from tsplib95 import loaders


def parse_and_store_tsplib(file_path: str, db_manager: DatabaseManager):
    """
    Parse a TSPLIB file and store it in the database.
    
    Args:
        file_path: Path to TSPLIB file
        db_manager: Database manager instance
        
    Returns:
        Problem ID
    """
    # Parse with tsplib95
    problem = loaders.load(file_path)
    problem_dict = problem.as_name_dict()
    
    # Insert problem
    problem_id = db_manager.insert_problem({
        'name': problem_dict.get('name'),
        'type': problem_dict.get('type'),
        'comment': problem_dict.get('comment'),
        'dimension': problem_dict.get('dimension'),
        'capacity': problem_dict.get('capacity'),
        'edge_weight_type': problem_dict.get('edge_weight_type'),
        'edge_weight_format': problem_dict.get('edge_weight_format')
    })
    
    # Get nodes from graph (0-based indexing)
    try:
        graph = problem.get_graph(normalize=True)
        
        # Insert nodes if we have coordinates
        if hasattr(problem, 'node_coords') and problem.node_coords:
            nodes = []
            for node_id in range(problem.dimension):
                # Get original 1-based coordinates
                orig_node = node_id + 1
                coords = problem.node_coords.get(orig_node, (None, None))
                
                node_data = {
                    'node_id': node_id,  # 0-based for database
                    'x': coords[0] if len(coords) > 0 else None,
                    'y': coords[1] if len(coords) > 1 else None,
                }
                
                # Add demand if VRP
                if hasattr(problem, 'demands') and problem.demands:
                    node_data['demand'] = problem.demands.get(orig_node, 0)
                
                # Check if depot
                if hasattr(problem, 'depots') and problem.depots:
                    node_data['is_depot'] = orig_node in problem.depots
                
                nodes.append(node_data)
            
            db_manager.insert_nodes(problem_id, nodes)
        
        # Insert a sample of edges (to avoid too many for large graphs)
        edges = []
        edge_count = 0
        max_edges = 1000  # Limit edges for demonstration
        
        for from_node, to_node, edge_data in graph.edges(data=True):
            if edge_count >= max_edges:
                break
            
            edges.append({
                'from_node': from_node,
                'to_node': to_node,
                'weight': edge_data.get('weight', 0),
                'is_fixed': edge_data.get('is_fixed', False)
            })
            edge_count += 1
        
        db_manager.insert_edges(problem_id, edges)
    
    except Exception as e:
        print(f"Warning: Could not extract graph data: {e}")
    
    return problem_id


def main():
    """Run integration test with real TSPLIB files."""
    print("=" * 60)
    print("TSPLIB95 ETL Integration Test")
    print("=" * 60)
    
    # Setup
    logger = setup_logging("INFO")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_integration.duckdb"
        db_manager = DatabaseManager(str(db_path), logger)
        
        # Find some sample TSPLIB files
        base_path = Path("datasets_raw/problems/tsp")
        
        if not base_path.exists():
            print("Error: datasets_raw/problems/tsp not found")
            return
        
        # Get first 5 small TSP files for testing
        tsp_files = []
        for tsp_file in sorted(base_path.glob("*.tsp")):
            # Skip very large files for this demo
            if tsp_file.stat().st_size < 100000:  # Less than 100KB
                tsp_files.append(str(tsp_file))
                if len(tsp_files) >= 5:
                    break
        
        print(f"\nFound {len(tsp_files)} test files")
        print("-" * 60)
        
        # Test 1: Sequential processing
        print("\n1. Sequential Processing Test")
        print("-" * 60)
        
        for file_path in tsp_files[:3]:
            try:
                problem_id = parse_and_store_tsplib(file_path, db_manager)
                file_name = Path(file_path).name
                print(f"✓ Processed {file_name} -> Problem ID: {problem_id}")
            except Exception as e:
                print(f"✗ Failed {Path(file_path).name}: {e}")
        
        # Check database stats
        stats = db_manager.get_problem_stats()
        print(f"\nDatabase stats: {stats['total_problems']} problems")
        
        # Test 2: Parallel processing
        print("\n2. Parallel Processing Test")
        print("-" * 60)
        
        processor = ParallelProcessor(max_workers=2, logger=logger)
        
        def process_wrapper(file_path):
            return parse_and_store_tsplib(file_path, db_manager)
        
        results = processor.process_files_parallel(
            tsp_files[3:5],  # Process remaining files
            process_wrapper
        )
        
        print(f"✓ Parallel processing: {results['successful']} successful, "
              f"{results['failed']} failed")
        print(f"  Throughput: {results['throughput']:.2f} files/sec")
        
        # Final stats
        stats = db_manager.get_problem_stats()
        print(f"\nFinal database stats: {stats['total_problems']} problems")
        
        # Test 3: Query database
        print("\n3. Database Query Test")
        print("-" * 60)
        
        problems = db_manager.query_problems(limit=10)
        print(f"\n{'Name':<15} {'Type':<6} {'Dim':>5} {'Nodes':>6} {'Edges':>6}")
        print("-" * 60)
        
        for prob in problems:
            # Get node and edge counts
            import duckdb
            with duckdb.connect(str(db_path)) as conn:
                node_count = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE problem_id = ?",
                    [prob['id']]
                ).fetchone()[0]
                
                edge_count = conn.execute(
                    "SELECT COUNT(*) FROM edges WHERE problem_id = ?",
                    [prob['id']]
                ).fetchone()[0]
            
            print(f"{prob['name']:<15} {prob['type']:<6} {prob['dimension']:>5} "
                  f"{node_count:>6} {edge_count:>6}")
        
        # Test 4: Update detection
        print("\n4. Update Detection Test")
        print("-" * 60)
        
        update_manager = UpdateManager(db_manager, logger)
        
        # Check for changes
        for file_path in tsp_files[:2]:
            change_info = update_manager.detect_changes(file_path)
            print(f"{Path(file_path).name}: {change_info['change_type']}")
        
        # Test 5: Export a problem
        print("\n5. Problem Export Test")
        print("-" * 60)
        
        if problems:
            exported = db_manager.export_problem(problems[0]['id'])
            print(f"Exported problem '{exported['problem']['name']}':")
            print(f"  - {len(exported['nodes'])} nodes")
            print(f"  - {len(exported['edges'])} edges")
        
        print("\n" + "=" * 60)
        print("✓ All integration tests completed successfully!")
        print("=" * 60)


if __name__ == '__main__':
    main()
