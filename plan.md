# Clean Architecture Refactoring Plan

## 🎯 Objectives

Transform the current codebase into a clean, maintainable, performant ETL system following SOLID principles and modern Python best practices.

### Core Requirements

- ✅ **No wrappers/adapters** - Direct, clean implementations
- ✅ **Type-safe** - Complete type hints, 0 Pylance errors (down from 753)
- ✅ **Performance optimized** - Parallel processing, memory-efficient generators
- ✅ **Clean architecture** - Unidirectional dependencies, clear separation of concerns
- ✅ **Proper naming** - Names reveal intent (format vs converter, not parsing vs core)
- ✅ **DRY principle** - No code duplication, single source of truth
- ✅ **NumPy docstrings** - Complete, professional documentation

---

## 📊 Current Problems Analysis

### 1. Circular Import Chain

```
converter/api.py → parsing/converter.py → converter/utils/exceptions.py
❌ CIRCULAR DEPENDENCY
```

**Root Cause:** TSPLIBParser in `parsing/` imports from `converter/utils`, but `converter/api.py` imports from `parsing/`.

### 2. Naming Issues

- `parsing/` - Too generic, doesn't describe TSPLIB format utilities
- `core.py` - Vague, should be `models.py` (contains StandardProblem model)
- `load()`, `read()`, `parse()` - Confusing trio of similar functions
- `TSPLIBParser` - Misleading, it's a wrapper not a parser
- Duplicate exception names: ParsingError exists in TWO places (name collision)

### 3. Architecture Issues

- Wrapper layers: TSPLIBParser wraps loaders wraps core (unnecessary abstraction)
- Dead code: `src/common/` is empty (deleted), `parsing/exceptions.py` unused by TSPLIBParser
- Workarounds: `__getattr__` lazy loading to avoid circular import
- Missing type hints: 753 Pylance errors throughout codebase

### 4. Performance Gaps

- No parallel processing for multiple files
- No generator support for large datasets (>10k nodes)
- Unclear memory management strategy

---

## 🏗️ Target Architecture

### Clean Structure

```
src/
├── format/                          # TSPLIB format utilities (pure, no external deps)
│   ├── __init__.py                 # Public API exports
│   ├── models.py                   # StandardProblem, Problem classes (renamed from core.py)
│   ├── parser.py                   # Unified parse_tsplib() function (replaces loaders.py)
│   ├── fields.py                   # Field definitions (unchanged)
│   ├── transformers.py             # Data transformers (unchanged)
│   └── exceptions.py               # FormatError, ParseError, ValidationError
│
└── converter/                       # ETL system (depends on format)
    ├── __init__.py                 # Clean exports (no lazy loading)
    ├── api.py                      # Public API: parse_file(), to_json(), to_database()
    ├── exceptions.py               # ConverterError, ExtractionError, TransformError, DatabaseError
    ├── core/
    │   ├── extractor.py            # Direct extraction (replaces TSPLIBParser wrapper)
    │   │   └── extract_nodes()
    │   │   └── extract_edges()
    │   │   └── extract_problem_data()
    │   │   └── extract_tours()
    │   │   └── validate_problem()
    │   │   └── preprocess_vrp_fields()
    │   └── transformer.py          # Data normalization
    ├── database/
    │   └── operations.py           # DuckDB operations
    ├── output/
    │   └── json_writer.py          # JSON output
    └── utils/
        ├── parallel.py             # Parallel file processing
        └── validation.py           # Validation utilities
```

### Dependency Flow (Unidirectional)

```
format/  (pure utility, no external deps)
   ↑
   └── converter/  (application layer, depends on format)
```

**Why unidirectional?**

- `format/` is reusable in other projects without converter
- No circular imports - cleaner, easier to test
- Clear responsibility: format = parse files, converter = ETL logic
- Independent testing: Test format utilities without converter

---

## 🔄 Refactoring Strategy

### Approach: Incremental Function-by-Function

**NOT bulk generation** - We'll:

1. Read complete TSPLIBParser (555 lines) for context
2. Analyze each function individually
3. Reimplement cleanly with type hints
4. Test before moving to next
5. Explain decisions with pros/cons AS WE CODE

**Why incremental?**

- ✅ Validate as we go (catch issues early)
- ✅ Easier to understand (deep dive per function)
- ✅ Lower risk (test each piece)
- ✅ Better explanations (no wall of text at end)

---

## 📋 Implementation Phases

### Phase 1: Foundation & Analysis

1. ✅ Read complete TSPLIBParser (555 lines) for context
2. ✅ Rename `parsing/` → `format/` package
3. ✅ Rename `core.py` → `models.py`
4. ✅ Simplify loaders to single `parse_tsplib()` function

### Phase 2: Exception Hierarchies

5. ✅ Redesign `format/exceptions.py` (FormatError, ParseError, ValidationError)
6. ✅ Redesign `converter/exceptions.py` (ConverterError, ExtractionError, etc.)

### Phase 3: Core Extraction Logic

7. ✅ Move TSPLIBParser → `converter/core/extractor.py`
8. ✅ Add complete type hints with NumPy docstrings
9. ✅ Implement generator auto-detection (>10k nodes)

### Phase 4: Architecture Cleanup

10. ✅ Update `converter/api.py` imports (break circular dependency)
11. ✅ Remove `__getattr__` lazy loading workaround

### Phase 5: Performance Optimization

12. ✅ Implement parallel file processing (`ParallelProcessor`)
13. ✅ Add generator support for large files

### Phase 6: Type Safety & Documentation

14. ✅ Fix all type hints (0 Pylance errors)
15. ✅ Add NumPy docstrings to all public functions

### Phase 7: Testing & Validation

16. ✅ Test import statements (no circular imports)
17. ✅ Test CLI functionality
18. ✅ Test parallel processing
19. ✅ Test generator support
20. ✅ Run complete test suite
21. ✅ Update documentation

---

## 🔑 Key Design Decisions

### 1. **No NumPy/Pandas for ETL**

- **Why**: ETL is I/O bound, not compute bound
- **Trade-off**: Dict-based extraction simpler, no dependency bloat
- **Decision**: Keep stdlib-only approach, let algorithms use NumPy later

### 2. **YAGNI on Strategy Pattern**

- **Why**: Only 2 output formats (DB + JSON) - pattern overhead > benefit
- **Trade-off**: Easy to add later (~20 min) when YAML/XML needed
- **Decision**: Simple functions now, refactor IF requirements grow

### 3. **No Distance Calculations in ETL**

- **Why**: We store coordinates + metadata, algorithms compute on-demand
- **Trade-off**: Don't precompute n² edges, avoid waste
- **Decision**: ETL scope = Extract, Transform, Load (not compute)

### 4. **Generator Auto-Detection at 10k Nodes**

- **Why**: Balance memory efficiency vs complexity
- **Trade-off**: <10k = list (faster batch insert), >10k = generator (memory safe)
- **Decision**: Hybrid approach with auto-detection

### 5. **Parallel Files, Not Chunks**

- **Why**: TSPLIB format is sequential, can't split mid-file
- **Trade-off**: ProcessPoolExecutor for multiple files = 8x speedup
- **Decision**: Parallel file processing with batching

---

## 🎯 Success Criteria

### Code Quality

- ✅ 0 Pylance errors (down from 753)
- ✅ 0 mypy errors
- ✅ 0 circular imports
- ✅ Complete type hints (all functions, all parameters, all returns)
- ✅ NumPy docstrings throughout

### Architecture

- ✅ Unidirectional dependencies (format ← converter)
- ✅ No wrappers/adapters (direct implementations)
- ✅ Clean exception hierarchies (no name collisions)
- ✅ No lazy loading workarounds

### Performance

- ✅ Parallel file processing (8x speedup with 8 workers)
- ✅ Generator support for large files (>10k nodes)
- ✅ Memory-efficient batch processing
- ✅ No O(n²) edge precomputation

### Testing

- ✅ Import works: `import converter; import format`
- ✅ CLI works: `converter --help`
- ✅ Parallel processing works with sample dataset
- ✅ Small files use lists, large files use generators

---

**For complete detailed plan with all phases, see updated Todo List.**
