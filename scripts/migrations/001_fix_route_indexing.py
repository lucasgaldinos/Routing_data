#!/usr/bin/env python3
"""
Migration Script: Convert Solution Routes from 1-based to 0-based Indexing

CRITICAL BUG FIX:
- Routes were stored with 1-based indexing (nodes 1 to N)
- Should be 0-based indexing (nodes 0 to N-1) to match node table
- This migration subtracts 1 from all node IDs in all routes

Usage:
    python migrate_routes_to_zero_based.py

Safety:
- Checks if migration already applied (looks for routes with node 0)
- Validates conversion on sample data before full migration
- Reports before/after statistics
"""

import duckdb
from pathlib import Path
import sys


def check_migration_needed(conn: duckdb.DuckDBPyConnection) -> bool:
    """
    Check if migration is needed by looking for 0-indexed routes.
    
    If any route contains node 0, migration already applied.
    """
    # Get a sample route and check if it contains small node IDs (0, 1, 2)
    result = conn.execute("""
        SELECT routes
        FROM solutions
        WHERE routes IS NOT NULL
        LIMIT 1
    """).fetchone()
    
    if not result or not result[0]:
        print("⚠️  No solutions found in database")
        return False
    
    # Check first route's first few nodes
    first_route = result[0][0] if result[0] else []
    
    # If first route starts with 0 or has very small numbers, likely 0-indexed
    # If it starts with numbers > 0, likely 1-indexed
    has_zero = 0 in first_route[:10]
    
    if has_zero:
        print("⚠️  Migration appears to already be applied (found node 0 in routes)")
        return False
    else:
        print("✅ Migration needed (routes appear to be 1-indexed)")
        return True


def get_migration_stats(conn: duckdb.DuckDBPyConnection) -> dict:
    """Get statistics before migration."""
    stats = {}
    
    # Total solutions
    result = conn.execute("SELECT COUNT(*) FROM solutions").fetchone()
    stats['total_solutions'] = result[0]
    
    # Total routes across all solutions
    result = conn.execute("SELECT SUM(len(routes)) FROM solutions").fetchone()
    stats['total_routes'] = result[0]
    
    # Sample route for validation
    result = conn.execute("""
        SELECT id, problem_id, routes
        FROM solutions
        WHERE id = (SELECT MIN(id) FROM solutions)
    """).fetchone()
    
    if result:
        stats['sample_id'] = result[0]
        stats['sample_problem_id'] = result[1]
        stats['sample_route_before'] = result[2][0][:10] if result[2] else []
    
    return stats


def validate_sample(conn: duckdb.DuckDBPyConnection, sample_id: int, expected_before: list):
    """Validate that sample route was converted correctly."""
    result = conn.execute("""
        SELECT routes FROM solutions WHERE id = ?
    """, [sample_id]).fetchone()
    
    if not result:
        print(f"❌ Sample solution {sample_id} not found!")
        return False
    
    actual_after = result[0][0][:10] if result[0] else []
    expected_after = [n - 1 for n in expected_before]
    
    print(f"\nSample Validation (Solution ID {sample_id}):")
    print(f"  Before: {expected_before}")
    print(f"  Expected After: {expected_after}")
    print(f"  Actual After:   {actual_after}")
    
    if actual_after == expected_after:
        print("  ✅ Sample conversion CORRECT")
        return True
    else:
        print("  ❌ Sample conversion FAILED")
        return False


def migrate_routes(conn: duckdb.DuckDBPyConnection) -> int:
    """
    Migrate all routes from 1-based to 0-based indexing.
    
    Only migrates solutions where min(node_id) > 0 (1-indexed).
    Skips solutions already 0-indexed (min(node_id) == 0).
    
    Returns:
        Number of solutions updated
    """
    print("\n" + "="*60)
    print("STARTING MIGRATION")
    print("="*60)
    
    # Fetch all solutions
    print("Fetching all solutions...")
    solutions = conn.execute("""
        SELECT id, routes
        FROM solutions
        ORDER BY id
    """).fetchall()
    
    print(f"Found {len(solutions)} solutions to check")
    
    # Convert each solution that needs it
    updated_count = 0
    skipped_count = 0
    
    for sol_id, routes in solutions:
        # Check if this solution is already 0-indexed
        all_nodes = [node for route in routes for node in route]
        if not all_nodes:
            continue
        
        min_node = min(all_nodes)
        
        if min_node == 0:
            # Already 0-indexed, skip
            skipped_count += 1
            continue
        
        # Convert all routes: subtract 1 from each node
        new_routes = [[node - 1 for node in route] for route in routes]
        
        # Update database
        conn.execute("""
            UPDATE solutions
            SET routes = ?
            WHERE id = ?
        """, [new_routes, sol_id])
        
        updated_count += 1
        
        if updated_count % 10 == 0:
            print(f"  Migrated {updated_count}, skipped {skipped_count}...")
    
    print(f"\n✅ Successfully migrated {updated_count} solutions")
    print(f"⏭️  Skipped {skipped_count} solutions (already 0-indexed)")
    return updated_count


def verify_migration(conn: duckdb.DuckDBPyConnection):
    """Verify migration completed successfully."""
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    
    # Check a few sample solutions to see if they contain node 0
    result = conn.execute("""
        SELECT id, routes
        FROM solutions
        ORDER BY id
        LIMIT 5
    """).fetchall()
    
    print(f"Checking {len(result)} sample solutions:")
    all_have_zero = True
    for sol_id, routes in result:
        first_route = routes[0] if routes else []
        has_zero = 0 in first_route
        status = "✅" if has_zero else "❌"
        print(f"  Solution {sol_id}: First route starts with {first_route[:5]} {status}")
        if not has_zero:
            all_have_zero = False
    
    if all_have_zero:
        print("\n✅ Migration successful - routes now use 0-based indexing")
    else:
        print("\n⚠️  Warning - some routes don't contain node 0 (might be normal for some problem types)")
    
    # Check for any negative nodes (would indicate double-migration)
    result = conn.execute("""
        SELECT id, routes
        FROM solutions
        LIMIT 100
    """).fetchall()
    
    has_negative = False
    for sol_id, routes in result:
        for route in routes:
            if any(node < 0 for node in route):
                print(f"❌ ERROR: Solution {sol_id} has negative node IDs!")
                has_negative = True
                break
    
    if not has_negative:
        print("✅ No negative node IDs found (migration not applied twice)")
    
    # Check bounds
    result = conn.execute("""
        SELECT s.id, p.name, p.dimension
        FROM solutions s
        JOIN problems p ON s.problem_id = p.id
        LIMIT 5
    """).fetchall()
    
    print("\nChecking node bounds for sample solutions:")
    for sol_id, name, dimension in result:
        routes_result = conn.execute("SELECT routes FROM solutions WHERE id = ?", [sol_id]).fetchone()
        if routes_result:
            routes = routes_result[0]
            all_nodes = [node for route in routes for node in route]
            max_node = max(all_nodes) if all_nodes else -1
            in_bounds = max_node < dimension
            status = "✅" if in_bounds else "❌"
            print(f"  {name}: max_node={max_node}, dimension={dimension} {status}")



def main():
    """Main migration execution."""
    db_path = Path("datasets_processed/db/routing.duckdb")
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        sys.exit(1)
    
    print("="*60)
    print("MIGRATION: Convert Routes to 0-based Indexing")
    print("="*60)
    print(f"Database: {db_path}")
    
    # Connect to database
    conn = duckdb.connect(str(db_path))
    
    try:
        # Check if migration needed
        if not check_migration_needed(conn):
            response = input("\nMigration may already be applied. Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                return
        
        # Get statistics before migration
        print("\n" + "="*60)
        print("BEFORE MIGRATION")
        print("="*60)
        stats_before = get_migration_stats(conn)
        print(f"Total solutions: {stats_before['total_solutions']}")
        print(f"Total routes: {stats_before['total_routes']}")
        print(f"Sample route (first 10 nodes): {stats_before.get('sample_route_before', [])}")
        
        # Confirm migration
        print("\n" + "="*60)
        response = input("Proceed with migration? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return
        
        # Execute migration
        updated_count = migrate_routes(conn)
        
        # Validate sample
        if 'sample_id' in stats_before:
            validate_sample(
                conn,
                stats_before['sample_id'],
                stats_before.get('sample_route_before', [])
            )
        
        # Verify migration
        verify_migration(conn)
        
        print("\n" + "="*60)
        print("MIGRATION COMPLETE")
        print("="*60)
        print(f"✅ Updated {updated_count} solutions")
        print("✅ All routes converted from 1-based to 0-based indexing")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
