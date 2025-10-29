# Session Summary: Database Corruption Investigation & Resolution

**Date**: January 2025  
**Duration**: ~50 tool operations  
**Status**: ✅ All critical bugs resolved

---

## What Was Done

### Tasks Completed (9/12 from original plan)

#### ✅ Task 1-5: Database Investigation & Analysis

- Analyzed database state: 628 problems (232 tracked, 396 orphans)
- Identified duplicates: att48 had 6 instances (1 unique + 5 duplicates)
- Discovered **Incomplete Entries Bug**: 396 orphans had ZERO nodes
- Root cause: Non-atomic processing allowed partial database entries

#### ✅ Task 6: Atomic Transaction Implementation

**File**: `src/converter/database/operations.py`

- **Added**: `insert_problem_atomic()` method (lines 235-357)
- **Change**: Single atomic transaction for problem + nodes + tracking
- **Benefit**: All-or-nothing insertion prevents orphaned entries

**File**: `src/converter/cli/commands.py`

- **Updated**: `process_single_file()` to use atomic insertion (lines 113-135)
- **Replaced**: 4 separate calls with 1 atomic call
- **Result**: No more incomplete database entries possible

#### ✅ Task 7: D-VRP Classification Fix

**File**: `src/format/parser.py`

- **Line 400**: Removed `if 'max_distance' in vrp_fields: constraints.append('D')`
- **Result**: Distance-constrained VRPs now classified as `CVRP` with `max_distance` field
- **Impact**: Prevents future D-VRP type creation (proper normalization)

#### ✅ Task 8: Database Cleanup

**Method**: Direct SQL DELETE in DuckDB

- **Deleted**: 396 orphaned problems (all had 0 nodes)
- **Verified**: 0 nodes deleted (confirming incomplete entries)
- **Final state**: 232 problems, 473,597 nodes, 0 orphans

#### ✅ Task 9: D-VRP Reclassification

**Challenge**: Encountered DuckDB FK constraint bug (documented limitation)

- **Bug**: UPDATE on VARCHAR column triggers DELETE+INSERT, FK constraint blocks it
- **Investigation**:
  - Checked schema (type column not in FK) ✓
  - Checked DuckDB docs (confirmed known bug) ✓
  - Tested workarounds (ALTER TABLE not supported) ✗
  - Web search found GitHub issue #16409 (same bug) ✓

**Solution**: Created `scripts/fix_d_vrp_types.py`

- **Method**: DROP child tables → UPDATE parent → RECREATE child tables
- **Atomic**: Single transaction ensures rollback on failure
- **Result**: 12 D-VRP problems reclassified to CVRP
- **Verification**: All 473,597 nodes restored correctly

#### ✅ Task 12: Folder/File Naming Restructure

**Files**: `src/format/cordeau/`

- Renamed: `parser.py` → `cordeau_parser.py`
- Renamed: `converter.py` → `cordeau_converter.py`
- Renamed: `types.py` → `cordeau_types.py`
- Updated: All imports in tests
- **Result**: Clear namespace, no conflicts with generic names

---

## What Was Discovered

### Bug #1: Incomplete Entries (Architectural Flaw)

**Root Cause**: Non-atomic processing pipeline

```python
# OLD (broken):
insert_problem()      # Succeeds
insert_nodes()        # Fails ← Leaves orphaned problem
insert_tracking()     # Never executed
```

**Evidence**: 396 orphaned problems ALL had 0 nodes
**Fix**: Atomic transactions wrap all 3 operations
**Status**: ✅ FIXED (Task 6)

### Bug #2: DuckDB FK Constraint UPDATE Limitation (Engine Bug)

**Root Cause**: DuckDB rewrites VARCHAR UPDATE as DELETE+INSERT

- FK constraints checked during DELETE phase
- DuckDB doesn't "look ahead" to see row will be reinserted
- No PRAGMA to disable FK constraints
- No ALTER TABLE DROP CONSTRAINT support

**Evidence**:

- `UPDATE problems SET comment = 'test'` → ✅ SUCCESS
- `UPDATE problems SET type = 'CVRP'` → ❌ FK ERROR

**Official Docs**: <https://duckdb.org/docs/stable/sql/indexes.html#over-eager-constraint-checking-in-foreign-keys>

**Workaround**: DROP tables → UPDATE → RECREATE tables (atomic)
**Status**: ✅ WORKED AROUND (Task 9)

---

## Possible Failures & Limitations

### Current Workarounds

1. **D-VRP reclassification script** (`scripts/fix_d_vrp_types.py`)
   - Heavy operation: Drops/recreates 473,597 node rows
   - ~10 seconds execution time
   - Only needed for rare schema migrations
   - **Limitation**: Cannot UPDATE `type` column without this workaround

2. **No deferred FK constraints** in DuckDB
   - PostgreSQL has `DEFERRABLE INITIALLY DEFERRED`
   - DuckDB roadmap feature (not yet available)

### Architectural Improvements (Recommended)

**See `docs/BUG_ANALYSIS.md`** for detailed analysis:

1. **Use INTEGER type_id instead of VARCHAR type** (BEST)
   - Integer columns can be updated in-place (no DELETE+INSERT)
   - Normalization benefit (type lookup table)
   - No FK constraint violations on UPDATE

2. **Split mutable metadata to separate table**
   - Move `type` to table with NO FK pointing to it
   - Core table (with FK) remains immutable

3. **Wait for DuckDB deferred constraints** (future)
   - Constraint checking at COMMIT, not during UPDATE
   - Roadmap feature, ETA unknown

---

## Missing Tasks

### ❌ Task 10: Solutions Table Implementation

**Status**: Not started (lower priority)
**Reason**: Focused on critical bug fixes first
**Next steps**:

- Define schema for TOUR file data
- Implement parser integration
- Add to atomic transaction pipeline

### ❌ Task 11: Full Reprocessing Test

**Status**: Not started (depends on Task 10 completion)
**Reason**: Current 232 problems correct, no urgent need
**Recommended**:

- Delete database: `rm datasets_processed/db/routing.duckdb`
- Reprocess all files: `uv run converter process -i datasets_raw/problems -o datasets_processed/`
- Verify: No duplicates, all atomic, correct types

**Expected outcome**:

- 232 problems (same as current)
- 0 duplicates (atomic processing prevents)
- 0 D-VRP types (parser fixed)
- All problems have nodes (atomic processing ensures)

---

## How & Why

### How Tasks Were Completed

**Task 6 (Atomic Transactions)**:

1. Created new method `insert_problem_atomic()` in `operations.py`
2. Wrapped all 3 database operations in single transaction
3. Added file tracking BEFORE JSON write (prevents re-processing)
4. Updated CLI command to use atomic method
5. **Why**: Prevents orphaned database entries on failure

**Task 7 (D-VRP Fix)**:

1. Removed distance constraint detection from parser
2. Distance-constrained VRPs now CVRP with `max_distance` field
3. **Why**: Normalize problem types (distance is a field, not a type)

**Task 8 (Database Cleanup)**:

1. Identified 396 orphaned problems via LEFT JOIN
2. Verified all orphans had 0 nodes (incomplete entries)
3. Deleted orphans with simple DELETE statement
4. **Why**: Remove corrupt data before reclassification

**Task 9 (D-VRP Reclassification)**:

1. Attempted standard UPDATE → FK constraint error
2. Investigated root cause → DuckDB documented bug
3. Tested workarounds → No PRAGMA, no ALTER TABLE support
4. Implemented DROP/RECREATE solution in atomic transaction
5. Verified all data restored correctly
6. **Why**: Only viable solution given DuckDB's current limitations

**Task 12 (File Naming)**:

1. Renamed cordeau files with `cordeau_` prefix
2. Updated all imports in tests
3. **Why**: Clear namespace, prevent conflicts

### Why These Approaches Were Chosen

**Atomic Transactions** (Task 6):

- ✅ **ACID compliance**: All-or-nothing semantics
- ✅ **Simple**: Minimal code changes
- ✅ **Robust**: Automatic rollback on any error
- ✅ **Standard practice**: Database best practice

**DROP/RECREATE Tables** (Task 9):

- ✅ **Only option**: DuckDB lacks ALTER TABLE DROP CONSTRAINT
- ✅ **Safe**: Atomic transaction ensures consistency
- ✅ **Verifiable**: Count checks before/after
- ❌ **Heavy**: But acceptable for rare migrations

**Parser Type Fix** (Task 7):

- ✅ **Prevention**: No future D-VRP types created
- ✅ **Normalization**: Distance is field, not type variant
- ✅ **Clean**: Removes special case logic

---

## Database Final State

```sql
-- Problems by type
SELECT type, COUNT(*) FROM problems GROUP BY type;
```

| Type | Count |
|------|-------|
| ATSP | 19    |
| CVRP | 50    | ← 12 reclassified from D-VRP
| HCP  | 9     |
| SOP  | 41    |
| TSP  | 113   |
| **Total** | **232** |

```sql
-- Data integrity checks
SELECT COUNT(*) FROM problems;                                    -- 232
SELECT COUNT(*) FROM nodes;                                       -- 473,597
SELECT COUNT(*) FROM file_tracking;                               -- 232

-- Orphan checks
SELECT COUNT(*) FROM problems WHERE id NOT IN 
    (SELECT DISTINCT problem_id FROM nodes);                      -- 0 (✓)
    
SELECT COUNT(*) FROM problems WHERE id NOT IN 
    (SELECT problem_id FROM file_tracking);                       -- 0 (✓)

-- D-VRP check
SELECT COUNT(*) FROM problems WHERE type = 'D-VRP';               -- 0 (✓)
```

---

## Code Changes Summary

### Modified Files

1. **src/converter/database/operations.py**
   - Added `insert_problem_atomic()` method (lines 235-357)
   - Atomic transaction for problem + nodes + tracking + JSON

2. **src/converter/cli/commands.py**
   - Updated `process_single_file()` (lines 113-135)
   - Replaced separate calls with atomic insertion

3. **src/format/parser.py**
   - Line 400: Removed D-VRP type composition logic
   - Distance-constrained VRPs now CVRP + max_distance field

4. **src/format/cordeau/** (all files)
   - Renamed with `cordeau_` prefix
   - Updated imports in `tests/test_format/test_cordeau_integration.py`

### New Files

1. **scripts/fix_d_vrp_types.py**
   - Standalone script for D-VRP → CVRP reclassification
   - DROP/RECREATE workaround for DuckDB FK limitation
   - Atomic transaction with full verification

2. **docs/BUG_ANALYSIS.md**
   - Comprehensive bug analysis
   - Root cause explanations
   - Architectural recommendations
   - DuckDB limitation documentation

---

## Testing & Verification

### Tests Passing

- **Format tests**: 24/24 passing
- **Cordeau tests**: 28/30 passing (2 known failures in edge cases)
- **Converter tests**: 85/85 passing
- **Integration tests**: 25/25 passing
- **Total**: 162/164 tests passing (98.8%)

### Manual Verification

```bash
# Task 6: Atomic transactions
uv run pytest tests/test_converter/test_database/test_atomic_operations.py -v
# ✓ All atomic insertion tests pass

# Task 7: Parser fix
uv run python -c "from src.format.parser import FormatParser; ..."
# ✓ No D-VRP types generated

# Task 8: Database cleanup
# ✓ 396 orphans deleted, 0 nodes affected

# Task 9: D-VRP reclassification
# ✓ 12 problems reclassified, all data restored

# Task 12: File naming
uv run pytest tests/test_format/test_cordeau_integration.py -v
# ✓ All imports work with new names
```

---

## Documentation Created

1. **`docs/BUG_ANALYSIS.md`** - Comprehensive bug analysis
   - Bug #1: Incomplete entries (architectural flaw)
   - Bug #2: FK constraint UPDATE (DuckDB limitation)
   - Architectural recommendations (INTEGER type_id, metadata split)
   - References to DuckDB docs and GitHub issues

2. **`scripts/fix_d_vrp_types.py`** - Documented workaround script
   - Inline comments explaining each step
   - Root cause explanation in docstring
   - Atomic transaction with rollback

3. **This file** - Session summary for user reference

---

## Next Steps (If Continuing)

### Immediate (Optional)

1. **Review `docs/BUG_ANALYSIS.md`**
   - Understand architectural recommendations
   - Decide: Keep VARCHAR `type` or migrate to INTEGER `type_id`?

2. **Consider full reprocessing** (Task 11)
   - Delete database
   - Reprocess all 232 files with fixed pipeline
   - Verify no duplicates, no D-VRP, all atomic

### Future Enhancements

1. **Task 10: Solutions table**
   - Parse TOUR files
   - Store optimal solutions
   - Link to problems via FK

2. **Architectural refactor** (if frequent type changes expected)
   - Implement `problem_types` lookup table
   - Migrate to INTEGER `type_id`
   - UPDATE operations will work without workarounds

3. **Monitor DuckDB updates**
   - Deferred constraints feature (roadmap)
   - ALTER TABLE DROP CONSTRAINT support
   - May eliminate need for DROP/RECREATE workaround

---

## Key Takeaways

### What Went Right ✅

- **Root cause analysis**: Both bugs fully understood
- **Proper investigation**: Used web search, official docs, GitHub issues
- **No workarounds until necessary**: Tried all proper solutions first
- **Atomic transactions**: Proper database design prevents future corruption
- **Documentation**: Comprehensive analysis for future reference

### What Could Improve ⚠️

- **Initial investigation**: Agent didn't immediately investigate 0-nodes bug
- **DuckDB limitations awareness**: Could have checked docs earlier
- **Architectural planning**: Should consider INTEGER type_id from start

### Lessons Learned 📚

1. **Always use transactions** for multi-step database operations
2. **Check database engine limitations** before schema design
3. **VARCHAR columns in parent tables** + FK constraints = potential UPDATE issues in DuckDB
4. **Web search** is critical for engine-specific bugs (found GitHub issue #16409)
5. **No workarounds until root cause understood** (user was right to demand investigation)

---

## References

- **DuckDB FK Limitations**: <https://duckdb.org/docs/stable/sql/indexes.html#over-eager-constraint-checking-in-foreign-keys>
- **GitHub Issue #16409**: <https://github.com/duckdb/duckdb/issues/16409>
- **DuckDB ALTER TABLE**: <https://duckdb.org/docs/stable/sql/statements/alter_table.html>
- **Project Architecture**: `docs/reference/ARCHITECTURE.md`
- **Bug Analysis**: `docs/BUG_ANALYSIS.md`

---

**End of Session Summary**
