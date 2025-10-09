# Test Coverage Improvement Plan

## Current Status: 63% Coverage ✅

**Target: 75-80% Coverage for Production Readiness**

## Priority 1: Critical Missing Coverage (High Impact) 🔴

### 1. **parallel.py (20% → Target: 70%)**

**Impact: HIGH** - Used in production for batch processing

**Missing Tests:**

- `tests/test_converter/test_parallel.py` (NEW FILE)
  - [ ] `test_parallel_processor_initialization()` - Test worker pool setup
  - [ ] `test_process_batch_parallel()` - Test parallel batch processing
  - [ ] `test_process_batch_sequential_fallback()` - Test fallback when workers=1
  - [ ] `test_parallel_worker_error_handling()` - Test error in worker process
  - [ ] `test_parallel_result_aggregation()` - Test combining results from workers
  - [ ] `test_parallel_with_progress_callback()` - Test progress reporting
  - [ ] `test_parallel_graceful_shutdown()` - Test cleanup on error
  - [ ] `test_parallel_optimal_worker_count()` - Test worker count calculation
  
**Rationale:** Parallel processing is critical for performance. Need comprehensive tests for worker pools, error handling, and edge cases.

### 2. **parser.py (52% → Target: 75%)**

**Impact: HIGH** - Core parsing logic

**Missing Tests:**

- `tests/test_format/test_parser_edge_cases.py` (NEW FILE)
  - [ ] `test_parse_malformed_header()` - Test invalid TSPLIB headers
  - [ ] `test_parse_missing_required_fields()` - Test missing TYPE or DIMENSION
  - [ ] `test_parse_invalid_edge_weight_format()` - Test unsupported formats
  - [ ] `test_parse_incomplete_node_data()` - Test truncated node sections
  - [ ] `test_parse_invalid_tour_data()` - Test malformed TOUR sections
  - [ ] `test_parse_mixed_line_endings()` - Test Windows/Unix line endings
  - [ ] `test_parse_unicode_in_comments()` - Test non-ASCII characters
  - [ ] `test_parse_very_large_file()` - Test performance with large files
  - [ ] `test_parse_empty_file()` - Test empty file handling
  - [ ] `test_parse_file_without_eof()` - Test missing EOF marker
  
**Rationale:** Parser is the entry point - robust error handling is critical.

### 3. **exceptions.py (35% → Target: 60%)**

**Impact: MEDIUM** - Error handling coverage

**Missing Tests:**

- Add to existing test files:
  - [ ] `test_custom_exception_messages()` - Test error message formatting
  - [ ] `test_exception_chaining()` - Test exception wrapping
  - [ ] `test_exception_with_context()` - Test exceptions with additional context
  - [ ] `test_validation_error_details()` - Test validation error specifics
  
**Rationale:** Better error messages help debugging. Test exception paths.

## Priority 2: Medium Impact Improvements ⚠️

### 4. **format/models.py (70% → Target: 85%)**

**Impact: MEDIUM** - Data model validation

**Missing Tests:**

- `tests/test_format/test_models_validation.py` (NEW FILE)
  - [ ] `test_problem_model_validation()` - Test Problem model constraints
  - [ ] `test_node_model_validation()` - Test Node model constraints
  - [ ] `test_edge_model_validation()` - Test Edge model constraints
  - [ ] `test_model_field_types()` - Test field type enforcement
  - [ ] `test_model_optional_fields()` - Test optional vs required fields
  - [ ] `test_model_json_serialization()` - Test JSON export
  - [ ] `test_model_json_deserialization()` - Test JSON import
  
**Rationale:** Ensure data models enforce constraints correctly.

### 5. **format/extraction.py (60% → Target: 75%)**

**Impact: MEDIUM** - Field extraction logic

**Missing Tests:**

- Add to `tests/test_format/test_extraction.py`:
  - [ ] `test_extract_with_multiple_edge_formats()` - Test various edge formats
  - [ ] `test_extract_depot_information()` - Test depot extraction (VRP)
  - [ ] `test_extract_capacity_constraints()` - Test capacity fields
  - [ ] `test_extract_time_windows()` - Test time window data
  - [ ] `test_extract_with_missing_optional_fields()` - Test optional field handling
  
**Rationale:** Better coverage of TSPLIB format variations.

### 6. **api.py (44% → Target: 60%)**

**Impact: LOW** - Appears to be legacy/deprecated

**Decision Needed:**

- [ ] Confirm if `api.py` is still used in production
- [ ] If YES: Add comprehensive tests
- [ ] If NO: Mark as deprecated and exclude from coverage requirements

**Tests if keeping:**

- `tests/test_converter/test_api_legacy.py` (NEW FILE)
  - [ ] Test all public API functions
  - [ ] Test backward compatibility
  
**Rationale:** Don't waste effort on deprecated code.

## Priority 3: Low Priority (Optional) ℹ️

### 7. **Unused Modules (0% coverage)**

- `config.py` - Configuration management (unused)
- `validation.py` - Validation utilities (unused)
- `__main__.py` - Entry point (unused)

**Action:** These are unused. Either:

- [ ] Remove from codebase (if truly unused)
- [ ] Document why they exist (future use)
- [ ] Exclude from coverage requirements

## Implementation Strategy

### Phase 1: Critical Parallel Processing (Week 1)

1. Create `test_parallel.py` with 8 comprehensive tests
2. Target: Bring parallel.py to 70%+ coverage
3. **Estimated Effort:** 4-6 hours

### Phase 2: Parser Edge Cases (Week 1-2)

1. Create `test_parser_edge_cases.py` with 10 edge case tests
2. Target: Bring parser.py to 75%+ coverage
3. **Estimated Effort:** 6-8 hours

### Phase 3: Exception Coverage (Week 2)

1. Add exception path tests to existing files
2. Target: Bring exceptions.py to 60%+ coverage
3. **Estimated Effort:** 2-3 hours

### Phase 4: Model & Extraction (Week 3)

1. Create model validation tests
2. Expand extraction tests
3. Target: 85% models, 75% extraction
4. **Estimated Effort:** 4-5 hours

### Phase 5: Cleanup & Documentation (Week 3)

1. Decide on api.py fate
2. Remove/document unused modules
3. Update coverage documentation
4. **Estimated Effort:** 2-3 hours

## Expected Outcomes

**After Phase 1-2 (Critical):**

- Coverage: ~68-70%
- Parallel processing fully tested
- Parser robustness verified

**After Phase 3-4 (Medium):**

- Coverage: ~75-78%
- Data models validated
- Error handling comprehensive

**After Phase 5 (Cleanup):**

- Coverage: ~75-80% (realistic target)
- Codebase cleaned
- Documentation complete

## Success Metrics

- ✅ Coverage > 75% overall
- ✅ All critical modules > 80%
- ✅ All production code paths tested
- ✅ Zero critical bugs from untested code
- ✅ CI/CD pipeline stable

## Test File Summary (Proposed)

**NEW Test Files to Create:**

1. `tests/test_converter/test_parallel.py` - 8 tests
2. `tests/test_format/test_parser_edge_cases.py` - 10 tests
3. `tests/test_format/test_models_validation.py` - 7 tests

**Files to Expand:**
4. `tests/test_format/test_extraction.py` - Add 5 tests
5. `tests/test_converter/test_database.py` - Add exception tests

**Total New Tests:** ~30 tests
**Final Test Count:** ~164 tests (from current 134)

## Notes

- Focus on **quality over quantity** - test real edge cases
- Use **verify-first methodology** - test actual behavior
- Prioritize **production code paths** over unused utilities
- Document **why certain code is excluded** from coverage
