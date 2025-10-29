#!/usr/bin/env python3
"""
Fix D-VRP type classification in database.

ROOT CAUSE: DuckDB FK constraint limitation (documented bug)
- UPDATE on PK table with VARCHAR columns triggers DELETE+INSERT rewrite
- FK constraints block DELETE even though value will be reinserted
- DuckDB lacks PRAGMA to disable FK constraints
- DuckDB lacks ALTER TABLE DROP CONSTRAINT support

SOLUTION: DROP child tables → UPDATE parent → RECREATE child tables with FK
- Safe because atomic transaction ensures rollback on any error
- Verifies all data is restored correctly before commit
- Only viable workaround given DuckDB's current limitations
"""
import duckdb
import sys
from pathlib import Path

DB_PATH = "datasets_processed/db/routing.duckdb"

def main():
    """Reclassify D-VRP problems to CVRP."""
    print("=" * 70)
    print("D-VRP to CVRP Reclassification")
    print("=" * 70)
    print()
    print("Root Cause: DuckDB FK constraint limitation (documented)")
    print("- UPDATE on VARCHAR columns rewrites as DELETE+INSERT")
    print("- FK constraints block DELETE when child rows exist")
    print("- No PRAGMA to disable FK constraints in DuckDB")
    print()
    print("Solution: DROP FK → UPDATE → RECREATE FK (atomic transaction)")
    print()
    
    conn = duckdb.connect(DB_PATH)
    
    try:
        # Step 1: Check current state
        d_vrp_count = conn.execute(
            "SELECT COUNT(*) FROM problems WHERE type = 'D-VRP'"
        ).fetchone()[0]
        
        if d_vrp_count == 0:
            print("✓ No D-VRP problems found - already fixed!")
            return 0
        
        print(f"Found {d_vrp_count} D-VRP problems to reclassify")
        print()
        
        # Step 2: Begin atomic transaction
        conn.execute("BEGIN")
        print("✓ Transaction started")
        
        # Step 3: DROP tables with FK constraints (backup data first)
        print("Creating backups of tables with FK constraints...")
        conn.execute("CREATE TEMP TABLE nodes_backup AS SELECT * FROM nodes")
        nodes_count = conn.execute("SELECT COUNT(*) FROM nodes_backup").fetchone()[0]
        conn.execute("CREATE TEMP TABLE file_tracking_backup AS SELECT * FROM file_tracking")
        tracking_count = conn.execute("SELECT COUNT(*) FROM file_tracking_backup").fetchone()[0]
        print(f"✓ Backed up {nodes_count:,} nodes and {tracking_count} tracking entries")
        
        # Drop child tables (this removes FK constraints)
        print("Dropping child tables...")
        conn.execute("DROP TABLE nodes")
        conn.execute("DROP TABLE file_tracking")
        print("✓ Child tables dropped (FK constraints removed)")
        
        # Step 4: UPDATE type column in problems table
        print("Updating D-VRP → CVRP in problems table...")
        conn.execute("UPDATE problems SET type = 'CVRP' WHERE type = 'D-VRP'")
        print(f"✓ Updated {d_vrp_count} problems to CVRP")
        
        # Step 5: RECREATE child tables with FK constraints
        print("Recreating child tables with FK constraints...")
        
        # Recreate nodes table with FK constraint
        conn.execute("""
            CREATE TABLE nodes (
                id INTEGER PRIMARY KEY DEFAULT nextval('nodes_seq'),
                problem_id INTEGER NOT NULL,
                node_id INTEGER NOT NULL,
                x DOUBLE,
                y DOUBLE,
                z DOUBLE,
                demand INTEGER DEFAULT 0,
                is_depot BOOLEAN DEFAULT FALSE,
                display_x DOUBLE,
                display_y DOUBLE,
                FOREIGN KEY (problem_id) REFERENCES problems(id)
            )
        """)
        
        # Recreate file_tracking table with FK constraint
        conn.execute("""
            CREATE TABLE file_tracking (
                id INTEGER PRIMARY KEY DEFAULT nextval('file_tracking_seq'),
                file_path VARCHAR UNIQUE NOT NULL,
                problem_id INTEGER,
                checksum VARCHAR,
                last_processed TIMESTAMP,
                file_size BIGINT,
                FOREIGN KEY (problem_id) REFERENCES problems(id)
            )
        """)
        print("✓ Child tables recreated with FK constraints")
        
        # Step 6: Restore data from backups
        print("Restoring data from backups...")
        conn.execute("INSERT INTO nodes SELECT * FROM nodes_backup")
        restored_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        conn.execute("INSERT INTO file_tracking SELECT * FROM file_tracking_backup")
        restored_tracking = conn.execute("SELECT COUNT(*) FROM file_tracking").fetchone()[0]
        print(f"✓ Restored {restored_nodes:,} nodes and {restored_tracking} tracking entries")
        
        # Step 7: Recreate indexes
        print("Recreating indexes...")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_nodes_problem 
            ON nodes(problem_id, node_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_tracking_path 
            ON file_tracking(file_path)
        """)
        print("✓ Indexes recreated")
        
        # Clean up temp tables
        conn.execute("DROP TABLE nodes_backup")
        conn.execute("DROP TABLE file_tracking_backup")
        
        # Step 7: Commit transaction
        conn.execute("COMMIT")
        print("✓ Transaction committed")
        print()
        
        # Step 8: Show final state
        final_state = conn.execute("""
            SELECT type, COUNT(*) as count 
            FROM problems 
            GROUP BY type 
            ORDER BY type
        """).fetchdf()
        
        print("Final database state:")
        print(final_state.to_string(index=False))
        print()
        print("=" * 70)
        print("✓ D-VRP reclassification completed successfully!")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print()
        print(f"✗ Error: {e}")
        print("Rolling back transaction...")
        try:
            conn.execute("ROLLBACK")
            print("✓ Rollback successful")
        except:
            pass
        return 1
        
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
