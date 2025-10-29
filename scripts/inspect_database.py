#!/usr/bin/env python3
"""
Database Inspector - Check tables and data in routing.duckdb

Usage:
    uv run python scripts/inspect_database.py
    uv run python scripts/inspect_database.py --db datasets/db/routing.duckdb
    uv run python scripts/inspect_database.py --table problems
    uv run python scripts/inspect_database.py --detail
"""

import argparse
import sys
from pathlib import Path

try:
    import duckdb
except ImportError:
    print("ERROR: duckdb not installed. Run: uv sync")
    sys.exit(1)


def format_bytes(size_bytes: int) -> str:
    """Format bytes into human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def inspect_database(db_path: Path, table_name: str = None, detail: bool = False):
    """Inspect the DuckDB database and show table information."""
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    file_size = db_path.stat().st_size
    print(f"📊 Database: {db_path}")
    print(f"💾 File size: {format_bytes(file_size)}")
    print("=" * 80)
    
    conn = duckdb.connect(str(db_path), read_only=True)
    
    try:
        # Get all tables
        tables = conn.execute("SHOW TABLES").fetchall()
        
        if not tables:
            print("⚠️  No tables found in database")
            return
        
        print(f"\n📋 Tables found: {len(tables)}\n")
        
        for (table,) in tables:
            # If specific table requested, skip others
            if table_name and table != table_name:
                continue
            
            print(f"🔸 Table: {table}")
            print("-" * 80)
            
            # Get row count
            count_result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            row_count = count_result[0] if count_result else 0
            print(f"   Rows: {row_count:,}")
            
            # Get schema
            schema = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
            print(f"   Columns: {len(schema)}")
            
            if detail:
                print("\n   Schema:")
                for col_id, name, col_type, not_null, default, pk in schema:
                    null_str = "NOT NULL" if not_null else "NULL"
                    pk_str = " PRIMARY KEY" if pk else ""
                    default_str = f" DEFAULT {default}" if default else ""
                    print(f"      {name:<30} {col_type:<15} {null_str}{pk_str}{default_str}")
            
            # Show sample data for specific tables
            if detail and row_count > 0:
                print("\n   Sample data (first 3 rows):")
                
                if table == "problems":
                    sample = conn.execute(f"""
                        SELECT name, type, dimension, edge_weight_type, comment
                        FROM {table} 
                        LIMIT 3
                    """).fetchall()
                    
                    for name, ptype, dim, ewt, comment in sample:
                        print(f"      • {name} ({ptype})")
                        print(f"        Dimension: {dim}, Edge Weight: {ewt}")
                        if comment:
                            print(f"        Comment: {comment[:60]}...")
                
                elif table == "nodes":
                    sample = conn.execute(f"""
                        SELECT p.name, n.node_id, n.x, n.y
                        FROM {table} n
                        JOIN problems p ON n.problem_id = p.id
                        LIMIT 3
                    """).fetchall()
                    
                    for pname, node_id, x, y in sample:
                        if x is not None and y is not None:
                            print(f"      • {pname}: Node {node_id} at ({x:.2f}, {y:.2f})")
                        else:
                            print(f"      • {pname}: Node {node_id} (no coordinates)")
                
                elif table == "depots":
                    sample = conn.execute(f"""
                        SELECT p.name, d.depot_id
                        FROM {table} d
                        JOIN problems p ON d.problem_id = p.id
                        LIMIT 3
                    """).fetchall()
                    
                    for pname, depot_id in sample:
                        print(f"      • {pname}: Depot {depot_id}")
                
                elif table == "demands":
                    sample = conn.execute(f"""
                        SELECT p.name, d.node_id, d.demand
                        FROM {table} d
                        JOIN problems p ON d.problem_id = p.id
                        LIMIT 3
                    """).fetchall()
                    
                    for pname, node_id, demand in sample:
                        print(f"      • {pname}: Node {node_id} demands {demand}")
                
                elif table == "edge_weight_matrices":
                    sample = conn.execute(f"""
                        SELECT p.name, e.dimension, e.matrix_format, e.is_symmetric,
                               LENGTH(e.matrix_json) as matrix_size
                        FROM {table} e
                        JOIN problems p ON e.problem_id = p.id
                        LIMIT 3
                    """).fetchall()
                    
                    for pname, dim, fmt, sym, size in sample:
                        sym_str = "symmetric" if sym else "asymmetric"
                        print(f"      • {pname}: {dim}×{dim} {sym_str} {fmt}")
                        print(f"        Matrix JSON size: {format_bytes(size)}")
                
                elif table == "capacities":
                    sample = conn.execute(f"""
                        SELECT p.name, c.capacity
                        FROM {table} c
                        JOIN problems p ON c.problem_id = p.id
                        LIMIT 3
                    """).fetchall()
                    
                    for pname, capacity in sample:
                        print(f"      • {pname}: Capacity {capacity}")
                
                elif table == "optimal_tours" or table == "optimal_routes":
                    sample = conn.execute(f"""
                        SELECT p.name, LENGTH(t.tour) as tour_length
                        FROM {table} t
                        JOIN problems p ON t.problem_id = p.id
                        LIMIT 3
                    """).fetchall()
                    
                    for pname, tour_len in sample:
                        print(f"      • {pname}: {tour_len} characters")
            
            # Table-specific statistics
            if detail and row_count > 0:
                if table == "problems":
                    type_stats = conn.execute(f"""
                        SELECT type, COUNT(*) as count
                        FROM {table}
                        GROUP BY type
                        ORDER BY count DESC
                    """).fetchall()
                    
                    print("\n   Problem types:")
                    for ptype, count in type_stats:
                        print(f"      {ptype}: {count:,}")
                
                elif table == "edge_weight_matrices":
                    size_stats = conn.execute(f"""
                        SELECT 
                            COUNT(*) as total,
                            MIN(dimension) as min_dim,
                            MAX(dimension) as max_dim,
                            CAST(AVG(dimension) AS INTEGER) as avg_dim,
                            SUM(LENGTH(matrix_json)) as total_json_size
                        FROM {table}
                    """).fetchone()
                    
                    if size_stats:
                        total, min_dim, max_dim, avg_dim, total_size = size_stats
                        print(f"\n   Matrix statistics:")
                        print(f"      Dimensions: {min_dim} to {max_dim} (avg: {avg_dim})")
                        print(f"      Total JSON size: {format_bytes(total_size)}")
            
            print()
        
        # Summary statistics
        if not table_name:
            print("=" * 80)
            print("\n📈 Summary Statistics:\n")
            
            # Total problems by type
            type_stats = conn.execute("""
                SELECT type, COUNT(*) as count
                FROM problems
                GROUP BY type
                ORDER BY count DESC
            """).fetchall()
            
            print("Problem Distribution:")
            total_problems = sum(count for _, count in type_stats)
            for ptype, count in type_stats:
                pct = (count / total_problems * 100) if total_problems else 0
                print(f"   {ptype:<10} {count:>6,} ({pct:>5.1f}%)")
            print(f"   {'TOTAL':<10} {total_problems:>6,}")
            
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Inspect DuckDB routing database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/inspect_database.py
  uv run python scripts/inspect_database.py --detail
  uv run python scripts/inspect_database.py --table problems --detail
  uv run python scripts/inspect_database.py --db datasets/db/routing.duckdb
        """
    )
    
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("datasets_processed/db/routing.duckdb"),
        help="Path to DuckDB database file (default: datasets_processed/db/routing.duckdb)"
    )
    
    parser.add_argument(
        "--table",
        type=str,
        help="Show only specific table"
    )
    
    parser.add_argument(
        "--detail",
        action="store_true",
        help="Show detailed information including schema and sample data"
    )
    
    args = parser.parse_args()
    
    try:
        inspect_database(args.db, args.table, args.detail)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
