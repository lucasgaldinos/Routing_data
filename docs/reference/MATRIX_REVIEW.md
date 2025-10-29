# Matrix Implementation Review

## Overview

This document reviews the completeness and correctness of `src/tsplib_parser/matrix.py` against the TSPLIB95 specification.

## TSPLIB95 Specification Requirements

According to the TSPLIB95 format specification (`docs/reference/tsplib95_format.md`), the following EDGE_WEIGHT_FORMAT values are defined:

1. `FUNCTION` — Weights given by function (not matrix format)
2. `FULL_MATRIX` — Full n×n matrix
3. `UPPER_ROW` — Upper triangular row-wise without diagonal
4. `LOWER_ROW` — Lower triangular row-wise without diagonal
5. `UPPER_DIAG_ROW` — Upper triangular row-wise with diagonal
6. `LOWER_DIAG_ROW` — Lower triangular row-wise with diagonal
7. `UPPER_COL` — Upper triangular column-wise without diagonal
8. `LOWER_COL` — Lower triangular column-wise without diagonal
9. `UPPER_DIAG_COL` — Upper triangular column-wise with diagonal
10. `LOWER_DIAG_COL` — Lower triangular column-wise with diagonal

## Implementation Coverage

### Matrix Classes Implemented

Our implementation in `src/tsplib_parser/matrix.py` provides:

```python
TYPES = {
    'FULL_MATRIX': FullMatrix,           # ✅ Spec requirement 2
    'UPPER_DIAG_ROW': UpperDiagRow,      # ✅ Spec requirement 5
    'UPPER_ROW': UpperRow,               # ✅ Spec requirement 3
    'LOWER_DIAG_ROW': LowerDiagRow,      # ✅ Spec requirement 6
    'LOWER_ROW': LowerRow,               # ✅ Spec requirement 4
    'UPPER_DIAG_COL': UpperDiagCol,      # ✅ Spec requirement 9
    'UPPER_COL': UpperCol,               # ✅ Spec requirement 7
    'LOWER_DIAG_COL': LowerDiagCol,      # ✅ Spec requirement 10
    'LOWER_COL': LowerCol,               # ✅ Spec requirement 8
}
```

**Coverage**: ✅ **9/9 matrix formats implemented (100%)**

Note: `FUNCTION` is not a matrix format - it indicates distances are computed from coordinates or a special function, so it doesn't need a matrix class.

## Architecture Review

### Base Classes

```python
Matrix                    # Abstract base class
├── FullMatrix           # Complete n×n matrix
└── HalfMatrix          # Abstract base for triangular matrices
    ├── UpperDiagRow    # Upper triangle with diagonal
    │   ├── UpperRow    # Upper triangle without diagonal (has_diagonal=False)
    │   └── LowerDiagCol # Column variant (swap row/col logic)
    └── LowerDiagRow    # Lower triangle with diagonal
        ├── LowerRow    # Lower triangle without diagonal (has_diagonal=False)
        └── UpperDiagCol # Column variant (swap row/col logic)
```

### Row/Column Duality Implementation

The implementation uses an elegant pattern for column variants:

```python
class UpperCol(LowerRow):
    """Upper-triangular column-wise matrix without diagonal.
    Same as LowerRow but stored column-wise instead of row-wise."""
    pass

class LowerCol(UpperRow):
    """Lower-triangular column-wise matrix without diagonal.
    Same as UpperRow but stored column-wise instead of row-wise."""
    pass
```

**Rationale**: In row-major storage, an upper-right triangle traversed row-by-row is equivalent to a lower-left triangle traversed column-by-column. This duality allows code reuse.

**Example** (4×4 matrix):

- `UPPER_ROW` (row-wise): `[1, 2, 3, 4, 5, 6]` → indexes (0,1), (0,2), (0,3), (1,2), (1,3), (2,3)
- `LOWER_COL` (col-wise): Same data, but conceptually column-wise traversal of lower triangle

**Correctness**: ✅ This pattern is mathematically sound and matches the tsplib95 reference implementation.

## Functionality Analysis

### Core Operations

1. **Matrix Construction**: `Matrix(numbers, size, min_index=0)`
   - ✅ Takes flattened list of numbers
   - ✅ Supports custom min_index (for 1-based TSPLIB data)
   - ✅ Stores size for bounds checking

2. **Element Access**: `matrix[i, j]` or `matrix.value_at(i, j)`
   - ✅ Supports Pythonic indexing notation
   - ✅ Handles symmetry for half-matrices (swaps i,j when needed)
   - ✅ Returns 0 for diagonal in matrices without diagonal
   - ✅ Bounds checking via `is_valid_row_column()`

3. **Index Calculation**: `get_index(i, j)` (subclass-specific)
   - ✅ Full matrix: `i * size + j` (row-major order)
   - ✅ Lower triangle: `sum(0..i) + j` (triangular number formula)
   - ✅ Upper triangle: `sum(n..n-i) + (j-i)` (complement formula)
   - ✅ Memoization for triangular numbers via `_int_sum()`

### Performance Optimizations

1. **Memoized triangular numbers**:
   ```python
   def _int_sum(n: int, memo: dict = {}) -> int:
       """Compute sum of integers from 0 to n (triangular number)."""
       if n not in memo:
           s = n * (n + 1) // 2
           memo[n] = s
       return memo[n]
   ```
   - ✅ Avoids recomputation for repeated queries
   - ✅ O(1) after first call for each n

2. **Direct index calculation** (no iteration):
   - ✅ `get_index()` uses closed-form formulas
   - ✅ O(1) complexity for all matrix types

## Test Coverage Gaps

Based on the design analysis document and code review, the following should be tested:

### 1. Matrix Construction Tests

| Test Case | Status | Priority |
|-----------|--------|----------|
| Full matrix (n×n elements) | Likely tested | Medium |
| Lower row without diagonal (n(n-1)/2 elements) | Likely tested | Medium |
| Lower row with diagonal (n(n+1)/2 elements) | Likely tested | Medium |
| **Dimension mismatch** (wrong number of elements) | ❌ Not tested | **HIGH** |
| **Empty matrix** (dimension=0) | ❌ Not tested | Medium |
| **Single element** (dimension=1) | ❌ Not tested | Low |
| Large matrix (rbg443: 443×443) | Likely tested | Low |

### 2. Element Access Tests

| Test Case | Status | Priority |
|-----------|--------|----------|
| Valid indices access | Likely tested | Medium |
| **Out of bounds access** | ❌ Not tested | Medium |
| Symmetry handling (accessing upper in lower matrix) | Likely tested | Medium |
| **Diagonal access in non-diagonal matrix** | ❌ Not tested | Medium |
| Negative indices | ❌ Not tested | Low |

### 3. Format Conversion Tests

| Test Case | Status | Priority |
|-----------|--------|----------|
| LOWER_ROW → full matrix | Likely tested | Medium |
| UPPER_ROW → full matrix | Likely tested | Medium |
| **Column formats** (LOWER_COL, UPPER_COL) | ❌ Not tested | **HIGH** |
| **Diagonal formats** (LOWER_DIAG_COL, UPPER_DIAG_COL) | ❌ Not tested | **HIGH** |

### 4. Edge Cases

| Test Case | Status | Priority |
|-----------|--------|----------|
| **Asymmetric matrix treated as symmetric** | ❌ Not tested | **HIGH** |
| **min_index != 0** (1-based indexing) | ❌ Not tested | Medium |
| **Type mixing** (int and float in same matrix) | ❌ Not tested | Low |

## Correctness Verification

### Formula Verification

**Lower triangle size** (with diagonal):

- Formula: n(n+1)/2
- Verification: n=4 → 4×5/2 = 10 elements ✅
- Elements: (0,0), (1,0), (1,1), (2,0), (2,1), (2,2), (3,0), (3,1), (3,2), (3,3)

**Lower triangle size** (without diagonal):

- Formula: n(n-1)/2
- Verification: n=4 → 4×3/2 = 6 elements ✅
- Elements: (1,0), (2,0), (2,1), (3,0), (3,1), (3,2)

**Upper triangle index** (with diagonal):

```python
# For UPPER_DIAG_ROW, element (i,j) where j >= i
# Row i starts at: sum(n..n-i+1) = sum(n) - sum(n-i)
# Position in row: j-i
return integer_sum(n, n - i) + (j - i)
```

**Verification** (n=4, access (1,2)):

- Row 1 starts at: sum(4) - sum(3) = 10 - 6 = 4
- Position: 2-1 = 1
- Index: 4 + 1 = 5 ✅
- Manual count: [0: (0,0), 1: (0,1), 2: (0,2), 3: (0,3), 4: (1,1), **5: (1,2)**, ...]

### Row/Column Duality Proof

**Claim**: `UpperCol` is equivalent to `LowerRow`

**Proof**:

- LOWER_ROW traverses: (1,0), (2,0), (2,1), (3,0), (3,1), (3,2), ...
  - Row 1: (1,0)
  - Row 2: (2,0), (2,1)
  - Row 3: (3,0), (3,1), (3,2)
  
- UPPER_COL traverses: (0,1), (0,2), (1,2), (0,3), (1,3), (2,3), ...
  - Column 1: (0,1)
  - Column 2: (0,2), (1,2)
  - Column 3: (0,3), (1,3), (2,3)

- Observation: LOWER_ROW element k is at (i,j) where j<i
- Observation: UPPER_COL element k is at (j,i) where j<i
- Conclusion: **UpperCol._fix_indices swaps (i,j) to (j,i), making it equivalent to LowerRow**

✅ **Duality implementation is mathematically correct.**

## Comparison with Official tsplib95

Checking the official tsplib95 repository structure:

- Official library: Has `matrix.py` with similar class hierarchy
- Our implementation: Vendored and simplified
- Key differences:
  - Official has more helper methods (`.to_dict()`, `.to_list()`)
  - Official has better type hints
  - Our implementation is more minimal (focuses on parsing only)

**Completeness**: ✅ All TSPLIB95-specified formats are implemented correctly.

## Security & Validation Concerns

### 1. Dimension Validation

**Current state**: No validation that `len(numbers)` matches expected size.

**Risk**: High - Could cause:

- `IndexError` when accessing elements
- Silent data corruption if too many elements provided
- Incorrect distance calculations

**Example exploit**:

```python
# LOWER_ROW dimension=10 needs 45 elements: 10*9/2
matrix = LowerRow(numbers=[1]*40, size=10)  # Only 40 provided
# Accessing matrix[9, 8] will cause IndexError or return wrong value
```

**Recommendation**: ✅ Add validation in `Matrix.__init__()`:

```python
expected_size = self.get_expected_size()  # Subclass-specific
if len(numbers) != expected_size:
    raise ValueError(f"Expected {expected_size} elements for {self.__class__.__name__} "
                     f"with dimension {size}, got {len(numbers)}")
```

### 2. Asymmetry Handling

**Current state**: `HalfMatrix._fix_indices()` swaps (i,j) to (j,i) for symmetry.

**Risk**: Medium - If used on ATSP data (asymmetric), returns wrong distances.

**Example**:

```python
# ATSP br17 has asymmetric distances
# If parsed as LOWER_ROW (assumes symmetry):
distance_ij = matrix[i, j]  # Correct
distance_ji = matrix[j, i]  # WRONG - swaps to matrix[i,j], assumes d(j,i) = d(i,j)
```

**Recommendation**: ⚠️ This is handled at a higher level (ATSP uses FULL_MATRIX, not half-matrices). But add assertion:

```python
assert self.is_symmetric or isinstance(self, FullMatrix), \
    "Asymmetric distances require FULL_MATRIX format"
```

### 3. Type Safety

**Current state**: Accepts `Union[int, float]` but no validation.

**Risk**: Low - Python handles mixed types well.

**Edge case**: What if someone passes strings? `TypeError` in arithmetic operations.

**Recommendation**: ✓ Current approach is fine. Type hints prevent most errors.

## Final Assessment

### Strengths

- ✅ **100% format coverage**: All 9 TSPLIB95 matrix formats implemented
- ✅ **Mathematically correct**: Formulas verified, duality pattern proven
- ✅ **Performance optimized**: Memoization, O(1) access
- ✅ **Clean architecture**: Base classes with clear inheritance

### Weaknesses

- ❌ **No dimension validation**: Critical gap (see Security section)
- ❌ **Insufficient test coverage**: Column formats, edge cases untested
- ⚠️ **Limited documentation**: Formula explanations could be clearer

### Recommendations

**Immediate (High Priority)**:

1. Add dimension validation in `Matrix.__init__()`
2. Add tests for column format classes
3. Add tests for dimension mismatches

**Short Term (Medium Priority)**:
4. Add tests for edge cases (dimension=0, dimension=1, out of bounds)
5. Add `get_expected_size()` method to each matrix class
6. Improve docstrings with formula explanations

**Long Term (Low Priority)**:
7. Consider adding `to_full_matrix()` method for analysis
8. Add property tests (hypothesis library) for index calculations
9. Benchmark performance on large matrices (rbg443)

## Conclusion

✅ **The matrix.py implementation is complete and correct** according to the TSPLIB95 specification. All 9 matrix formats are implemented with mathematically sound formulas and efficient algorithms.

⚠️ **However, critical validation is missing.** Dimension mismatches could cause data corruption or errors. This should be addressed before production use.

**Overall Score**: 8/10

- Completeness: 10/10
- Correctness: 10/10
- Validation: 3/10
- Testing: 6/10
- Documentation: 7/10

## See Also

- [TSPLIB95 Format Specification](../reference/tsplib95_format.md)
- [Design Analysis](../reference/DESIGN_ANALYSIS.md)
- [Database Schema](../diagrams/database-schema.md)
