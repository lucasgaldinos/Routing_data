
# VRP Data Format Analysis and Unified Converter Architecture

## Architecture Overview

This project implements a **unified converter architecture** that transforms all VRP data formats into TSPLIB95 standard, enabling the use of a single parsing library while preserving format-specific metadata.

### Key Benefits

- **Single parsing library dependency**: Only `tsplib95` library needed
- **Standardized internal representation**: All problems processed uniformly  
- **Isolated complexity**: Format-specific logic contained in converters
- **Enhanced maintainability**: Easy to add new formats without core changes
- **Preserved semantics**: Original format metadata stored for algorithm compatibility

## Format Categories and Processing Strategy

### 1. **Format Categories and Processing Strategy**

**A. TSPLIB95 Format (.vrp files) - Direct Processing**

- **Format**: Standard TSPLIB95 keyword-based sections
- **Structure**: NAME, TYPE, DIMENSION, NODE_COORD_SECTION, DEMAND_SECTION, etc.
- **Processing**: Direct parsing using `tsplib95` library
- **Examples**: A-VRP, B-VRP, F-VRP, XML100 series
- **Implementation**: Phase 1 (1-2 days)

**B. Solomon/Homberger Format (.txt files) - Converter Required**

- **Format**: Header with vehicle info, then customer data in columns
- **Structure**: Customer tables with coordinates, demands, time windows, and service times
- **Processing**: **Convert to TSPLIB95** → Parse with `tsplib95`
- **Examples**: Solomon instances (25, 50, 100 customers), Homberger instances (200-1000 customers)
- **Implementation**: Phase 2 (3-4 days) - Solomon Converter

**C. Taillard Format (.dat files) - Converter Required**

- **Format**: Space-separated values with specific structure
- **Structure**: Dimension/capacity header, depot coordinates, numbered customer data
- **Processing**: **Transform to TSPLIB95** → Parse with `tsplib95`
- **Examples**: Taillard instances (tai75a, tai100a, tai150a, etc.)
- **Implementation**: Phase 3 (3-4 days) - Taillard Converter

### 2. **Problem Type Classification**

**A. Basic Problems**

- **TSP**: Traveling Salesman Problem
- **CVRP**: Capacitated Vehicle Routing Problem
- **VRP**: Basic Vehicle Routing Problem

**B. Time-Constrained Problems**

- **CVRPTW**: CVRP with Time Windows
- **VRPTW**: VRP with Time Windows

**C. Pickup and Delivery Problems**

- **CVRPPDTW**: CVRP with Pickup and Delivery and Time Windows
- **PDPTW**: Pickup and Delivery Problem with Time Windows

**D. Size Categories**

- Small: 25-100 customers
- Medium: 200-400 customers  
- Large: 600-1000+ customers

### 3. **Existing Parser Analysis**

**A. tsplib95 Library** ✅

- **Supports**: TSP, ATSP, SOP, HCP, CVRP, and 1-PDTSP formats
- **Strengths**: Robust, well-documented, handles TSPLIB95 standard formats
- **Limitations**: Limited to TSPLIB95 format specification
- **Coverage**: Handles .VRP files that follow TSPLIB95 format

**B. Missing Parsers** ❌

- **Solomon/Homberger .TXT format**: No dedicated parser found
- **CVRPPDTW .DAT format**: No dedicated parser found
- **CMT custom format**: No dedicated parser found

### 4. **Parser Implementation Complexity Assessment**

Starting (4/5) *Assess parsing complexity*

**A. TSPLIB95/.VRP Format** - **LOW Complexity** ⭐⭐

- **Existing Solution**: tsplib95 library handles this perfectly
- **Implementation**: Use tsplib95 directly
- **Effort**: Minimal - just integration work

**B. Solomon/Homberger .TXT Format** - **MEDIUM Complexity** ⭐⭐⭐

- **Structure**: Well-defined header + tabular data
- **Parsing Logic**:
  1. Parse vehicle section (number and capacity)
  2. Parse customer table with fixed columns
  3. Handle coordinate, demand, and time window data
- **Estimated Effort**: 2-3 days for robust implementation
- **Key Challenges**: Consistent column parsing, time window format handling

**C. CVRPPDTW .DAT Format** - **MEDIUM Complexity** ⭐⭐⭐

- **Structure**: Space-separated values with specific column meaning
- **Parsing Logic**:
  1. Parse fixed-width columns
  2. Handle pickup/delivery flags
  3. Process multiple time windows
- **Estimated Effort**: 2-3 days
- **Key Challenges**: Understanding pickup/delivery semantics, time window variations

**D. CMT Custom Format** - **LOW-MEDIUM Complexity** ⭐⭐

- **Structure**: Simple space-separated format
- **Parsing Logic**: Basic coordinate and demand parsing
- **Estimated Effort**: 1-2 days
- **Key Challenges**: Format variations between instances

### 5. **Database Indexing Strategy**

Starting (5/5) *Create recommendations*

**A. Core Schema Design**

```sql
-- Problem instances table
problems (
    id, name, problem_type, format_type, dimension, 
    capacity, has_time_windows, has_pickup_delivery,
    file_path, created_at
)

-- Nodes/customers table  
nodes (
    problem_id, node_id, x_coord, y_coord, demand,
    ready_time, due_time, service_time, is_depot
)

-- Vehicles table
vehicles (
    problem_id, vehicle_id, capacity, capacity_vol
)
```

**B. Indexing Strategy**

- **Primary Indices**: problem_type, dimension, format_type
- **Composite Indices**: (problem_type, dimension), (has_time_windows, has_pickup_delivery)
- **Spatial Indices**: (x_coord, y_coord) for geographic queries
- **Performance Indices**: dimension ranges, capacity ranges

## **Recommendations**

### **Implementation Priority**

1. **Phase 1**: Integrate tsplib95 for .VRP files (immediate value)
2. **Phase 2**: Implement Solomon/Homberger parser (high impact)
3. **Phase 3**: Implement CVRPPDTW .DAT parser (specialized needs)
4. **Phase 4**: Handle remaining custom formats

### **Parser Architecture**

```python
class ProblemParser:
    def detect_format(self, file_path) -> str
    def parse(self, file_path) -> ProblemInstance
    def to_database(self, problem: ProblemInstance) -> Dict

class TsplibParser(ProblemParser): # Use tsplib95
class SolomonParser(ProblemParser): # Custom implementation  
class CvrppdtwParser(ProblemParser): # Custom implementation
```

### **Total Development Effort**

- **tsplib95 Integration**: 1-2 days
- **Solomon/Homberger Parser**: 3-4 days  
- **CVRPPDTW Parser**: 3-4 days
- **Database Schema + Integration**: 2-3 days
- **Testing + Validation**: 2-3 days
- **Total**: ~2-3 weeks for comprehensive solution

Completed (5/5) *Create recommendations*

The analysis shows that your data collection contains a rich variety of vehicle routing problems with different complexities. The tsplib95 library provides excellent coverage for TSPLIB95-standard formats, but you'll need custom parsers for Solomon/Homberger and CVRPPDTW formats. The total implementation effort is moderate (2-3 weeks) and highly feasible, with the database indexing strategy supporting efficient querying across multiple problem characteristics.
