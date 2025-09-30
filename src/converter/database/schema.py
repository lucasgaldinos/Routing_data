"""Database schema definitions for TSPLIB converter."""
from typing import List

# SQL for creating tables - reference docs/diagrams/database-schema.mmd
CREATE_PROBLEMS_TABLE = """
CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    type VARCHAR NOT NULL,  -- TSP|VRP|ATSP|HCP|SOP|TOUR
    comment TEXT,
    dimension INTEGER NOT NULL,
    capacity INTEGER,
    edge_weight_type VARCHAR,
    edge_weight_format VARCHAR,
    node_coord_type VARCHAR,
    display_data_type VARCHAR,
    file_path VARCHAR NOT NULL,
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_NODES_TABLE = """
CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY,
    problem_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,  -- Original 1-based ID from TSPLIB
    x DOUBLE,
    y DOUBLE,
    z DOUBLE,
    demand INTEGER DEFAULT 0,
    is_depot BOOLEAN DEFAULT FALSE,
    display_x DOUBLE,
    display_y DOUBLE,
    FOREIGN KEY (problem_id) REFERENCES problems(id),
    UNIQUE(problem_id, node_id)
);
"""

CREATE_EDGES_TABLE = """
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY,
    problem_id INTEGER NOT NULL,
    from_node INTEGER NOT NULL,  -- 0-based normalized
    to_node INTEGER NOT NULL,    -- 0-based normalized
    weight DOUBLE NOT NULL,
    is_fixed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (problem_id) REFERENCES problems(id),
    UNIQUE(problem_id, from_node, to_node)
);
"""

# Performance indexes
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_problems_type_dimension ON problems(type, dimension);",
    "CREATE INDEX IF NOT EXISTS idx_problems_name ON problems(name);",
    "CREATE INDEX IF NOT EXISTS idx_nodes_problem_id ON nodes(problem_id);",
    "CREATE INDEX IF NOT EXISTS idx_nodes_problem_node ON nodes(problem_id, node_id);",
    "CREATE INDEX IF NOT EXISTS idx_edges_problem_id ON edges(problem_id);",
    "CREATE INDEX IF NOT EXISTS idx_edges_from_to ON edges(problem_id, from_node, to_node);",
]

def get_schema_version() -> str:
    """Get current schema version."""
    return "1.0.0"

def get_all_table_creation_sql() -> List[str]:
    """Get all SQL statements for table creation."""
    return [
        CREATE_PROBLEMS_TABLE,
        CREATE_NODES_TABLE,
        CREATE_EDGES_TABLE
    ] + CREATE_INDEXES
