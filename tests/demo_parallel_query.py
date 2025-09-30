"""
Demonstration script showing parallel processing and database querying.

This script demonstrates:
1. Parallel file processing with ParallelProcessor
2. Database storage with DuckDB
3. Advanced database queries
4. Statistics and analysis
"""

import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from converter.database.operations import DatabaseManager
from converter.utils.parallel import ParallelProcessor
from converter.utils.logging import setup_logging
from tsplib95 import loaders
import duckdb


def process_tsplib_file(file_path: str, db_manager: DatabaseManager):
    """Process a single TSPLIB file and store in database."""
    problem = loaders.load(file_path)
    problem_dict = problem.as_name_dict()
    
    # Insert problem
    problem_id = db_manager.insert_problem({
        'name': problem_dict.get('name'),
        'type': problem_dict.get('type'),
        'comment': problem_dict.get('comment'),
        'dimension': problem_dict.get('dimension'),
        'edge_weight_type': problem_dict.get('edge_weight_type'),
    })
    
    # Insert nodes if available
    if hasattr(problem, 'node_coords') and problem.node_coords:
        nodes = []
        for node_id in range(problem.dimension):
            orig_node = node_id + 1
            coords = problem.node_coords.get(orig_node, (None, None))
            nodes.append({
                'node_id': node_id,
                'x': coords[0] if len(coords) > 0 else None,
                'y': coords[1] if len(coords) > 1 else None,
            })
        db_manager.insert_nodes(problem_id, nodes)
    
    # Insert sample edges
    try:
        graph = problem.get_graph(normalize=True)
        edges = []
        for i, (from_node, to_node, edge_data) in enumerate(graph.edges(data=True)):
            if i >= 500:  # Limit for demo
                break
            edges.append({
                'from_node': from_node,
                'to_node': to_node,
                'weight': edge_data.get('weight', 0),
            })
        db_manager.insert_edges(problem_id, edges)
    except:
        pass
    
    return problem_id


def main():
    print("\n" + "=" * 70)
    print("TSPLIB95 PARALLEL PROCESSING & DATABASE QUERY DEMONSTRATION")
    print("=" * 70)
    
    logger = setup_logging("INFO")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "routing.duckdb"
        db_manager = DatabaseManager(str(db_path), logger)
        
        # Find test files
        base_path = Path("datasets_raw/problems/tsp")
        test_files = [
            str(f) for f in sorted(base_path.glob("*.tsp"))
            if f.stat().st_size < 50000
        ][:10]  # Take first 10 small files
        
        print(f"\n📁 Found {len(test_files)} TSPLIB files for processing")
        print("-" * 70)
        
        # DEMONSTRATION 1: Parallel Processing
        print("\n🔄 PARALLEL PROCESSING WITH 4 WORKERS")
        print("-" * 70)
        
        processor = ParallelProcessor(max_workers=4, logger=logger)
        
        def process_wrapper(file_path):
            return process_tsplib_file(file_path, db_manager)
        
        results = processor.process_files_parallel(test_files, process_wrapper)
        
        print(f"\n✅ Processing Results:")
        print(f"   • Files processed:  {results['successful']}")
        print(f"   • Failures:         {results['failed']}")
        print(f"   • Processing time:  {results['processing_time']:.2f}s")
        print(f"   • Throughput:       {results['throughput']:.2f} files/sec")
        
        # DEMONSTRATION 2: Database Statistics
        print("\n📊 DATABASE STATISTICS")
        print("-" * 70)
        
        stats = db_manager.get_problem_stats()
        print(f"\nTotal problems in database: {stats['total_problems']}")
        
        for type_stat in stats['by_type']:
            print(f"\n{type_stat['type']} Problems:")
            print(f"   • Count:           {type_stat['count']}")
            print(f"   • Avg dimension:   {type_stat['avg_dimension']}")
            print(f"   • Max dimension:   {type_stat['max_dimension']}")
        
        # DEMONSTRATION 3: Advanced Queries
        print("\n🔍 ADVANCED DATABASE QUERIES")
        print("-" * 70)
        
        # Query 1: Problems by dimension range
        print("\n1. Problems with dimension between 40 and 100:")
        medium_problems = db_manager.query_problems(min_dimension=40, max_dimension=100)
        for p in medium_problems[:5]:
            print(f"   • {p['name']:<15} (dim: {p['dimension']}, type: {p['edge_weight_type']})")
        
        # Query 2: Custom SQL queries
        print("\n2. Node density analysis (nodes with coordinates):")
        with duckdb.connect(str(db_path)) as conn:
            result = conn.execute("""
                SELECT 
                    p.name,
                    p.dimension,
                    COUNT(n.id) as node_count,
                    ROUND(COUNT(n.id) * 100.0 / p.dimension, 2) as coverage_pct
                FROM problems p
                LEFT JOIN nodes n ON p.id = n.problem_id
                GROUP BY p.id, p.name, p.dimension
                ORDER BY p.dimension DESC
                LIMIT 5
            """).fetchall()
            
            print(f"   {'Name':<15} {'Dim':>5} {'Nodes':>6} {'Coverage':>10}")
            print("   " + "-" * 40)
            for row in result:
                print(f"   {row[0]:<15} {row[1]:>5} {row[2]:>6} {row[3]:>9}%")
        
        # Query 3: Edge statistics
        print("\n3. Edge weight statistics by problem:")
        with duckdb.connect(str(db_path)) as conn:
            result = conn.execute("""
                SELECT 
                    p.name,
                    COUNT(e.id) as edge_count,
                    ROUND(AVG(e.weight), 2) as avg_weight,
                    ROUND(MIN(e.weight), 2) as min_weight,
                    ROUND(MAX(e.weight), 2) as max_weight
                FROM problems p
                LEFT JOIN edges e ON p.id = e.problem_id
                WHERE e.id IS NOT NULL
                GROUP BY p.id, p.name
                ORDER BY edge_count DESC
                LIMIT 5
            """).fetchall()
            
            print(f"   {'Name':<15} {'Edges':>6} {'Avg':>8} {'Min':>8} {'Max':>8}")
            print("   " + "-" * 50)
            for row in result:
                print(f"   {row[0]:<15} {row[1]:>6} {row[2]:>8} {row[3]:>8} {row[4]:>8}")
        
        # DEMONSTRATION 4: Memory Usage
        print("\n💾 RESOURCE MONITORING")
        print("-" * 70)
        
        memory_stats = processor.monitor_memory_usage()
        print(f"\nMemory Usage:")
        print(f"   • Used:      {memory_stats['used_mb']:.1f} MB")
        print(f"   • Available: {memory_stats['available_mb']:.1f} MB")
        print(f"   • Percent:   {memory_stats['percent']:.1f}%")
        
        # DEMONSTRATION 5: Problem Export
        print("\n📤 PROBLEM EXPORT EXAMPLE")
        print("-" * 70)
        
        problems = db_manager.query_problems(limit=1)
        if problems:
            exported = db_manager.export_problem(problems[0]['id'])
            print(f"\nExported problem: {exported['problem']['name']}")
            print(f"   • Type:       {exported['problem']['type']}")
            print(f"   • Dimension:  {exported['problem']['dimension']}")
            print(f"   • Nodes:      {len(exported['nodes'])}")
            print(f"   • Edges:      {len(exported['edges'])}")
            
            if exported['nodes']:
                print(f"\n   Sample node (first):")
                node = exported['nodes'][0]
                print(f"     - ID: {node['node_id']}, X: {node.get('x')}, Y: {node.get('y')}")
            
            if exported['edges']:
                print(f"\n   Sample edge (first):")
                edge = exported['edges'][0]
                print(f"     - From: {edge['from_node']}, To: {edge['to_node']}, Weight: {edge['weight']}")
        
        print("\n" + "=" * 70)
        print("✅ DEMONSTRATION COMPLETE")
        print("=" * 70)
        print(f"\n📊 Summary:")
        print(f"   • Processed {results['successful']} files in parallel")
        print(f"   • Stored in DuckDB with {stats['total_problems']} problems")
        print(f"   • Performed advanced SQL queries")
        print(f"   • Demonstrated resource monitoring")
        print(f"   • Showed data export capabilities")
        print()


if __name__ == '__main__':
    main()
