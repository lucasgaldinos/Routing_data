# DuckDB Database Usage Guide for Routing Problems

**Database**: `datasets/db/routing.duckdb`  
**Problems**: 188 routing problems (113 TSP, 47 CVRP, 19 ATSP, 9 HCP)  
**Nodes**: 469,631 total nodes across all problems  
**Purpose**: AI-optimized guide for external projects using only the DuckDB database

---

## Database Overview

### Schema Architecture

```mermaid
erDiagram
    problems ||--o{ nodes : "has"
    problems ||--o| edge_weight_matrices : "has"
    problems ||--o{ solutions : "has"
    problems ||--o{ file_tracking : "tracks"
    
    problems {
        INTEGER id PK
        VARCHAR name
        VARCHAR type "TSP|VRP|ATSP|HCP|SOP|TOUR"
        VARCHAR comment
        INTEGER dimension
        INTEGER capacity
        VARCHAR edge_weight_type "EUC_2D|EXPLICIT|GEO|ATT|etc"
        VARCHAR edge_weight_format "FULL_MATRIX|LOWER_ROW|etc"
        INTEGER capacity_vol "VRP variant field"
        INTEGER capacity_weight "VRP variant field"
        DOUBLE max_distance "VRP constraint"
        INTEGER service_time "VRP constraint"
        INTEGER vehicles "Number of vehicles"
        INTEGER depots "Number of depots"
        INTEGER periods "Multi-period VRP"
        BOOLEAN has_time_windows "VRPTW indicator"
        BOOLEAN has_pickup_delivery "VRPPD indicator"
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    
    nodes {
        INTEGER id PK
        INTEGER problem_id FK
        INTEGER node_id "0-based index"
        DOUBLE x "Coordinate (nullable)"
        DOUBLE y "Coordinate (nullable)"
        DOUBLE z "Coordinate (nullable)"
        INTEGER demand "Node demand (VRP)"
        BOOLEAN is_depot "Depot indicator"
        DOUBLE display_x "GEO converted to Euclidean"
        DOUBLE display_y "GEO converted to Euclidean"
    }
    
    edge_weight_matrices {
        INTEGER problem_id PK_FK "One matrix per EXPLICIT problem"
        INTEGER dimension
        VARCHAR matrix_format "FULL_MATRIX|LOWER_ROW|etc"
        BOOLEAN is_symmetric
        TEXT matrix_json "Full dimension×dimension 2D array as JSON"
    }
    
    solutions {
        INTEGER id PK
        INTEGER problem_id FK
        VARCHAR solution_name
        VARCHAR solution_type "TOUR|VRP_ROUTE"
        DOUBLE cost "Total cost/distance"
        INTEGER routes "2D array: routes[vehicle][node_sequence]"
        TIMESTAMP created_at
    }
    
    file_tracking {
        INTEGER id PK
        VARCHAR file_path UNIQUE
        INTEGER problem_id FK
        VARCHAR checksum "SHA-256"
        TIMESTAMP last_processed
        INTEGER file_size
    }
```

### Database Statistics

```sql
-- Summary by problem type
SELECT 
    type,
    COUNT(*) as count,
    ROUND(AVG(dimension), 2) as avg_dimension,
    MAX(dimension) as max_dimension,
    MIN(dimension) as min_dimension
FROM problems 
GROUP BY type;

-- Result:
-- CVRP: 47 problems (avg: 2,973.6, max: 30,001)
-- ATSP: 19 problems (avg: 127.53, max: 443)  
-- TSP: 113 problems (avg: 2,658.84, max: 85,900)
-- HCP: 9 problems (avg: 3,000.0, max: 5,000)
```

---

## Quick Start

### 1. Connection Examples

#### **Python (DuckDB + pandas)**

```python
import duckdb
import pandas as pd

# Read-only connection (recommended for analysis)
conn = duckdb.connect('datasets/db/routing.duckdb', read_only=True)

# Execute query and return pandas DataFrame
df = conn.execute("SELECT * FROM problems WHERE type = 'TSP' AND dimension < 100").df()

# Don't forget to close
conn.close()
```

#### **Python Context Manager (Best Practice)**

```python
import duckdb

with duckdb.connect('datasets/db/routing.duckdb', read_only=True) as conn:
    # Query problems
    problems = conn.execute("""
        SELECT id, name, type, dimension, edge_weight_type 
        FROM problems 
        WHERE dimension BETWEEN 50 AND 200
    """).df()
    
    # Get nodes for specific problem
    nodes = conn.execute("""
        SELECT node_id, x, y, demand, is_depot 
        FROM nodes 
        WHERE problem_id = ?
    """, [problems.iloc[0]['id']]).df()
```

#### **CLI Access**

```bash
# Open database interactively
duckdb datasets/db/routing.duckdb

# Execute query from command line
duckdb datasets/db/routing.duckdb "SELECT type, COUNT(*) FROM problems GROUP BY type;"

# Export query results to CSV
duckdb datasets/db/routing.duckdb "COPY (SELECT * FROM problems) TO 'problems.csv' (HEADER)"
```

#### **R (duckdb package)**

```r
library(duckdb)

# Connect
con <- dbConnect(duckdb::duckdb(), "datasets/db/routing.duckdb", read_only = TRUE)

# Query to data.frame
problems <- dbGetQuery(con, "SELECT * FROM problems WHERE type = 'TSP'")

# Clean up
dbDisconnect(con, shutdown = TRUE)
```

---

## Essential Query Patterns

### 2. Problem Discovery

#### **Find All TSP Problems**

```sql
SELECT id, name, dimension, edge_weight_type 
FROM problems 
WHERE type = 'TSP' 
ORDER BY dimension;
```

#### **Get CVRP Problems with Time Windows**

```sql
SELECT id, name, dimension, capacity, vehicles, service_time
FROM problems 
WHERE type = 'VRP' AND has_time_windows = true;
```

#### **Problems by Dimension Range**

```sql
-- Small problems (useful for testing algorithms)
SELECT name, type, dimension 
FROM problems 
WHERE dimension BETWEEN 20 AND 100 
ORDER BY type, dimension;
```

#### **Problems with Explicit Distance Matrices**

```sql
SELECT p.id, p.name, p.dimension, ewm.is_symmetric, ewm.matrix_format
FROM problems p
JOIN edge_weight_matrices ewm ON p.id = ewm.problem_id
WHERE p.edge_weight_type = 'EXPLICIT';
```

### 3. Node Retrieval

#### **Get All Nodes for a Problem**

```sql
-- Using problem name
SELECT n.node_id, n.x, n.y, n.demand, n.is_depot
FROM nodes n
JOIN problems p ON n.problem_id = p.id
WHERE p.name = 'berlin52'
ORDER BY n.node_id;
```

#### **Get Only Depot Nodes (VRP)**

```sql
SELECT p.name, n.node_id, n.x, n.y
FROM nodes n
JOIN problems p ON n.problem_id = p.id
WHERE n.is_depot = true AND p.type = 'VRP';
```

#### **Get Customer Nodes with Demand**

```sql
SELECT n.node_id, n.x, n.y, n.demand
FROM nodes n
JOIN problems p ON n.problem_id = p.id
WHERE p.name = 'att48' AND n.is_depot = false
ORDER BY n.demand DESC;
```

### 4. Distance Matrix Access

#### **Retrieve Full Distance Matrix (EXPLICIT problems)**

```python
import duckdb
import json

with duckdb.connect('datasets/db/routing.duckdb', read_only=True) as conn:
    # Get matrix for br17 ATSP problem
    result = conn.execute("""
        SELECT dimension, matrix_json, is_symmetric 
        FROM edge_weight_matrices ewm
        JOIN problems p ON ewm.problem_id = p.id
        WHERE p.name = 'br17'
    """).fetchone()
    
    dimension = result[0]
    matrix = json.loads(result[1])  # 2D list: matrix[i][j] = distance i→j
    is_symmetric = result[2]
    
    # Access distance from node 0 to node 5
    distance = matrix[0][5]
```

**Matrix Format Types**:

- `FULL_MATRIX`: Complete dimension×dimension matrix
- `LOWER_ROW`: Lower triangular (symmetric problems)
- `LOWER_DIAG_ROW`: Lower triangular with diagonal
- `UPPER_ROW` / `UPPER_DIAG_ROW`: Upper triangular variants

**Important**: All matrices stored as **full dimension×dimension** JSON arrays regardless of original format.

### 5. Coordinate-based Distance Calculation

#### **EUC_2D (Euclidean 2D)**

```python
import numpy as np

# Get coordinates
nodes = conn.execute("""
    SELECT node_id, x, y 
    FROM nodes 
    WHERE problem_id = (SELECT id FROM problems WHERE name = 'berlin52')
    ORDER BY node_id
""").df()

# Calculate distance matrix
def euclidean_distance(x1, y1, x2, y2):
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

# Distance from node 0 to node 1
dist = euclidean_distance(nodes.iloc[0]['x'], nodes.iloc[0]['y'],
                          nodes.iloc[1]['x'], nodes.iloc[1]['y'])
```

#### **GEO (Geographical Coordinates)**

```python
import numpy as np

def geo_distance(lat1, lon1, lat2, lon2):
    """TSPLIB95 geographical distance formula"""
    PI = 3.141592
    RRR = 6378.388  # Earth radius in km
    
    # Convert to radians
    q1_lat = np.pi * lat1 / 180.0
    q1_lon = np.pi * lon1 / 180.0
    q2_lat = np.pi * lat2 / 180.0
    q2_lon = np.pi * lon2 / 180.0
    
    # Spherical law of cosines
    dlon = q1_lon - q2_lon
    cos_angle = (np.sin(q1_lat) * np.sin(q2_lat) + 
                 np.cos(q1_lat) * np.cos(q2_lat) * np.cos(dlon))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Numerical stability
    
    return int(RRR * np.arccos(cos_angle) + 1.0)  # TSPLIB rounds down

# Query GEO problem
nodes = conn.execute("""
    SELECT node_id, x as longitude, y as latitude
    FROM nodes 
    WHERE problem_id = (SELECT id FROM problems WHERE edge_weight_type = 'GEO')
    ORDER BY node_id
""").df()
```

#### **ATT (Pseudo-Euclidean)**

```python
import numpy as np

def att_distance(x1, y1, x2, y2):
    """ATT distance (rounding up)"""
    xd = x1 - x2
    yd = y1 - y2
    rij = np.sqrt((xd**2 + yd**2) / 10.0)
    tij = int(np.round(rij))
    if tij < rij:
        return tij + 1
    return tij
```

---

## Advanced Queries

### 6. Aggregations and Analytics

#### **Problem Type Distribution**

```sql
SELECT 
    type,
    COUNT(*) as count,
    ROUND(AVG(dimension), 2) as avg_nodes,
    ROUND(SUM(dimension) * 100.0 / (SELECT SUM(dimension) FROM problems), 2) as pct_total_nodes
FROM problems
GROUP BY type
ORDER BY count DESC;
```

#### **VRP Variant Characteristics**

```sql
SELECT 
    name,
    dimension,
    capacity,
    vehicles,
    has_time_windows,
    has_pickup_delivery,
    service_time,
    max_distance
FROM problems
WHERE type = 'VRP' AND capacity IS NOT NULL
ORDER BY dimension;
```

#### **Node Count by Problem**

```sql
SELECT 
    p.name,
    p.type,
    COUNT(n.id) as actual_nodes,
    p.dimension as declared_dimension,
    CASE WHEN COUNT(n.id) = p.dimension THEN 'OK' ELSE 'MISMATCH' END as validation
FROM problems p
LEFT JOIN nodes n ON p.id = n.problem_id
GROUP BY p.id, p.name, p.type, p.dimension
ORDER BY p.dimension DESC;
```

### 7. Filtering and Subsetting

#### **Get Benchmark Problem Set**

```sql
-- Classic TSP benchmarks under 1000 nodes
SELECT name, dimension, edge_weight_type
FROM problems
WHERE type = 'TSP' 
  AND dimension <= 1000 
  AND edge_weight_type = 'EUC_2D'
  AND name NOT LIKE 'xray%'  -- Exclude special problems
ORDER BY dimension;
```

#### **Large-Scale Problems Only**

```sql
SELECT name, type, dimension
FROM problems
WHERE dimension >= 10000
ORDER BY dimension DESC;

-- Result: d18512, brd14051, rl11849, xray14012_1, xray14012_2, d15112, usa13509, etc.
```

### 8. Join Patterns

#### **Problem + Nodes in One Query**

```sql
SELECT 
    p.name as problem,
    p.dimension,
    n.node_id,
    n.x,
    n.y,
    n.demand,
    n.is_depot
FROM problems p
JOIN nodes n ON p.id = n.problem_id
WHERE p.name = 'att48'
ORDER BY n.node_id;
```

#### **Problem + Matrix Metadata**

```sql
SELECT 
    p.name,
    p.dimension,
    p.edge_weight_type,
    ewm.matrix_format,
    ewm.is_symmetric,
    LENGTH(ewm.matrix_json) as matrix_size_bytes
FROM problems p
LEFT JOIN edge_weight_matrices ewm ON p.id = ewm.problem_id
WHERE p.type = 'ATSP';
```

---

## Indexes for Performance

### Current Indexes (Pre-built)

```sql
-- Automatically utilized by query planner:
idx_problems_type_dim      -- ON problems(type, dimension)
idx_nodes_problem          -- ON nodes(problem_id, node_id)
idx_solutions_problem      -- ON solutions(problem_id)
idx_edge_matrices_problem  -- ON edge_weight_matrices(problem_id)
idx_file_tracking_path     -- ON file_tracking(file_path)
```

**Query Optimization Tips**:

1. **Filter by `type` and `dimension`** → Uses `idx_problems_type_dim`
2. **Join nodes via `problem_id`** → Uses `idx_nodes_problem`
3. **Lookup by problem name** → Sequential scan (only 188 rows, fast)
4. **Order by `node_id` after filtering** → Index covers ordering

---

## Data Quality Notes

### Index Convention

**Critical**: Database uses **0-based indexing** for `nodes.node_id`, while TSPLIB95 files use 1-based.  
**Conversion**: Automatic during ETL (subtract 1 from TSPLIB node IDs)

```sql
-- Node IDs start at 0
SELECT MIN(node_id), MAX(node_id) 
FROM nodes 
WHERE problem_id = 1;

-- Result: 0, 51 (for berlin52 with 52 nodes)
```

### Hybrid Storage Model

1. **Coordinate-based problems** (`EUC_2D`, `GEO`, `ATT`, `CEIL_2D`, `MAN_2D`, `MAX_2D`):
   - Nodes stored in `nodes` table with `x`, `y`, `z` coordinates
   - **No entry in `edge_weight_matrices`**
   - Calculate distances on-demand from coordinates

2. **Explicit matrix problems** (`EXPLICIT` edge weight type):
   - **Distance matrix stored** in `edge_weight_matrices.matrix_json`
   - Nodes table may be **empty** or contain display coordinates only
   - Use matrix for all distance lookups

**Example Check**:

```sql
SELECT 
    p.name,
    p.edge_weight_type,
    COUNT(DISTINCT n.id) as node_count,
    CASE WHEN ewm.problem_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_matrix
FROM problems p
LEFT JOIN nodes n ON p.id = n.problem_id
LEFT JOIN edge_weight_matrices ewm ON p.id = ewm.problem_id
WHERE p.name IN ('berlin52', 'br17')
GROUP BY p.id, p.name, p.edge_weight_type, ewm.problem_id;

-- berlin52: EUC_2D, 52 nodes, NO matrix
-- br17: EXPLICIT, 0 nodes, YES matrix (17×17)
```

### VRP-Specific Fields

```sql
-- Fields populated only for VRP problems:
capacity            -- Vehicle capacity
capacity_vol        -- Volume capacity variant
capacity_weight     -- Weight capacity variant
max_distance        -- Distance constraint
service_time        -- Service time at each node
vehicles            -- Number of vehicles available
depots              -- Number of depot locations
has_time_windows    -- VRPTW indicator (boolean)
has_pickup_delivery -- VRPPD indicator (boolean)
```

---

## Export and Integration

### Export to CSV

```bash
# Export entire problems table
duckdb datasets/db/routing.duckdb "COPY problems TO 'problems.csv' (HEADER, DELIMITER ',')"

# Export filtered subset
duckdb datasets/db/routing.duckdb \
  "COPY (SELECT * FROM problems WHERE type = 'TSP' AND dimension < 200) TO 'small_tsp.csv' (HEADER)"
```

### Export to Parquet

```bash
# High compression, columnar format
duckdb datasets/db/routing.duckdb \
  "COPY (SELECT p.*, array_agg(n.node_id ORDER BY n.node_id) as nodes 
         FROM problems p 
         LEFT JOIN nodes n ON p.id = n.problem_id 
         GROUP BY p.id) 
   TO 'problems_with_nodes.parquet' (FORMAT PARQUET, COMPRESSION 'ZSTD')"
```

### Python Integration Examples

#### **Load Problem as NetworkX Graph (TSP/VRP)**

```python
import duckdb
import networkx as nx
import numpy as np

def load_as_graph(problem_name, db_path='datasets/db/routing.duckdb'):
    """Load TSP problem as complete weighted graph"""
    with duckdb.connect(db_path, read_only=True) as conn:
        # Get problem metadata
        meta = conn.execute("""
            SELECT id, type, dimension, edge_weight_type 
            FROM problems WHERE name = ?
        """, [problem_name]).fetchone()
        
        if not meta:
            raise ValueError(f"Problem '{problem_name}' not found")
        
        problem_id, ptype, dimension, ewtype = meta
        
        # Create graph
        G = nx.Graph() if ptype == 'TSP' else nx.DiGraph()
        
        # Add nodes
        nodes = conn.execute("""
            SELECT node_id, x, y, demand, is_depot 
            FROM nodes WHERE problem_id = ? 
            ORDER BY node_id
        """, [problem_id]).df()
        
        for _, node in nodes.iterrows():
            G.add_node(node['node_id'], 
                      x=node['x'], 
                      y=node['y'], 
                      demand=node['demand'],
                      is_depot=node['is_depot'])
        
        # Add edges with distances
        if ewtype == 'EXPLICIT':
            # Load distance matrix
            import json
            matrix_json = conn.execute("""
                SELECT matrix_json FROM edge_weight_matrices 
                WHERE problem_id = ?
            """, [problem_id]).fetchone()[0]
            matrix = json.loads(matrix_json)
            
            for i in range(dimension):
                for j in range(dimension):
                    if i != j:
                        G.add_edge(i, j, weight=matrix[i][j])
        
        elif ewtype == 'EUC_2D':
            # Calculate Euclidean distances
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    x1, y1 = nodes.iloc[i][['x', 'y']]
                    x2, y2 = nodes.iloc[j][['x', 'y']]
                    dist = np.sqrt((x1-x2)**2 + (y1-y2)**2)
                    G.add_edge(i, j, weight=dist)
                    if ptype == 'TSP':
                        G.add_edge(j, i, weight=dist)  # Symmetric
        
        return G

# Usage
G = load_as_graph('berlin52')
print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
```

#### **Batch Load Multiple Problems**

```python
import duckdb
import pandas as pd

def load_problem_batch(problem_type='TSP', max_dimension=500, db_path='datasets/db/routing.duckdb'):
    """Load all problems matching criteria"""
    with duckdb.connect(db_path, read_only=True) as conn:
        problems = conn.execute("""
            SELECT id, name, dimension, edge_weight_type 
            FROM problems 
            WHERE type = ? AND dimension <= ?
            ORDER BY dimension
        """, [problem_type, max_dimension]).df()
        
        results = []
        for _, prob in problems.iterrows():
            # Get nodes
            nodes = conn.execute("""
                SELECT node_id, x, y FROM nodes 
                WHERE problem_id = ? ORDER BY node_id
            """, [prob['id']]).df()
            
            results.append({
                'name': prob['name'],
                'dimension': prob['dimension'],
                'coordinates': nodes[['x', 'y']].values
            })
        
        return results

# Load all small TSPs
small_tsps = load_problem_batch('TSP', max_dimension=100)
```

---

## Common Pitfalls and Solutions

### ❌ **Mistake**: Assuming 1-based node indexing

```sql
-- WRONG: Looking for node ID 1 as first node
SELECT * FROM nodes WHERE problem_id = 5 AND node_id = 1;
```

✅ **Correct**: Use 0-based indexing

```sql
SELECT * FROM nodes WHERE problem_id = 5 AND node_id = 0;
```

### ❌ **Mistake**: Trying to access matrix for coordinate-based problems

```python
# WRONG: berlin52 has no matrix (EUC_2D)
matrix = conn.execute("""
    SELECT matrix_json FROM edge_weight_matrices ewm
    JOIN problems p ON ewm.problem_id = p.id
    WHERE p.name = 'berlin52'
""").fetchone()  # Returns None!
```

✅ **Correct**: Check edge_weight_type first

```python
result = conn.execute("""
    SELECT edge_weight_type FROM problems WHERE name = 'berlin52'
""").fetchone()

if result[0] == 'EXPLICIT':
    # Load from matrix
    pass
else:
    # Calculate from coordinates
    pass
```

### ❌ **Mistake**: Forgetting to handle NULL coordinates

```python
# WRONG: ATSP problems may have no coordinates
nodes = conn.execute("SELECT x, y FROM nodes WHERE problem_id = 10").df()
distances = np.sqrt((nodes['x']**2 + nodes['y']**2))  # NaN values!
```

✅ **Correct**: Filter or check for NULL

```sql
SELECT node_id, x, y FROM nodes 
WHERE problem_id = 10 AND x IS NOT NULL AND y IS NOT NULL;
```

---

## Performance Benchmarks

### Query Performance (on 188 problems, 469k nodes)

| Query | Rows Returned | Avg Time | Notes |
|-------|---------------|----------|-------|
| `SELECT * FROM problems` | 188 | <1ms | Full table scan (small) |
| `SELECT * FROM nodes WHERE problem_id = 1` | 52 | <1ms | Index hit |
| `SELECT * FROM nodes` | 469,631 | ~50ms | Full scan |
| `JOIN problems + nodes (1 problem)` | 52 | <2ms | Indexed join |
| `COUNT(DISTINCT problem_id) FROM nodes` | 1 | ~30ms | Aggregate |
| `GROUP BY type` aggregation | 4 | <5ms | Indexed group |

### Database Size

- **Total**: ~92 MB
- **Problems table**: <100 KB (188 rows, 19 columns)
- **Nodes table**: ~60 MB (469,631 rows, 10 columns)
- **Edge weight matrices**: ~30 MB (19 EXPLICIT problems, JSON matrices)
- **Solutions**: <1 KB (empty initially)
- **File tracking**: <50 KB (232 tracked files)

---

## Troubleshooting

### Connection Issues

```python
# Error: "database is locked"
# Solution: Ensure read_only=True for concurrent access
conn = duckdb.connect('datasets/db/routing.duckdb', read_only=True)

# Error: "file not found"
# Solution: Use absolute path
import os
db_path = os.path.abspath('datasets/db/routing.duckdb')
conn = duckdb.connect(db_path, read_only=True)
```

### Memory Issues (Large Queries)

```python
# Problem: Loading 85k-node problem crashes
# Solution: Use chunked iteration or limit columns
import duckdb

with duckdb.connect('datasets/db/routing.duckdb', read_only=True) as conn:
    # Instead of loading all at once
    # nodes = conn.execute("SELECT * FROM nodes WHERE problem_id = 150").df()
    
    # Use batched fetching
    result = conn.execute("SELECT node_id, x, y FROM nodes WHERE problem_id = 150")
    batch_size = 10000
    while True:
        batch = result.fetchmany(batch_size)
        if not batch:
            break
        # Process batch
        print(f"Processed {len(batch)} nodes")
```

---

## Additional Resources

### Related Files in Repository

- **Schema Documentation**: `docs/diagrams/database-schema.md` (includes full ER diagram)
- **Architecture Design**: `docs/reference/ARCHITECTURE.md` (design decisions, hybrid storage)
- **CLI Reference**: Run `uv run converter --help` for database generation commands
- **Test Suite**: `tests/test_converter/test_database_operations.py` (usage examples)

### External Documentation

- **DuckDB SQL Reference**: <https://duckdb.org/docs/sql/introduction>
- **TSPLIB95 Format Spec**: See `TSPLIB95.md` in repository root
- **Distance Functions**: `src/tsplib_parser/distances.py` (reference implementations)

---

## Summary Checklist

**For AI Models / External Projects**:

✅ **Database Connection**: Use `duckdb.connect('datasets/db/routing.duckdb', read_only=True)`  
✅ **Node Indexing**: 0-based (not 1-based like TSPLIB files)  
✅ **Distance Retrieval**:

- EXPLICIT problems → Query `edge_weight_matrices.matrix_json`
- Coordinate-based → Calculate from `nodes.x, nodes.y` using appropriate formula
✅ **VRP Problems**: Check `has_time_windows`, `capacity`, `vehicles` fields  
✅ **Query Optimization**: Use indexed columns (`type`, `dimension`, `problem_id`)  
✅ **Export**: Use `COPY` command for CSV/Parquet export  
✅ **Problem Stats**: 188 problems (113 TSP, 47 CVRP, 19 ATSP, 9 HCP)  

**Key Design Insight**: Hybrid storage model optimizes space—coordinate-based problems store only nodes, explicit problems store full matrices. Always check `edge_weight_type` before accessing data.

---

**Database Version**: Generated 2025-10-28  
**Problems**: 188 total (no Solomon instances present)  
**Nodes**: 469,631 total  
**Size**: ~92 MB  
