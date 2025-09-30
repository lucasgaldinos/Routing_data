# Examples and Usage Scenarios

## Overview

This document provides real-world examples of using the TSPLIB95 ETL Converter for common tasks and scenarios.

## Example 1: Analyzing a Classic TSP Problem

**Scenario**: You want to analyze the famous berlin52 TSP problem.

### Steps

```bash
# 1. Parse the problem
python -m src.converter.cli.commands parse datasets_raw/problems/tsp/berlin52.tsp
```

Output:
```
✓ Successfully processed datasets_raw/problems/tsp/berlin52.tsp
  Problem: berlin52 (TSP)
  Dimension: 52
  Nodes: 52
  Edges: 1378
  Database ID: 1
```

```bash
# 2. Query node coordinates
duckdb datasets/db/routing.duckdb << 'EOF'
SELECT node_id, x, y
FROM nodes
WHERE problem_id = (SELECT id FROM problems WHERE name = 'berlin52')
ORDER BY node_id
LIMIT 10;
EOF
```

Output:
```
┌─────────┬────────┬────────┐
│ node_id │   x    │   y    │
├─────────┼────────┼────────┤
│       1 │  565.0 │  575.0 │
│       2 │   25.0 │  185.0 │
│       3 │  345.0 │  750.0 │
│       4 │  945.0 │  685.0 │
│       5 │  845.0 │  655.0 │
│       6 │  880.0 │  660.0 │
│       7 │   25.0 │  230.0 │
│       8 │  525.0 │ 1000.0 │
│       9 │  580.0 │ 1175.0 │
│      10 │  650.0 │ 1130.0 │
└─────────┴────────┴────────┘
```

```bash
# 3. Analyze edge weights
duckdb datasets/db/routing.duckdb << 'EOF'
SELECT 
    COUNT(*) as total_edges,
    MIN(weight) as min_distance,
    AVG(weight) as avg_distance,
    MAX(weight) as max_distance
FROM edges
WHERE problem_id = (SELECT id FROM problems WHERE name = 'berlin52');
EOF
```

Output:
```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ total_edges  │ min_distance │ avg_distance │ max_distance │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ 1378         │ 0.0          │ 553.54       │ 1716.0       │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

### Analysis

- Berlin52 has 52 cities
- Distances range from 0 to 1716 units
- Average distance between cities is ~554 units
- All coordinates are available for visualization

---

## Example 2: Comparing TSP and ATSP Problems

**Scenario**: Compare symmetric (TSP) and asymmetric (ATSP) problems.

### Steps

```bash
# Parse both problems
python -m src.converter.cli.commands parse datasets_raw/problems/tsp/gr17.tsp
python -m src.converter.cli.commands parse datasets_raw/problems/atsp/ft70.atsp
```

```bash
# Compare edge counts and characteristics
duckdb datasets/db/routing.duckdb << 'EOF'
SELECT 
    p.name,
    p.type,
    p.dimension,
    p.edge_weight_type,
    COUNT(e.id) as edge_count,
    p.dimension * (p.dimension - 1) as max_directed_edges,
    ROUND(100.0 * COUNT(e.id) / (p.dimension * (p.dimension - 1)), 2) as density_pct
FROM problems p
LEFT JOIN edges e ON p.id = e.problem_id
WHERE p.name IN ('gr17', 'ft70')
GROUP BY p.id, p.name, p.type, p.dimension, p.edge_weight_type;
EOF
```

Output:
```
┌───────┬──────┬───────────┬─────────────────────┬────────────┬────────────────────┬─────────────┐
│ name  │ type │ dimension │  edge_weight_type   │ edge_count │ max_directed_edges │ density_pct │
├───────┼──────┼───────────┼─────────────────────┼────────────┼────────────────────┼─────────────┤
│ gr17  │ TSP  │ 17        │ EXPLICIT            │ 153        │ 272                │ 56.25       │
│ ft70  │ ATSP │ 70        │ EXPLICIT            │ 4900       │ 4830               │ 101.45      │
└───────┴──────┴───────────┴─────────────────────┴────────────┴────────────────────┴─────────────┘
```

### Analysis

- TSP (gr17) is sparse: only 56% of possible edges stored
- ATSP (ft70) is complete: >100% because includes self-loops
- Both use EXPLICIT weights (no coordinates)

---

## Example 3: Working with VRP Problems

**Scenario**: Analyze a Vehicle Routing Problem with depots and demands.

### Steps

```bash
# Parse VRP problem
python -m src.converter.cli.commands parse datasets_raw/problems/vrp/eil22.vrp
```

```bash
# Find depot and analyze demands
duckdb datasets/db/routing.duckdb << 'EOF'
SELECT 
    node_id,
    x,
    y,
    demand,
    CASE WHEN is_depot THEN 'DEPOT' ELSE 'Customer' END as node_type
FROM nodes
WHERE problem_id = (SELECT id FROM problems WHERE name = 'eil22')
ORDER BY is_depot DESC, node_id
LIMIT 10;
EOF
```

Output:
```
┌─────────┬───────┬───────┬────────┬───────────┐
│ node_id │   x   │   y   │ demand │ node_type │
├─────────┼───────┼───────┼────────┼───────────┤
│ 1       │ 145.0 │ 215.0 │ 0      │ DEPOT     │
│ 2       │ 151.0 │ 264.0 │ 1100   │ Customer  │
│ 3       │ 159.0 │ 261.0 │ 700    │ Customer  │
│ 4       │ 130.0 │ 254.0 │ 800    │ Customer  │
│ 5       │ 128.0 │ 252.0 │ 1400   │ Customer  │
│ 6       │ 163.0 │ 247.0 │ 2100   │ Customer  │
│ 7       │ 146.0 │ 246.0 │ 400    │ Customer  │
│ 8       │ 161.0 │ 242.0 │ 800    │ Customer  │
│ 9       │ 142.0 │ 239.0 │ 100    │ Customer  │
│ 10      │ 163.0 │ 236.0 │ 500    │ Customer  │
└─────────┴───────┴───────┴────────┴───────────┘
```

```bash
# Calculate total demand and check against capacity
duckdb datasets/db/routing.duckdb << 'EOF'
SELECT 
    p.name,
    p.capacity as vehicle_capacity,
    SUM(n.demand) as total_demand,
    CEIL(SUM(n.demand) * 1.0 / p.capacity) as min_vehicles_needed
FROM problems p
JOIN nodes n ON p.id = n.problem_id
WHERE p.name = 'eil22'
GROUP BY p.id, p.name, p.capacity;
EOF
```

Output:
```
┌────────┬──────────────────┬──────────────┬─────────────────────┐
│  name  │ vehicle_capacity │ total_demand │ min_vehicles_needed │
├────────┼──────────────────┼──────────────┼─────────────────────┤
│ eil22  │ 6000             │ 22500        │ 4                   │
└────────┴──────────────────┴──────────────┴─────────────────────┘
```

### Analysis

- Problem has 1 depot (node 1 with demand 0)
- 21 customers with varying demands
- Total demand is 22,500 units
- With vehicle capacity of 6,000, need at least 4 vehicles

---

## Example 4: Batch Processing Multiple Files

**Scenario**: Parse all TSP files in a directory.

### Bash Script

```bash
#!/bin/bash
# parse_all_tsp.sh

# Directory containing TSP files
TSP_DIR="datasets_raw/problems/tsp"

# Counter for progress
count=0
total=$(ls -1 "$TSP_DIR"/*.tsp 2>/dev/null | wc -l)

echo "Found $total TSP files to process"

# Parse each file
for file in "$TSP_DIR"/*.tsp; do
    if [ -f "$file" ]; then
        count=$((count + 1))
        echo "[$count/$total] Processing: $(basename $file)"
        
        python -m src.converter.cli.commands parse "$file" 2>&1 | grep "✓\|✗"
        
        if [ $? -eq 0 ]; then
            echo "  Success"
        else
            echo "  Failed"
        fi
    fi
done

echo "Completed processing $count files"

# Show final statistics
echo ""
echo "Database Statistics:"
python -m src.converter.cli.commands stats
```

### Usage

```bash
chmod +x parse_all_tsp.sh
./parse_all_tsp.sh
```

### Output

```
Found 12 TSP files to process
[1/12] Processing: a280.tsp
✓ Successfully processed datasets_raw/problems/tsp/a280.tsp
  Success
[2/12] Processing: berlin52.tsp
✓ Successfully processed datasets_raw/problems/tsp/berlin52.tsp
  Success
...
Completed processing 12 files

Database Statistics:
  Total Problems: 12
  Total Nodes: 2453
  Total Edges: 125687
```

---

## Example 5: Finding Coordinate vs Weight-Based Problems

**Scenario**: Identify which problems have coordinates for visualization.

### Query

```sql
-- Save to find_coord_problems.sql
SELECT 
    p.name,
    p.type,
    p.dimension,
    CASE 
        WHEN p.edge_weight_type = 'EUC_2D' THEN 'Has Coordinates'
        WHEN p.edge_weight_type = 'EXPLICIT' THEN 'Weight Matrix Only'
        ELSE 'Other'
    END as data_type,
    COUNT(DISTINCT CASE WHEN n.x IS NOT NULL THEN n.id END) as nodes_with_coords
FROM problems p
LEFT JOIN nodes n ON p.id = n.problem_id
GROUP BY p.id, p.name, p.type, p.dimension, p.edge_weight_type
ORDER BY data_type, p.dimension;
```

### Execute

```bash
duckdb datasets/db/routing.duckdb < find_coord_problems.sql
```

### Output

```
┌────────────┬──────┬───────────┬──────────────────────┬────────────────────┐
│    name    │ type │ dimension │      data_type       │ nodes_with_coords  │
├────────────┼──────┼───────────┼──────────────────────┼────────────────────┤
│ eil22      │ CVRP │ 22        │ Has Coordinates      │ 22                 │
│ berlin52   │ TSP  │ 52        │ Has Coordinates      │ 52                 │
│ a280       │ TSP  │ 280       │ Has Coordinates      │ 280                │
│ gr17       │ TSP  │ 17        │ Weight Matrix Only   │ 0                  │
│ ft70       │ ATSP │ 70        │ Weight Matrix Only   │ 0                  │
│ ft53.1.sop │ SOP  │ 54        │ Weight Matrix Only   │ 0                  │
└────────────┴──────┴───────────┴──────────────────────┴────────────────────┘
```

---

## Example 6: Exporting Data for Analysis

**Scenario**: Export problem data to CSV for use in other tools.

### Export Nodes

```bash
duckdb datasets/db/routing.duckdb << 'EOF'
COPY (
    SELECT 
        p.name as problem_name,
        n.node_id,
        n.x,
        n.y,
        n.demand,
        n.is_depot
    FROM nodes n
    JOIN problems p ON n.problem_id = p.id
    WHERE p.name = 'berlin52'
    ORDER BY n.node_id
) TO 'berlin52_nodes.csv' (HEADER, DELIMITER ',');
EOF
```

### Export Edge Weights

```bash
duckdb datasets/db/routing.duckdb << 'EOF'
COPY (
    SELECT 
        e.from_node,
        e.to_node,
        e.weight
    FROM edges e
    JOIN problems p ON e.problem_id = p.id
    WHERE p.name = 'berlin52'
    ORDER BY e.from_node, e.to_node
) TO 'berlin52_edges.csv' (HEADER, DELIMITER ',');
EOF
```

### Use in Python

```python
import pandas as pd

# Load exported data
nodes = pd.read_csv('berlin52_nodes.csv')
edges = pd.read_csv('berlin52_edges.csv')

# Basic analysis
print(f"Number of nodes: {len(nodes)}")
print(f"Number of edges: {len(edges)}")
print(f"\nNode coordinate ranges:")
print(f"X: {nodes['x'].min()} to {nodes['x'].max()}")
print(f"Y: {nodes['y'].min()} to {nodes['y'].max()}")
```

---

## Example 7: Validating Data Quality

**Scenario**: Check for potential data quality issues.

### Comprehensive Validation Script

```bash
#!/bin/bash
# validate_database.sh

echo "=== Database Validation Report ==="
echo ""

# Run built-in validation
echo "1. Running integrity checks..."
python -m src.converter.cli.commands validate

# Check for problems without edges
echo ""
echo "2. Problems without edges:"
duckdb datasets/db/routing.duckdb << 'EOF'
SELECT p.name, p.type, p.dimension
FROM problems p
WHERE NOT EXISTS (SELECT 1 FROM edges e WHERE e.problem_id = p.id)
ORDER BY p.dimension DESC;
EOF

# Check for extreme edge weights (potential errors)
echo ""
echo "3. Problems with very high edge weights (>1000000):"
duckdb datasets/db/routing.duckdb << 'EOF'
SELECT DISTINCT p.name, p.type, MAX(e.weight) as max_weight
FROM problems p
JOIN edges e ON p.id = e.problem_id
GROUP BY p.id, p.name, p.type
HAVING MAX(e.weight) > 1000000;
EOF

# Check nodes without coordinates for coordinate-based problems
echo ""
echo "4. Coordinate problems with missing coordinates:"
duckdb datasets/db/routing.duckdb << 'EOF'
SELECT 
    p.name,
    COUNT(CASE WHEN n.x IS NULL THEN 1 END) as nodes_without_coords
FROM problems p
JOIN nodes n ON p.id = n.problem_id
WHERE p.edge_weight_type = 'EUC_2D'
GROUP BY p.id, p.name
HAVING COUNT(CASE WHEN n.x IS NULL THEN 1 END) > 0;
EOF

echo ""
echo "=== Validation Complete ==="
```

---

## Example 8: Creating Custom Views

**Scenario**: Create reusable views for common queries.

### Create Views

```sql
-- Save to create_views.sql

-- View 1: Problem summary with counts
CREATE OR REPLACE VIEW problem_summary AS
SELECT 
    p.id,
    p.name,
    p.type,
    p.dimension,
    p.edge_weight_type,
    COUNT(DISTINCT n.id) as node_count,
    COUNT(DISTINCT e.id) as edge_count,
    COUNT(DISTINCT CASE WHEN n.is_depot THEN n.id END) as depot_count,
    SUM(n.demand) as total_demand
FROM problems p
LEFT JOIN nodes n ON p.id = n.problem_id
LEFT JOIN edges e ON p.id = e.problem_id
GROUP BY p.id, p.name, p.type, p.dimension, p.edge_weight_type;

-- View 2: Coordinate-based problems only
CREATE OR REPLACE VIEW coord_problems AS
SELECT 
    p.*,
    COUNT(n.id) as coords_count
FROM problems p
JOIN nodes n ON p.id = n.problem_id
WHERE n.x IS NOT NULL
GROUP BY p.id;
```

### Use Views

```bash
# Create views
duckdb datasets/db/routing.duckdb < create_views.sql

# Query views
duckdb datasets/db/routing.duckdb << 'EOF'
SELECT * FROM problem_summary ORDER BY dimension DESC LIMIT 10;
EOF
```

---

## Best Practices from Examples

### 1. Always Validate After Batch Operations

```bash
# After parsing multiple files
python -m src.converter.cli.commands validate
```

### 2. Use Descriptive Output Files

```bash
# Good: descriptive filename
duckdb ... > "tsp_analysis_$(date +%Y%m%d).txt"

# Bad: generic filename
duckdb ... > output.txt
```

### 3. Check Stats Before and After

```bash
# Before
python -m src.converter.cli.commands stats > before_stats.txt

# Parse files...

# After
python -m src.converter.cli.commands stats > after_stats.txt

# Compare
diff before_stats.txt after_stats.txt
```

### 4. Log Important Operations

```bash
# Enable logging
# In config.yaml: log_level: INFO

# Operations will be logged to logs/converter.log
```

### 5. Backup Before Major Changes

```bash
# Backup database
cp datasets/db/routing.duckdb datasets/db/routing_backup_$(date +%Y%m%d).duckdb

# Proceed with operations
```

## See Also

- [User Guide](03-user-guide.md) - General usage information
- [Command Reference](04-command-reference.md) - Detailed command syntax
- [Database Schema](05-database-schema.md) - Schema and advanced queries
