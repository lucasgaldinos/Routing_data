# Revised Comprehensive Test Plan - Quality-Focused

## 🎯 Core Principles

1. **Test BEHAVIORS, not implementations** - Validate requirements, not code structure
2. **Independent verification** - Tests must validate correctness independently, not just match current output
3. **Comprehensive coverage** - Multiple problem types, sizes, edge cases
4. **Clear documentation** - Every test explains WHAT, WHY, and EXPECTED outcome
5. **No "made to pass" tests** - If code is wrong, tests MUST fail

---

## 📊 Test File Matrix

### Available Test Files (from datasets_raw/problems/)

**TSP Files (Symmetric):**

- `gr17.tsp` - 17 nodes, EUC_2D (small, basic)
- `att48.tsp` - 48 nodes, ATT distance (small, special metric)
- `att532.tsp` - 532 nodes, ATT distance (medium)
- `berlin52.tsp` - 52 nodes, EUC_2D (small, classic)
- `a280.tsp` - 280 nodes, EUC_2D (medium)
- `brd14051.tsp` - 14051 nodes, EUC_2D (large)

**ATSP Files (Asymmetric):**

- `br17.atsp` - 17 nodes, EXPLICIT matrix (small)
- `ftv33.atsp` - 33 nodes (small)
- `ftv170.atsp` - 170 nodes (medium)
- `p43.atsp` - 43 nodes (small)
- `rbg403.atsp` - 403 nodes (large)

**VRP Files (Vehicle Routing):**

- `eil7.vrp` - 7 nodes (tiny, with demands)
- `eil13.vrp` - 13 nodes (small)
- `eil51.vrp` - 51 nodes (medium)

**HCP Files (Hamiltonian Cycle):**

- `alb1000.hcp` - 1000 nodes
- `alb4000.hcp` - 4000 nodes

**SOP Files (Sequential Ordering):**

- Available in datasets_raw/problems/sop/

---

## 🧪 Revised Test Strategy

### Phase 1: Core Parsing - Diverse File Types

#### 1.1 TSP Parsing Tests

**File:** `tests/test_format/test_parser_tsp.py`

```python
def test_parse_tsp_euclidean_small():
    """
    Parse small symmetric TSP with Euclidean 2D coordinates.
    
    Validates:
    - Correct problem type identification
    - All nodes extracted with (x, y) coordinates
    - Dimension matches node count
    - Symmetry correctly detected
    
    Test file: gr17.tsp
    - Specification: 17 cities, EUC_2D distance
    - Known: Symmetric problem, optimal tour length ~2085
    
    Requirements validated:
    - TSPLIB95 TSP format parsing
    - NODE_COORD_SECTION extraction
    - 2D Euclidean distance calculation
    """

def test_parse_tsp_att_distance():
    """
    Parse TSP with ATT (pseudo-Euclidean) distance metric.
    
    Validates:
    - ATT distance function correctly identified
    - Distance calculation uses ceiling(sqrt(...))
    - Not using standard Euclidean formula
    
    Test file: att48.tsp
    - Specification: 48 cities, ATT distance
    - Known: Different distance metric than EUC_2D
    
    Requirements validated:
    - ATT distance type recognition
    - Special distance function handling
    """

def test_parse_tsp_medium_size():
    """
    Parse medium-sized TSP to verify scalability.
    
    Validates:
    - Handles 500+ nodes efficiently
    - Memory usage reasonable
    - No performance degradation
    
    Test file: att532.tsp
    - Specification: 532 cities
    
    Requirements validated:
    - Scalability to medium problems
    - Performance acceptable (<5 seconds)
    """

def test_parse_tsp_large_file():
    """
    Parse large TSP (10k+ nodes) with memory efficiency check.
    
    Validates:
    - Can handle large files without memory errors
    - Processing time reasonable (<30 seconds)
    - Generator usage for memory efficiency (if applicable)
    
    Test file: brd14051.tsp
    - Specification: 14051 cities
    
    Requirements validated:
    - Large file handling
    - Memory efficiency
    - No out-of-memory errors
    """
```

#### 1.2 ATSP Parsing Tests

**File:** `tests/test_format/test_parser_atsp.py`

```python
def test_parse_atsp_explicit_matrix():
    """
    Parse ATSP with explicit distance matrix.
    
    Validates:
    - Asymmetric problem correctly identified
    - Full distance matrix extracted
    - Matrix dimensions match problem dimension
    - Asymmetry flag set correctly
    
    Test file: br17.atsp
    - Specification: 17 cities, EXPLICIT distances
    - Format: FULL_MATRIX or similar
    
    Requirements validated:
    - ATSP type recognition
    - Distance matrix extraction
    - Asymmetric distance handling
    """

def test_parse_atsp_verify_asymmetry():
    """
    Verify asymmetric distances are NOT symmetrical.
    
    Validates:
    - distance(i, j) != distance(j, i) for some i, j
    - Symmetry check returns False
    - Edge weights stored correctly
    
    Test file: p43.atsp
    
    Requirements validated:
    - Asymmetry detection logic
    - Distance matrix correctness
    """
```

#### 1.3 VRP Parsing Tests

**File:** `tests/test_format/test_parser_vrp.py`

```python
def test_parse_vrp_with_demands():
    """
    Parse VRP with customer demands.
    
    Validates:
    - CVRP/VRP type identified correctly
    - Demand values extracted for each node
    - Depot information preserved
    - Capacity constraints present
    
    Test file: eil13.vrp
    - Specification: 13 nodes with demands
    - Has DEMAND_SECTION
    
    Requirements validated:
    - VRP format parsing
    - DEMAND_SECTION extraction
    - Depot handling
    """

def test_parse_vrp_depot_identification():
    """
    Verify depot node identification.
    
    Validates:
    - Depot node marked correctly
    - Depot has demand = 0 (or not counted)
    - Depot coordinates extracted
    
    Test file: eil7.vrp
    
    Requirements validated:
    - Depot vs customer distinction
    - DEPOT_SECTION parsing
    """
```

---

### Phase 2: Edge Cases & Error Handling

**File:** `tests/test_format/test_parser_errors.py`

```python
def test_parse_missing_dimension():
    """
    File missing required DIMENSION field.
    
    Expected: ParseError raised
    Error message: "Missing required field: DIMENSION"
    
    Validates:
    - Required field validation
    - Clear error messages
    """

def test_parse_malformed_coordinates():
    """
    Invalid coordinate data (non-numeric, incomplete).
    
    Expected: ValidationError raised
    Error message: Describes invalid line/data
    
    Validates:
    - Data format validation
    - Graceful error handling
    """

def test_parse_dimension_mismatch():
    """
    DIMENSION=10 but only 5 nodes provided.
    
    Expected: ValidationError raised
    Error message: "Node count (5) doesn't match DIMENSION (10)"
    
    Validates:
    - Dimension consistency check
    - Data completeness validation
    """

def test_parse_missing_eof():
    """
    File without EOF marker.
    
    Expected: Should still parse successfully OR warn
    
    Validates:
    - Robustness to minor format issues
    - EOF marker handling
    """

def test_parse_unsupported_edge_weight_type():
    """
    EDGE_WEIGHT_TYPE not implemented (e.g., SPECIAL function).
    
    Expected: UnsupportedFeatureError raised
    Error message: "EDGE_WEIGHT_TYPE 'SPECIAL' not supported"
    
    Validates:
    - Feature availability checking
    - Clear unsupported feature messages
    """
```

---

### Phase 3: Data Correctness Validation

**File:** `tests/test_format/test_extraction_correctness.py`

```python
def test_distance_calculation_euclidean():
    """
    Verify Euclidean distance calculation is mathematically correct.
    
    Method:
    1. Parse gr17.tsp
    2. Take nodes 1 and 2
    3. Manually calculate sqrt((x1-x2)^2 + (y1-y2)^2)
    4. Compare with extracted distance
    
    Validates:
    - Distance formula implementation
    - Calculation accuracy
    
    NOT testing: What the current code outputs
    Testing: Mathematical correctness against formula
    """

def test_distance_calculation_att():
    """
    Verify ATT distance uses ceiling(sqrt(...)) formula.
    
    Method:
    1. Parse att48.tsp
    2. Manually calculate ATT distance for known nodes
    3. Formula: ceil(sqrt(((x1-x2)^2 + (y1-y2)^2) / 10.0))
    4. Compare with extracted distance
    
    Validates:
    - ATT distance formula correctness
    - Ceiling function application
    """

def test_node_coordinates_match_file():
    """
    Verify extracted coordinates exactly match file content.
    
    Method:
    1. Read gr17.tsp raw file
    2. Parse NODE_COORD_SECTION manually
    3. Parse with parse_tsplib()
    4. Compare coordinate values exactly
    
    Validates:
    - Data extraction accuracy
    - No data loss or corruption
    """
```

---

### Phase 4: Integration & Performance

**File:** `tests/integration/test_full_pipeline.py`

```python
@pytest.mark.integration
def test_pipeline_tsp_to_json(temp_output_dir):
    """
    Full pipeline: TSP file → parse → transform → JSON output.
    
    Steps:
    1. Parse gr17.tsp
    2. Transform data
    3. Write to JSON
    4. Load JSON and verify structure
    
    Validates:
    - Complete ETL flow works
    - Data preserved through pipeline
    - Output format correct
    """

@pytest.mark.integration  
def test_pipeline_multiple_problem_types(temp_output_dir):
    """
    Process array of different problem types.
    
    Test files:
    - gr17.tsp (TSP)
    - br17.atsp (ATSP)
    - eil13.vrp (VRP)
    
    Validates:
    - Pipeline handles different types
    - No cross-contamination of data
    - All outputs created successfully
    """
```

**File:** `tests/integration/test_performance.py`

```python
@pytest.mark.performance
@pytest.mark.slow
def test_large_file_performance(benchmark):
    """
    Benchmark large file parsing performance.
    
    Test file: brd14051.tsp (14k nodes)
    
    Requirements:
    - Parsing time < 30 seconds
    - Memory usage < 500MB
    - No memory leaks
    
    Validates:
    - Performance meets requirements
    - Memory efficiency
    """

@pytest.mark.performance
def test_parallel_processing_speedup():
    """
    Verify parallel processing is faster than sequential.
    
    Test: Process 10 medium files
    - Sequential: baseline time
    - Parallel (4 workers): should be 2-3x faster
    
    Validates:
    - Parallel processing works
    - Actual performance benefit
    """
```

---

## 📝 Test Documentation Standard

Every test MUST have:

```python
def test_something():
    """
    [ONE LINE SUMMARY]
    
    Validates:
    - [Specific behavior being tested]
    - [Another behavior]
    
    Test data:
    - File: [filename]
    - Specification: [key properties]
    - Known facts: [any known correct values]
    
    Requirements validated:
    - [Requirement ID or description]
    - [TSPLIB95 spec section]
    
    Expected behavior:
    - [What should happen]
    - [Success criteria]
    
    Edge cases covered:
    - [If applicable]
    """
    # Test implementation
```

---

## ✅ Updated Fixtures (conftest.py)

```python
# Multi-file fixtures
@pytest.fixture
def tsp_files_small(test_data_dir):
    """Small TSP test files (< 100 nodes)."""
    return {
        'gr17': test_data_dir / 'tsp' / 'gr17.tsp',
        'att48': test_data_dir / 'tsp' / 'att48.tsp',
        'berlin52': test_data_dir / 'tsp' / 'berlin52.tsp',
    }

@pytest.fixture
def atsp_files(test_data_dir):
    """ATSP test files."""
    return {
        'br17': test_data_dir / 'atsp' / 'br17.atsp',
        'p43': test_data_dir / 'atsp' / 'p43.atsp',
        'ftv170': test_data_dir / 'atsp' / 'ftv170.atsp',
    }

@pytest.fixture
def vrp_files(test_data_dir):
    """VRP test files with demands."""
    return {
        'eil7': test_data_dir / 'vrp' / 'eil7.vrp',
        'eil13': test_data_dir / 'vrp' / 'eil13.vrp',
    }

@pytest.fixture
def malformed_files(tmp_path):
    """Create malformed test files for error testing."""
    files = {}
    
    # Missing DIMENSION
    missing_dim = tmp_path / 'missing_dimension.tsp'
    missing_dim.write_text("""NAME: test
TYPE: TSP
NODE_COORD_SECTION
1 0.0 0.0
EOF
""")
    files['missing_dimension'] = missing_dim
    
    # Dimension mismatch
    dim_mismatch = tmp_path / 'dimension_mismatch.tsp'
    dim_mismatch.write_text("""NAME: test
TYPE: TSP
DIMENSION: 10
NODE_COORD_SECTION
1 0.0 0.0
2 1.0 1.0
EOF
""")
    files['dimension_mismatch'] = dim_mismatch
    
    return files
```

---

## 🎯 Success Criteria

1. ✅ **Comprehensive Coverage:**
   - At least 3 files per problem type (TSP, ATSP, VRP)
   - Small (< 100), medium (100-1000), large (> 1000) sizes
   - All major edge weight types (EUC_2D, ATT, EXPLICIT, GEO)

2. ✅ **Error Handling:**
   - 10+ error test cases
   - All major error scenarios covered
   - Clear, actionable error messages

3. ✅ **Correctness:**
   - Distance calculations verified mathematically
   - Data extraction verified against file content
   - Known solutions validated when available

4. ✅ **Documentation:**
   - Every test has complete docstring
   - What, why, and expected outcome documented
   - Test data properties described

5. ✅ **No "Made to Pass":**
   - Tests validate requirements, not implementations
   - Independent verification of correctness
   - Will fail if code is wrong

6. ✅ **Performance:**
   - Large file tests (> 10k nodes)
   - Parallel processing validated
   - Memory efficiency checked

---

## 🔄 Implementation Order

1. **Setup** - Create comprehensive fixtures
2. **Core parsing** - TSP, ATSP, VRP tests
3. **Error handling** - All error scenarios
4. **Correctness** - Mathematical validation
5. **Integration** - Full pipeline tests
6. **Performance** - Large file & parallel tests
7. **Verification** - Run all, check coverage, fix type errors

This is a **real** test plan, not a checklist to make pass.
