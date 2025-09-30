# Database Schema Documentation

## Overview

This document describes the database schema used by the TSPLIB95 ETL Converter, including table structures, relationships, and indexes.

## Entity-Relationship Diagram

```
┌─────────────┐
│  problems   │
│─────────────│
│ id (PK)     │
│ name        │◄───┐
│ type        │    │
│ dimension   │    │
│ capacity    │    │
│ ...         │    │
└─────────────┘    │
                   │
      ┌────────────┼────────────┐
      │            │            │
      │            │            │
┌─────▼─────┐ ┌────▼──────┐    │
│   nodes   │ │   edges   │    │
│───────────│ │───────────│    │
│ id (PK)   │ │ id (PK)   │    │
│ problem_id├─┤ problem_id├────┘
│ node_id   │ │ from_node │
│ x, y, z   │ │ to_node   │
│ demand    │ │ weight    │
│ is_depot  │ │ is_fixed  │
└───────────┘ └───────────┘
```

## Tables

### problems

Stores metadata about TSPLIB problem instances.

#### Schema

```sql
CREATE TABLE problems (
    id INTEGER PRIMARY KEY DEFAULT nextval('problems_id_seq'),
    name VARCHAR NOT NULL UNIQUE,
    type VARCHAR NOT NULL,
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
```

#### Column Descriptions

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | No | Auto-generated unique identifier |
| `name` | VARCHAR | No | Problem name (from TSPLIB file) |
| `type` | VARCHAR | No | Problem type (TSP, VRP, ATSP, etc.) |
| `comment` | TEXT | Yes | Problem description/comment |
| `dimension` | INTEGER | No | Number of nodes/cities |
| `capacity` | INTEGER | Yes | Vehicle capacity (VRP only) |
| `edge_weight_type` | VARCHAR | Yes | How edge weights are computed (EUC_2D, EXPLICIT, etc.) |
| `edge_weight_format` | VARCHAR | Yes | Matrix format (FULL_MATRIX, LOWER_DIAG_ROW, etc.) |
| `node_coord_type` | VARCHAR | Yes | Coordinate system type |
| `display_data_type` | VARCHAR | Yes | Display coordinate type |
| `file_path` | VARCHAR | No | Path to source TSPLIB file |
| `file_size` | INTEGER | Yes | Source file size in bytes |
| `created_at` | TIMESTAMP | No | When record was created |
| `updated_at` | TIMESTAMP | No | When record was last updated |

#### Indexes

- Primary key on `id`
- Unique constraint on `name`
- Index on `(type, dimension)` for filtering
- Index on `name` for lookups

#### Example Data

```
id | name      | type | dimension | edge_weight_type | capacity
---+-----------+------+-----------+------------------+----------
1  | berlin52  | TSP  | 52        | EUC_2D           | NULL
2  | eil22     | CVRP | 22        | EUC_2D           | 6000
3  | ft70      | ATSP | 70        | EXPLICIT         | NULL
```

### nodes

Stores individual nodes/cities/locations for each problem.

#### Schema

```sql
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY DEFAULT nextval('nodes_id_seq'),
    problem_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
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
```

#### Column Descriptions

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | No | Auto-generated unique identifier |
| `problem_id` | INTEGER | No | Foreign key to problems table |
| `node_id` | INTEGER | No | Original node ID from TSPLIB (1-based) |
| `x` | DOUBLE | Yes | X coordinate (NULL if not coordinate-based) |
| `y` | DOUBLE | Yes | Y coordinate (NULL if not coordinate-based) |
| `z` | DOUBLE | Yes | Z coordinate for 3D problems |
| `demand` | INTEGER | No | Node demand (VRP), default 0 |
| `is_depot` | BOOLEAN | No | True if this is a depot node (VRP) |
| `display_x` | DOUBLE | Yes | Display X coordinate (if different from x) |
| `display_y` | DOUBLE | Yes | Display Y coordinate (if different from y) |

#### Indexes

- Primary key on `id`
- Index on `problem_id`
- Unique constraint on `(problem_id, node_id)`
- Index on `(problem_id, node_id)` for efficient lookups

#### Example Data

```
id | problem_id | node_id | x     | y     | demand | is_depot
---+------------+---------+-------+-------+--------+----------
1  | 1          | 1       | 565.0 | 575.0 | 0      | false
2  | 1          | 2       | 25.0  | 185.0 | 0      | false
3  | 2          | 1       | 145.0 | 215.0 | 0      | true
4  | 2          | 2       | 151.0 | 264.0 | 1100   | false
```

### edges

Stores pairwise distances/weights between nodes.

#### Schema

```sql
CREATE TABLE edges (
    id INTEGER PRIMARY KEY DEFAULT nextval('edges_id_seq'),
    problem_id INTEGER NOT NULL,
    from_node INTEGER NOT NULL,
    to_node INTEGER NOT NULL,
    weight DOUBLE NOT NULL,
    is_fixed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (problem_id) REFERENCES problems(id),
    UNIQUE(problem_id, from_node, to_node)
);
```

#### Column Descriptions

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | No | Auto-generated unique identifier |
| `problem_id` | INTEGER | No | Foreign key to problems table |
| `from_node` | INTEGER | No | Source node (0-based normalized) |
| `to_node` | INTEGER | No | Target node (0-based normalized) |
| `weight` | DOUBLE | No | Edge weight/distance |
| `is_fixed` | BOOLEAN | No | True if edge is required (from FIXED_EDGES_SECTION) |

#### Important Notes

- **Indexing**: Uses 0-based indexing (converted from TSPLIB's 1-based)
- **Symmetry**: For symmetric problems, both directions may be stored
- **Self-loops**: May include edges where `from_node = to_node`

#### Indexes

- Primary key on `id`
- Index on `problem_id`
- Unique constraint on `(problem_id, from_node, to_node)`
- Index on `(problem_id, from_node, to_node)` for efficient edge lookups

#### Example Data

```
id | problem_id | from_node | to_node | weight  | is_fixed
---+------------+-----------+---------+---------+----------
1  | 1          | 0         | 1       | 521.22  | false
2  | 1          | 0         | 2       | 293.41  | false
3  | 3          | 0         | 0       | 9999999 | false
4  | 3          | 0         | 1       | 375.0   | false
```

## Sequences

Three sequences provide auto-incrementing IDs:

```sql
CREATE SEQUENCE problems_id_seq;
CREATE SEQUENCE nodes_id_seq;
CREATE SEQUENCE edges_id_seq;
```

## Relationships

### One-to-Many

- **problems → nodes**: One problem has many nodes
  - Foreign key: `nodes.problem_id` → `problems.id`
  
- **problems → edges**: One problem has many edges
  - Foreign key: `edges.problem_id` → `problems.id`

### Referential Integrity

- Foreign keys enforce that nodes and edges must reference valid problems
- When querying, always join through `problem_id`
- No CASCADE delete (must manually clean up nodes/edges when deleting problems)

## Common Query Patterns

### 1. Get Problem with All Data

```sql
-- Get problem metadata
SELECT * FROM problems WHERE name = 'berlin52';

-- Get all nodes
SELECT * FROM nodes 
WHERE problem_id = (SELECT id FROM problems WHERE name = 'berlin52')
ORDER BY node_id;

-- Get all edges
SELECT * FROM edges 
WHERE problem_id = (SELECT id FROM problems WHERE name = 'berlin52')
ORDER BY from_node, to_node;
```

### 2. Join Problems with Statistics

```sql
SELECT 
    p.name,
    p.type,
    p.dimension,
    COUNT(DISTINCT n.id) as node_count,
    COUNT(DISTINCT e.id) as edge_count
FROM problems p
LEFT JOIN nodes n ON p.id = n.problem_id
LEFT JOIN edges e ON p.id = e.problem_id
GROUP BY p.id, p.name, p.type, p.dimension;
```

### 3. Find Nodes by Coordinates

```sql
SELECT p.name, n.node_id, n.x, n.y
FROM nodes n
JOIN problems p ON n.problem_id = p.id
WHERE n.x BETWEEN 100 AND 200
  AND n.y BETWEEN 200 AND 300
  AND n.x IS NOT NULL;
```

### 4. Analyze Edge Weights

```sql
SELECT 
    p.name,
    COUNT(*) as edge_count,
    MIN(e.weight) as min_weight,
    AVG(e.weight) as avg_weight,
    MAX(e.weight) as max_weight,
    STDDEV(e.weight) as stddev_weight
FROM edges e
JOIN problems p ON e.problem_id = p.id
GROUP BY p.id, p.name;
```

### 5. Find VRP Depots

```sql
SELECT 
    p.name,
    n.node_id,
    n.x,
    n.y,
    n.demand
FROM nodes n
JOIN problems p ON n.problem_id = p.id
WHERE n.is_depot = TRUE
ORDER BY p.name, n.node_id;
```

## Index Usage

### When Indexes Are Used

1. **Primary Key Lookups**: `WHERE id = ?`
2. **Foreign Key Joins**: `JOIN ON problem_id = ...`
3. **Name Lookups**: `WHERE name = 'berlin52'`
4. **Type Filtering**: `WHERE type = 'TSP'`
5. **Combined Filters**: `WHERE type = 'TSP' AND dimension > 100`

### When to Add Custom Indexes

Consider adding indexes if you frequently query:

```sql
-- For range queries on coordinates
CREATE INDEX idx_nodes_coords ON nodes(x, y) WHERE x IS NOT NULL;

-- For demand-based queries
CREATE INDEX idx_nodes_demand ON nodes(demand) WHERE demand > 0;

-- For weight-based filtering
CREATE INDEX idx_edges_weight ON edges(weight);
```

## Data Types and Constraints

### Data Type Choices

- **INTEGER**: IDs, counts, dimensions (exact values)
- **DOUBLE**: Coordinates, weights (may have decimals)
- **VARCHAR**: Names, types (variable length text)
- **TEXT**: Comments (long text)
- **BOOLEAN**: Flags (true/false)
- **TIMESTAMP**: Audit timestamps

### Constraints

1. **NOT NULL**: Critical fields that must have values
2. **UNIQUE**: `(problem_id, node_id)` - one node per ID per problem
3. **UNIQUE**: `(problem_id, from_node, to_node)` - one edge per pair per problem
4. **UNIQUE**: `name` - problem names must be unique
5. **DEFAULT**: Provides sensible defaults (0, FALSE, CURRENT_TIMESTAMP)

## Database Size Estimates

### Storage Requirements

| Component | Size per Record | Example (1000 nodes) |
|-----------|----------------|---------------------|
| Problem | ~500 bytes | 500 bytes |
| Node | ~100 bytes | 100 KB |
| Edge (complete graph) | ~50 bytes | ~50 MB |

### Example Database Sizes

| Problems | Avg Dimension | Approx Size |
|----------|---------------|-------------|
| 10 small | 50 nodes | <5 MB |
| 100 medium | 200 nodes | ~200 MB |
| 1000 mixed | varies | ~2 GB |

## Performance Optimization

### Best Practices

1. **Use Indexes**: Ensure queries use existing indexes
2. **Batch Inserts**: Use transactions for multiple inserts
3. **Selective Queries**: Don't `SELECT *` if you only need specific columns
4. **Limit Results**: Use `LIMIT` for large result sets
5. **Analyze Queries**: Use `EXPLAIN` to understand query plans

### Example: Efficient Bulk Query

```sql
-- Good: Uses indexes, specific columns
SELECT p.name, COUNT(e.id) as edges
FROM problems p
JOIN edges e ON p.id = e.problem_id
WHERE p.type = 'TSP'
GROUP BY p.id, p.name;

-- Bad: No indexes used, all columns
SELECT * FROM edges
WHERE problem_id IN (
    SELECT id FROM problems WHERE type LIKE '%TSP%'
);
```

## Schema Evolution

### Adding New Columns

When adding features, extend tables carefully:

```sql
-- Add new column with default
ALTER TABLE nodes ADD COLUMN priority INTEGER DEFAULT 1;

-- Add index if needed
CREATE INDEX idx_nodes_priority ON nodes(priority);
```

### Version Tracking

Consider adding a schema_version table:

```sql
CREATE TABLE schema_version (
    version VARCHAR PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_version (version) VALUES ('1.0.0');
```

## See Also

- [User Guide](03-user-guide.md) - Using the database
- [Examples](05-examples.md) - Query examples
- [Command Reference](04-command-reference.md) - CLI commands for database operations
