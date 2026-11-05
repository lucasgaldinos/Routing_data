---
# --- Antigravity rule keys ---
trigger: glob
globs: "tests/**/*.py"
description: "Use when writing, refactoring, reviewing, or splitting tests in routing_data: package-mirrored layout, one responsibility per file, behavior-first assertions, fixture reuse, filename-encoded levels, and dataset isolation." # shared with VS Code
# --- VS Code instruction keys ---
name: "Testing Standards (routing_data)"
applyTo: "tests/**/*.py"
---

# Testing standards — routing_data

The suite is organized by source package and test level: `tests/tsplib_parser/` for the parser, `tests/converter/` for the transformation pipeline, `tests/e2e/` for the chain that spans both. Layout, marker table and command map live in [tests/README.md](../../tests/README.md); this file holds the non-negotiable rules.

> [!IMPORTANT]
> A test that passes while the behavior is wrong is worse than no test: it turns a defect into a contract. Every rule below exists to prevent that.

## 1. Philosophy: enforce behavior, do not document bugs

- A new test must fail against the pre-fix code and pass after it.
- Never `@pytest.mark.skip` with a comment explaining a known bug. Fix it, or `xfail` it with a live register ID.
- Do not assert that a bug exists (for example accepting `null` coordinates because the parser currently does).

## 2. Assert values, not structure

```python
# BAD: proves a key exists, not that parsing worked
assert "dimension" in problem_data

# GOOD: proves the parsed value
assert problem_data["dimension"] == 52
```

- Assert full values for small collections; assert the property for large ones (sorted equality, sums, invariants).
- Add a failure message when the assertion alone is not self-explanatory.

## 3. Reuse fixtures

- Shared fixtures live in [tests/conftest.py](../../tests/conftest.py); use them before writing setup code.
- Do not re-create a temp directory, DuckDB file or problem fixture that already exists.
- Dataset-backed tests use the `requires_dataset` marker and the conftest fixtures — never a hardcoded `datasets_raw/**` path.

## 4. Layout and naming

- Mirror the source package: `tests/tsplib_parser/`, `tests/converter/`, `tests/e2e/`.
- One responsibility per file: one source module or one pipeline stage. Split when a file starts covering a second module, a second failure mode, or a second stage.
- Name files `test_<level>_<module>[_<concern>].py`, where `<level>` is `unit`, `integration`, `e2e` or `performance`.
- The filename declares the level. Never add a hand-written level marker; never create a parallel `tests/unit/` tree.
- One concern per file; cross-package flows belong in `tests/e2e/`.
- Update `tests/README.md` (tree, counts, slow timings) in the same change that adds or moves tests.

## 5. Banned patterns

- No `print()` in tests; use assertions and, when output matters, `caplog`.
- No hardcoded repository paths; use `pathlib.Path` and fixtures.
- No single-sample coverage for a multi-case function; parametrize.
- No wall-clock assertions.

## 6. Exceptions

```python
with pytest.raises(ValueError, match="Invalid input format"):
    parse_problem("bad-input")
```

Assert type and message. A bare `pytest.raises(ValueError)` hides message regressions.

## 7. Write-time checklist

- [ ] Test all elements, not a sample.
- [ ] Validate values, not only structure.
- [ ] Cover boundaries: minimum, maximum, empty, single element.
- [ ] Cover invalid input and error paths.
- [ ] Docstring states WHAT is tested, WHY it matters, EXPECTED result.
- [ ] Assertions validate the property, with informative messages.
- [ ] Multiple cases via `parametrize` (or Hypothesis for invariants).
- [ ] Fixtures reused; no duplicate setup.

## 8. Parametrize and properties

```python
@pytest.mark.parametrize("filename,expected_dimension", [
    ("gr17.tsp", 17),
    ("berlin52.tsp", 52),
    ("att48.tsp", 48),
])
def test_dimension_matches_header(dataset_problem, filename, expected_dimension):
    assert dataset_problem(filename).dimension == expected_dimension
```

Use Hypothesis (`@given`) when a property must hold for a range of inputs rather than a list of examples.

## 9. Workflow

1. THINK: identify testable functions; list happy, edge and error cases. Use `sequentialthinking` when the module has many branches.
2. CHECK: read this file and `tests/conftest.py`; find an existing fixture before writing setup.
3. CODE: write the test with the AAA structure (arrange, act, assert).
4. CRITIC: re-read the checklist; fix any failing box before running the suite.

## 10. Commands

```bash
.venv/bin/python -m pytest tests/tsplib_parser/test_unit_parser.py -q
.venv/bin/python -m pytest tests -m "not slow and not requires_dataset" -q
.venv/bin/python -m pytest tests/e2e -q
```
