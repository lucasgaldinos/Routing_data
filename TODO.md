# TODO

_Active implementation plan - routing_data parser hardening (tsplib_parser) + ETL visibility._

> Registered 2026-09-09 from the stepwise Q&A. Execution follows the `stepwise-explain-and-fix`
> protocol: one change at a time -> business-rule-first ELI5 -> askQuestions gate -> verify ->
> pause -> summary. Mermaid README (Task 5.2) is deliberately the LAST task.

## Current status

- [x] Review complete: 239-file corpus parses cleanly; `test_unit_parser_validation.py` = 100% green.
- [x] Batch 1 - `models.py` micro-cleanups (1.1 - 1.6 completed)
- [x] Batch 2 - `StandardProblem.parse` structural simplification & decomposition into `tokenization.py`, `fields.py`, `transformers.py`
- [x] Batch 3 - ETL failure visibility (converter / CLI) — B1/B3 fixed 2026-11-03
- [ ] Batch 4 - naming collision (`DataTransformer` -> `ProblemNormalizer`) — re-opened 2026-11-04 to remove `DataTransformer` alias and migrate all 20 test files + 6 doc files
- [x] Batch 5 - docs: `src/tsplib_parser/README.md` with mermaid diagrams, updated TODOs, test layout conventions
- [x] Batch 6 - parser payload typing (`ParseResult` / `ProblemData` / `Metadata`) + Cordeau payload bridge (2026-10-23)
- [ ] Batch 7 - post-`v0.2.0` deep review fixes: `GEO` degree truncation, corpus-independence (`C1`–`C3`), `inspect_parse_result.py` output, `v0.2.0` spec/architecture/coverage (`81%`) docs, and `config.schema.json` + `config.full.example.yaml`

## Verification baseline (re-measured 2026-11-03 for `v0.2.0`)

The three gates below are the only accepted evidence that a change is done. Numbers are the
state at the time of writing; a change may not raise any of them.

```bash
.venv/bin/python -m ruff check src tests     # All checks passed
.venv/bin/python -m mypy src                 # Success: no issues found in 38 source files
.venv/bin/python -m pytest -q                 # 425 passed, 1 xfailed
```

- **ruff:** clean across `src` and `tests`.
- **mypy strict:** 0 errors. The former 17-error debt (`utils/parallel.py`, `utils/update.py`,
  `output/parquet_writer.py`, `cli/commands.py`) was paid down in the `v0.2.0` batch.
- **pytest:** 425 passed / 1 xfailed (317 `unit`, 108 `integration`, 1 `e2e`); includes the
  239-file corpus sweep.
- **Pylance/pyright strict** is a second, stricter lens and remains advisory until a config is
  committed.
- **mypy is installed** in `.venv` as of 2026-10-23 (2.4.0); it is a dev-group tool (**T6**).

## Decisions pinned

| # | Decision | Why |
| --- | --- | --- |
| D1 | Keep `FileMeta` metaclass | `__init_subclass__` never runs for `Problem` itself -> fields declared on the base class would silently never register. |
| D2 | No `@dataclass` / `ABC` | Fields are descriptors; a bare `Transformer()` is a deliberate no-op child; model-layer `parse` is already a classmethod. |
| D3 | No numpy in the parser | Text->number is already C `int()`; no gain at this data scale. |
| D4 | Cordeau stays an island | Separate grammar, own parser/converter; untouched. |
| D5 | Keep both `FuncT(int)` and `NumberT()` | Different strictness; used by different fields. |
| D6 | Task 4.1 = **option A**: class-only rename `DataTransformer` -> `ProblemNormalizer` | Smallest ripple; keeps `models.Transformer` upstream-faithful. |
| D7 | Batch 1 items 1.5 / 1.6 | Completed. |
| D8 | Subtractive LSP fix for `Problem.parse()` | Removed `parse()` on base `Problem`; parsing belongs to `StandardProblem` and `FormatParser`. |
| D9 | `Field.__get__` descriptor | Implemented non-data descriptor protocol, eliminating `Problem.__getattribute__` interception. |

## Non-goals / out of scope

- 14 pre-existing converter/integration failures (v1-schema assertions in `tests/converter/`) - not caused by parser refactoring; handled in converter batch.
- Removing the metaclass, adopting `@dataclass` or `ABC` - rejected (D1/D2).
- numpy in the parser - rejected (D3).

## Tasks

### Batch 1 - `models.py` micro-cleanups — **COMPLETED**

- [x] **Task 1.1 - `create_explicit_matrix` header cleanup**
- [x] **Task 1.2 - `FuncT.parse`: narrow the exception clause**
- [x] **Task 1.3 - `NumberT.parse` error parity with `FuncT`**
- [x] **Task 1.4 - `ContainerT.parse`: use the `enumerate` index**
- [x] **Task 1.5 - Dedupe terminal-stripping block (`_split_items`)**
- [x] **Task 1.6 - `BiSep.from_value` classmethod**

### Batch 2 - `StandardProblem.parse` structural simplification — **COMPLETED**

- [x] **Task 2.1 - Single-pass decoupled splitting (`_split_tsplib_text`) and module decomposition into `tokenization.py`, `fields.py`, `transformers.py`, and `models.py`**

### Batch 3 - ETL failure visibility

- [x] **Task 3.1 - Trace `process_files_parallel()` result consumption**

  + **What:** Trace where the stats dict (`successful`/`failed`/`errors`) returned by
    `ParallelProcessor.process_files_parallel()` is consumed in the CLI / `core` pipeline.
  + **Why:** Workers log and record failures, but if the caller never surfaces the `errors` list
    or exits non-zero, a failed batch looks silent ("no errored batches shown").
  + **Where:** `src/converter/core/`, CLI entry points.
  + **How much:** Low (investigation only).
  + **DoD:** A written trace stating whether/where failures surface. No code change yet.

- [x] **Task 3.2 - (conditional on 3.1) Surface failures loudly**

  + **What:** Make the CLI print the error summary and exit non-zero when any batch failed.
  + **Why:** Failures must be visible at the process boundary, not buried in a returned dict.
  + **How much:** Low.
  + **DoD:** Running the pipeline against one deliberately broken file produces a visible,
    non-zero failure.

### Batch 4 - naming collision (option A locked, D6)

- [ ] **Task 4.1 - Rename converter class `DataTransformer` -> `ProblemNormalizer` (class only, no legacy alias)**

  + **What:** Rename the class in `src/converter/core/transformer.py`, remove the `DataTransformer = ProblemNormalizer` release-cycle alias (`transformer.py:511`), and update all remaining references and imports across `tests/` (20 sites) and `docs/` (6 sites); keep the module filename. Also remove the duplicated `_nint` helper in `transformer.py:45` and import `nint` from `converter.utils.cost`.
  + **Why:** `models.Transformer` (format parser) vs `converter ... transformer.py::DataTransformer` (ETL reshape) name collision is confusing, and keeping a backwards-compatible alias for a single-user repo left `tests/` and `docs/` importing the retired name.
  + **Where:** `src/converter/core/transformer.py` + referencing modules, `tests/converter/**`, `tests/tsplib_parser/test_integration_cordeau.py`, `tests/e2e/test_e2e_pipeline.py`, `docs/**`.
  + **How much:** Low/Medium.
  + **DoD:** Zero `DataTransformer` references in `src/`, `tests/`, and `docs/` (excluding historical register notes); `nint` imported from `converter.utils.cost`; converter suite green.

### Batch 5 - documentation — **COMPLETED**

- [x] **Task 5.1 - Comment near `FileMeta`**
- [x] **Task 5.2 - `src/tsplib_parser/README.md` with 3-layer architecture and mermaid diagrams**

### Batch 7 - Post-`v0.2.0` Review Fixes, Corpus Independence (`C1`–`C3`), Spec/Coverage Docs & Config Schema

- [ ] **Task 7.1 - Fix `GEO` degree truncation in `src/converter/utils/cost.py` (`_geographical`)**

  + **What:** Change `deg = _nint(x)` to C-style truncation `deg = int(x)` in `_geographical` (`src/converter/utils/cost.py:80`) to match TSPLIB95 spec §2.4 (`deg = (int) x[i]`) and canonical `burma14` distances (`d(1,3) = 510`, not `560`).
  + **Why:** Rounding the degree part shifts every `GEO` coordinate whose fractional part is `>= 0.50`, breaking canonical TSPLIB95 tour lengths and forcing `gpu_accelerated_clean` to keep a separate `compute_geographical` implementation.
  + **Where:** `src/converter/utils/cost.py:75-95`, `tests/converter/test_unit_cost.py`, `tests/converter/test_unit_cost_exports.py`.
  + **How much:** Low (~15 lines).
  + **DoD:** `geographical` in `cost.py` matches `burma14` canonical distances (`d(1,3) == 510`); `pytest tests/converter/test_unit_cost*.py -q` passes.

- [ ] **Task 7.2 - Enforce Corpus Independence Rules `C1`, `C2`, and `C3`**

  + **What:**
    1. `C3` (No config default pointing into `datasets_raw`): Remove `./datasets_raw/problems` defaults from `config.yaml:4`, `src/converter/config.py:15`, and `src/converter/cli/commands.py:348` (use `./datasets/problems` or require explicit `-i/--input-dir`), and update `docs/guides/USER_GUIDE.md:119`;
    2. `C2` (No corpus directory shape encoded in library/CLI code): Remove `parent_dir = problem_path.parent.parent; tour_dir = parent_dir / "tour"` in `src/converter/core/transformer.py:298-312` and `"all_problems" in str(input_path)` / `cvrplib` sibling traversal in `src/converter/cli/commands.py:103-113`;
    3. `C1` (No `datasets_raw/**` path in `src/tsplib_parser`): Replace `"datasets_raw/umalaga/mdvrp/C-mdvrp/p01"` in `src/tsplib_parser/cordeau/cordeau_parser.py:34` docstring with a generic path (`"path/to/p01"`), and fix `src/tsplib_parser/README.md:73-82,132`.
  + **Why:** `.agents/rules/documentation.instructions.md` (`C1`–`C3`) and `AGENTS.md` §7 forbid coupling library/config code to the `datasets_raw/` directory tree.
  + **Where:** `config.yaml`, `src/converter/config.py`, `src/converter/cli/commands.py`, `src/converter/core/transformer.py`, `src/tsplib_parser/cordeau/cordeau_parser.py`, `src/tsplib_parser/README.md`.
  + **How much:** Medium (~60 lines).
  + **DoD:** `grep -rn "datasets_raw" src/ config.yaml` returns 0 matches; `pytest tests -q` passes.

- [ ] **Task 7.3 - Improve `examples/inspect_parse_result.py` Output**

  + **What:** Rewrite `describe()` and `inspect()` in `examples/inspect_parse_result.py` so it displays actual parsed values instead of shallow container types:
    - Print scalar `problem_data` fields (`name`, `type`, `dimension`, `capacity`, `edge_weight_type`, `edge_weight_format`) and `Matrix` summary (`class`, `size`) when `edge_weights` is present (`gr17.tsp`);
    - Print `metadata` highlights (`is_symmetric`, `weight_source`, `has_coordinates`, `has_demands`, `has_tours`);
    - Print array lengths plus a preview of the first element/row for `coords`, `demands`, `depots`, `edges`, and `tours` (with a clear label when empty because the problem is `EXPLICIT` or a `.tour` file).
  + **Why:** Currently `inspect_parse_result.py` prints `dict keys=[...]` and `coords: list len=0 first=empty`, hiding the actual parsed content.
  + **Where:** `examples/inspect_parse_result.py`.
  + **How much:** Low (~45 lines).
  + **DoD:** Running `uv run python examples/inspect_parse_result.py` displays human-readable problem metadata, symmetry/matrix info, and sample array entries for all 4 sample files; `ruff` and `mypy examples` pass.

- [ ] **Task 7.4 - Document `v0.2.0` Storage/Validation Rules in `tsplib_format_extended_spec.md` & `ARCHITECTURE.md` and Update Coverage (`81%`)**

  + **What:**
    1. In `docs/reference/tsplib_format_extended_spec.md`, document: (a) value-based symmetry derivation (`check_symmetry` over $d(i, j) = d(j, i)$ for `FULL_MATRIX` and all `EXPLICIT` formats, `M7`), (b) TSPLIB95 `nint(x) = floor(x + 0.5)` rounding for `EXPLICIT` matrices stored in `edge_weight_matrices.matrix` (`INTEGER[][]`, `M3`), and (c) the storage output conventions (`<name>.<type>.json` in `M2` and `ALLOWED_TABLES` in `m17`);
    2. In `docs/ARCHITECTURE.md`, update stale line numbers and symbol names (`ProblemNormalizer`, `NormalizedProblemData`, 9-key `ParseResult` without `nodes`, 12-key `metadata`, 9-table schema v2 including `solutions`, and `ParquetWriter.export_from_database`);
    3. Replace remaining v1 `nodes` table references in `README.md`, `docs/DATABASE_CONNECTION_GUIDE.md`, `docs/diagrams/database-schema.md`, and `docs/guides/PARQUET_EXPORT.md`, and fix unlinked `§x.y` references (`L2`);
    4. Update test coverage from `63%` to the measured **`81%`** (`3,427` statements, `654` missed; `matrix.py` at `98%`) in `README.md:25,47` and `docs/reference/ARCHITECTURE_DECISIONS.md:183`.
  + **Why:** Keeps the authoritative specification and architecture docs aligned with the `v0.2.0` code and measured test coverage.
  + **Where:** `docs/reference/tsplib_format_extended_spec.md`, `docs/ARCHITECTURE.md`, `docs/reference/ARCHITECTURE_DECISIONS.md`, `README.md`, `docs/DATABASE_CONNECTION_GUIDE.md`, `docs/diagrams/database-schema.md`, `docs/guides/PARQUET_EXPORT.md`.
  + **How much:** Medium.
  + **DoD:** Zero references to `DataTransformer`, `export_database_to_parquet`, `_expand_vrp_matrix`, or the dropped `nodes` table in active docs; coverage badge and text report `81%`.

- [ ] **Task 7.5 - Add JSON Schema (`docs/schemas/config.schema.json`) and Full Example Config (`config.full.example.yaml`)**

  + **What:** Create `docs/schemas/config.schema.json` describing all `ConverterConfig` fields, link it at the top of `config.yaml` via `# yaml-language-server: $schema=./docs/schemas/config.schema.json`, and create `config.full.example.yaml` with commented documentation of every available parameter (`input_path`, `file_patterns`, `output_dir`, `json_output_path`, `database_path`, `output_formats`, `batch_size`, `max_workers`, `memory_limit_mb`, `pretty_json`, `parquet_compression`, `force_reprocess`, `log_level`, `log_file`).
  + **Why:** `config.yaml` currently shows only a minimal subset of options without schema validation or parameter documentation.
  + **Where:** `docs/schemas/config.schema.json` _(new)_, `config.full.example.yaml` _(new)_, `config.yaml`.
  + **How much:** Low/Medium (~120 lines).
  + **DoD:** `config.yaml` and `config.full.example.yaml` validate against `docs/schemas/config.schema.json` and load cleanly via `load_config()`.

## Verification commands

```bash
uv run python -m pytest tests/test_format -q        # 63 passed / 1 skipped
~/.local/bin/ruff check src/tsplib_parser            # changed files
uv run converter process -i datasets_raw/problems -o <tmp>   # corpus run when a task touches parsing
```

## Deferred / parked

- Full corpus regression-harness automation.
- Anything new that surfaces during the walk - propose it, don't assume it.

| ID | Severity | Problem | Type | Where | Cause / Why | Depends on |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | Blocker | Rerun on existing DB silently no-ops: duplicate key → batch rollback, stale row kept, exit 0, JSON rewritten anyway → DB/JSON diverge | Data integrity / workflow | `operations.py:292` (`_insert_hub`), UNIQUE `:109`, batch `:434-519`, caller `commands.py:161`, update branch `commands.py:120-135` | **Resolved 2026-11-03**: `_upsert_problem_row` updates the hub in place (same id), refreshes `updated_at`, deletes the type-table and matrix rows, and re-inserts — verified by `test_reinserting_same_name_and_type_updates_in_place` | Closed |
| B2 | Blocker | CI gates: tests and ruff are green since 2026-10-23; **mypy still red (18 errors / 5 files)**; black still conflicts with the project's 2-space/120-col style | Process / verification | `tests/**`, `pyproject.toml:75`, `ci.yml`, `src/**` | **mypy resolved 2026-11-03**: `mypy src` → 0 errors (parallel/update/parquet_writer/commands annotations). black remains rejected in favour of `ruff format` | Closed |
| B3 | Blocker | One bad row kills whole batch; payload without `problem_data` vanishes uncounted (returns 0/0) | Failure isolation / data integrity | `operations.py:434-570`, silent skip `:473` | **Resolved 2026-11-03**: one transaction per problem (DuckDB has no savepoints); a failing row rolls back alone and lands in `failed[]`; missing `problem_data` is counted as a failure — verified by `test_batch_isolates_a_refused_problem` and `tests/converter/test_integration_batch_accounting.py` | Closed |
| M1 | Major | `analyze` crashes on any DB with HCP/SOP; `--type TOUR` guaranteed to fail | Correctness / CLI | `commands.py:313`, `:264`; `operations.py:830-831`, `:281-287` | `None` formatted with `:<15` (NULL `edge_weight_type` emitted as `CAST(NULL AS VARCHAR)`); `TOUR` offered in `Choice` but schema guard raises | M12 taxonomy drift |
| M2 | Major | JSON output: path traversal via file `NAME`, silent overwrite, thread race, JSON/DB key divergence | Security / data integrity | `json_writer.py:64,122`; `validation.py:70-71`; `commands.py:170-185`; `operations.py:573-583` | **Resolved 2026-11-03**: filenames are `_sanitize_segment`-cleaned `<name>.<type>.json`; identical `(name, type)` content is skipped under a lock; changed content still overwrites (`test_unit_output_guards.py`) | Closed |
| M3 | Major | Float edge weights silently rounded to int (`1.5` → `2`) | Data integrity | `operations.py:191`; `models.py:161-176`; `transformer.py:186` | **Resolved 2026-11-03**: `_nint(x) = int(floor(x + 0.5))` applied in `_convert_edge_weights_to_matrix`; `INTEGER[][]` kept per DP10-12 (`test_fractional_explicit_weights_use_tsplib95_nint`) | Closed |
| M4 | Major | Failed matrix conversion still stores problem, minus distances | Silent failure / data integrity | `transformer.py:85-98` vs `api.py:203-206` | **Resolved 2026-11-03**: EXPLICIT conversion failure raises `TransformError`, so the worker discards the problem (`test_explicit_conversion_failure_raises_transform_error`) | Closed |
| M5 | Major | VRP preprocessed temp files orphaned on every parse failure | Resource leak | `parser.py:142-146` (unlink on success only), temp created `:366-375` | No `try/finally`; correct pattern exists in `transformer.py` tour path — **fixed 2026-10-14** (PB3, see `src/tsplib_parser/TODO.md` §9) | G1 no tests |
| M6 | Major | `special_func` documented, accepted, dropped; `UnsupportedFeatureError` never raised | Dead feature / API lie | `parser.py:83-142`, `:790`; `models.py:831` | `StandardProblem.parse(text, **options)` never reads options; no dispatch | **Revised 2026-10-14 (P2):** XRAY parses and needs no `special_func`; the parser must record the declared weight type (parser-side, Phase C) and the converter raises `UnsupportedFeatureError` for `SPECIAL` without a callable — done (`CV2` in `src/converter/TODO.md`) |
| M7 | Major | `is_symmetric` guessed from format names, can be false | Data integrity | `parser.py:727-753` | **Resolved**: `_check_symmetry` builds the explicit matrix (also for `FULL_MATRIX`) and `check_symmetry` compares `(i, j)` vs `(j, i)` values; `test_symmetry_check_inspects_explicit_matrix_values` | Closed |
| M8 | Major | CVRP customer-only matrices get fabricated zeroed depot row | Data integrity | `transformer.py:238-262` | Deliberate decision #5; `0.0` is not a distance → garbage depot legs | Accepted compromise, unmarked |
| M9 | Major | `errors="latin-1"` is not a codec error handler → tour files silently dropped | Silent failure / correctness | `transformer.py:423` | `LookupError: unknown error handler` → broad except → `None` → tour absent | G2 untested path |
| M10 | Major | `SimpleConverter.to_json(data, "problem.json")` crashes | Correctness / public API | `api.py:65` | `os.makedirs(os.path.dirname(...))` → `makedirs("")` → `FileNotFoundError` — **fixed 2026-10-26** (guarded `if dirname: os.makedirs(dirname)`) | Closed |
| M11 | Major | `converter validate` validates nothing | UX / docs | `commands.py:228-258`; `verify_database.py` | **Resolved 2026-11-03**: `DatabaseManager.integrity_failures()` runs seven SQL checks (hub/type joins both ways, EXPLICIT matrix presence, square/dimension, coordinates, solutions FK) and the CLI exits 1 on any violation (`test_integration_validate_integrity.py`) | Closed |
| M12 | Major | Problem-type taxonomy copied 5+ times, already drifted | Architecture / SSOT | `operations.py:105,200-206,212-218,281-287`; `validation.py:88`; `scanner.py:150-157`; `commands.py:264`; `__init__.py:8-14` | No single enum/registry; `TOUR` accepted by CLI/docs, rejected by schema | Partially resolved 2026-10-26 (STORABLE_PROBLEM_TYPES in types.py wired to DB CHECK and dispatch) |
| m1 | Minor | `--batch-size` no-op | CLI / UX | `parallel.py:44`; `commands.py:140` | Stored, never read; scanner batching never triggers | — |
| m2 | Minor | `--workers 0` crashes | Correctness | `commands.py:138-146` | No validation; `ProcessPoolExecutor(0)` ValueError — **fixed 2026-10-26** (validated workers >= 1 via click.BadParameter) | Closed |
| m3 | Minor | Docstring sells connection pooling / backpressure / memory limit — none enforced | Docs / behavior | `parallel.py:22-31`, `:148-157` | `memory_limit_mb` unused; sequential mode still pays executor indirection | — |
| m4 | Minor | Dead-API archipelago (~800 lines uncalled) | Maintainability | `cost.py:148`; `transformer.py:339-552,280-333`; `config.py`; `update.py:37,138,223,249`; `parallel.py:240,255`; `parquet_writer.py:131-168`; `conftest.py:76-84` | Written + documented, never wired; stale v1 asserts | S4 feature sprawl |
| m5 | Minor | Public validator crashes instead of returning errors | Correctness | `validation.py:81` | `.upper()` on `None`/non-str → `AttributeError` | — |
| m6 | Minor | `if "VRP" in t` substring match | Correctness | `operations.py:285` | `"VRPTSP"`-style types silently land in `cvrp_problems` — **fixed 2026-10-26** (explicit `_TYPE_TO_STORAGE` dict for all 53 storable types) | Closed |
| m7 | Minor | `load()` normalizes type, `load_matrix()` doesn't | API inconsistency | `operations.py:637-658` vs `:660-685` | `"VRP"` lookups fail in one path — **fixed 2026-10-26** (`load_matrix` now uses `_validate_hub_type`) | Closed |
| m8 | Minor | `.sol` parse maps depot `0` → node `-1` silently; cost regex misses negatives/scientific notation | Data integrity | `transformer.py:496-529` | `([\d.]+)` pattern; depot mapping undocumented | G2 |
| m9 | Minor | Two policies for display coords; sparse `node_id`s misalign silently | Data integrity | `transformer.py:148-160` vs `:122-146`; `validation.py` | `_build_display_coords` compresses missing entries; validation checks counts only | — |
| m10 | Minor | Scanner order = filesystem order; no dedupe; `stat()` races deletion | Reproducibility / workflow | `scanner.py:63,110,138-141` | Unsorted `rglob`; `problem_id` differs per machine | — |
| m11 | Minor | CLI heuristically re-scans `cvrplib` sibling; root containing `cvrplib`/`all_problems` double-lists files | Workflow | `commands.py:99-111` | String-match MDVRP filter + extra scan root → duplicate input | Feeds B1/B3 rollback |
| m12 | Minor | `config.yaml` write-only | Config | `commands.py:329-373`; `load_config` 0 callers | `init` emits, nothing reads; `database_path` ignored; `log_file` never wired | S4 |
| m13 | Minor | Version drift ×4 | Docs / API | `pyproject.toml` 0.1.0; `converter.__version__` 1.0.0; `tsplib_parser.__version__` 2.0.0; `commands.py:22` "0.1.0" | **Resolved 2026-11-03**: package and CLI both report `0.2.0` (`click.version_option(version=__version__)`); `tsplib_parser` keeps its own 2.0.0 version by design | Closed |
| m14 | Minor | Stale examples/docstrings (`nodes` key, `nodes.parquet`, "Step 5" w/o Step 4, unused `output_dir`) | Docs | `api.py:262-268`; `parquet_writer` docstring; `worker_functions.py:70`; `cordeau_parser.py:249` | Retired v1 shapes still documented | S1 |
| m15 | Minor | Parser nits: `# EXPLAIN:` in parse loop; `self.func.__name__` AttributeError for `partial`; `MapT` dup keys last-wins; extra `EDGE_LIST` tokens ignored; `#` lines in sections hard-fail | Correctness / robustness | `models.py:860,142,832-905` | — | — |
| m16 | Minor | Cordeau: time-window errors swallowed; extra node lines sliced away; MDVRP flattened to `CVRP`, per-depot `Q`/`D` dropped | Data integrity | `cordeau_parser.py:306-307,69-87`; `cordeau_converter.py:123,151` | RESOLVED: FormatError inheritance, CordeauProblem(Problem), to_tsplib lossless LKH mode with DEPOT_CAPACITY/DEPOT_DURATION sections | Closed |
| m17 | Minor | f-string SQL in Parquet export (`COPY` interpolation, template+`replace`) | Security (bounded) | `parquet_writer.py:112-114,150-152,219` | **Resolved 2026-11-03**: every export identifier passes `_assert_allowed_table` against `ALLOWED_TABLES`; custom output names reduced to their basename (`test_parquet_export_rejects_non_allowlisted_table`) | Closed |
| m18 | Minor | `_calculate_checksum` returns `""` on error — indistinguishable from "changed" | Failure point | `update.py:126-131` | Transient read failure → reprocess loop | Feeds B1 |
| m19 | Minor | `update_file_tracking` reimplements upsert (TOCTOU window) | Workflow / correctness | `operations.py:713-760` vs upsert at `:609` | Check-then-insert duplicates logic | — |
| m20 | Minor | Unused runtime deps: `pandas` 0 imports, `ruff` as runtime dep, `pyyaml` reachable only via dead config | Dependencies | `pyproject.toml:20-31` | Liability with no consumer | m4, m12 |
| m21 | Minor | Black vs ruff-format contradiction; dual pytest config closed 2026-10-27 | Tooling | `[project.optional-dependencies].dev` declares `black`; `[tool.ruff.format]` is the formatter; pytest is now single-sourced in `[tool.pytest.ini_options]` | Two formatters, one infeasible | Root for B2 |
| m22 | Minor | Whole-corpus results held in memory before single batch insert | Performance / memory | `worker_functions.py:70-90`; `parallel.py:122,181`; `commands.py:151-161` | Matrices pickled + retained; peak ≈ Σ matrix sizes | Interacts with B1/B3 fix |
| n1 | Nit | Stale "circular imports" rationale | Docs | `tsplib_parser/__init__.py:64-66` | No cycle exists; `parser.py` never imports package `__init__` | — |
| n2 | Nit | 308-line exceptions module, 44% covered, ~200 lines docstring | Docs | `converter/utils/exceptions.py` | Docstring cosplay for 6 classes | m4 |
| n3 | Nit | 2-space/120-col style vs CI black defaults | Style / tooling | repo-wide | Pick one universe | m21 |
| n4 | Nit | Commit message `some changes, don't even know` | Process | git `0e04050` | Reviewability of history | — |
| n5 | Nit | Reviewer bookmark comment left in hot path | Maintainability | `models.py:860` | Question answered 20 lines later | — |
| S1 | Systemic | Migration half-landed: v2 in `src`, absent in tests/docs/CLI | Root cause | `src` vs `tests/**`, docstrings, `commands.py:264` | Generates B2, B3 (`TOUR`), M1, m14 | — |
| S2 | Systemic | Two error philosophies colliding: strict parser vs lenient storage | Root cause | `models.py:831-905` vs `transformer.py`, `commands.py` | Garbage in, success reported | — |
| S3 | Systemic | Non-idempotent writes vs re-run-centric operations | Root cause | only upsert = `operations.py:609`; rest insert-only | Contradicts `--force`/incremental model | B1, B3 |
| S4 | Systemic | Feature sprawl ahead of wiring | Root cause | `cost.py`, solution ingestion, backup, progress, config, `special_func` | Dead code that looks alive; docs describe intended behavior | m4, M6, M11 |
| S5 | Systemic | SSOT violations | Root cause | type ×5, version ×4, pytest config ×2 (closed 2026-10-27), formatter ×2, DB path ×2 | Drift is already fact, not a risk | M12, m13, m21, B2 |
| G1 | Gap | VRP preprocessing entirely untested (UTF-8→latin-1 fallback, section skips, multi-dim demands, `CAPACITY_VOL/WEIGHT`, temp files) | Coverage | `parser.py:233-373` | 0 tests; proven leak M5 | M5 |
| G2 | Gap | Solution discovery / `.opt.tour` / `.sol` / cost extraction: 0 tests, 0 callers | Coverage | `transformer.py:339-552` | Contains broken latin-1 path | M9, m4, m8 |
| G3 | Gap | `cost.py` and `config.py` 0% covered | Coverage | `cost.py`, `config.py` | Dead modules | m4, m12 |
| G4 | Gap | `parquet_writer` 16%; `export-parquet` and `init` commands untested | Coverage | `parquet_writer.py`; `commands.py:433-481,329-373` | — | m17 |
| G5 | Gap | `update.py` modified-file branch, backup, candidate scan untested | Coverage | `update.py:86-106,149-170,260-273` | Exactly the branch B1 breaks | B1, m18 |
| G6 | Gap | Force/re-insert path test asserts log substring, not DB state | Coverage | `tests/test_integration/test_cli.py:181-201`; `operations.py:665-681` | False confidence; test that would have caught B1 | B1 |
| G7 | Gap | No tests for: duplicate/name-collision JSON, `NAME` traversal, concurrent writes, `analyze` NULL `edge_weight_type`, `--types TOUR`, rollback accounting, `WORKERS=0` | Coverage | `tests/**` | — | M1, M2, B3, m2 |
| G8 | Gap | `in_memory_db` fixture unused + broken; `verify_database.py` not collected; `validate` a stub | Coverage | `tests/conftest.py:76-84`; `verify_database.py`; `commands.py:228` | Open-per-call `:memory:` = fresh empty DB each time | M11 |
| F1 | Fixed | `FuncT` identity lambda incompatible with `T` (mypy strict) | Type safety | `models.py:131` | `func or (lambda x: x)` returns `str` vs `T`; fixed with `cast("Callable[[str], T]", ...)` + `cast` import | Resolved |
| F2 | Fixed | `requires-python = ">=3.10"` vs PEP 695 syntax (3.12+ only) | Tooling / metadata | `pyproject.toml:10` (+classifier `:21`); `ci.yml:14`; `README.md:27,63`; `docs/README.md:125`; `docs/guides/USER_GUIDE.md:78`; `docs/reference/CONTRIBUTING.md:535` | Metadata claimed 3.10/3.11 support; file can't parse there; bumped to `>=3.12` + CI matrix/docs ripples | Resolved |
| F3 | Fixed | Extended VRP/LKH-3 headers stripped even when the problem class registers them, so typed fields never ran | Data integrity / typing | `parser.py:292-302` (guard now at `:41-54`, `:243-249`) | `VEHICLES : 16` became `vehicles='16'` (str), `DEPOTS : 4` produced `num_depots=None` **and** a stray `depots='4'` key; the section branch already had the `not in fields_by_keyword` guard, the header branch did not | Resolved 2026-10-23 — guard added, regression test `test_registered_lkh_headers_keep_typed_values`, corpus sweep neutral (511/1329 parse before and after, identical failure set) |
| F4 | Fixed | `EdgeDataField.parse_for_problem` returned `Any` from a `list[list[int]]` signature (mypy + pyright flag) | Typing | `fields.py:203-210` | `TransformerField` stores `self.tf: Transformer[Any]`, so the un-narrowed `parse` is `Any`; `build_transformer` guarantees `EdgeDataT` | Resolved 2026-10-23 — documented `cast` on the subclass-only fallback, `isinstance` fast path unchanged |
| F5 | Fixed | Converter consumers typed against `dict[str, Any]` while the producer emitted `ParseResult` | Typing / contract | `core/transformer.py:12,39,332-345`; `utils/worker_functions.py:66-87`; 10 test modules | Producer signature was `ParseResult`, consumers took `dict[str, Any]`; TC001 (type-only import at runtime) and a `dict[str, Unknown]` return followed | Resolved 2026-10-23 — imports moved into `TYPE_CHECKING`, explicit local annotations |
| F6 | Fixed | `SimpleConverter.to_json(data, "problem.json")` crashes | Correctness / public API | `api.py:65` | `os.makedirs(os.path.dirname(...))` called on `""` -> `FileNotFoundError`; fixed by guarding `if dirname:` + regression test | Resolved 2026-10-26 |
| F7 | Fixed | `analyze` crashes on database with NULL `edge_weight_type` (HCP/SOP) | Correctness / CLI | `commands.py:313` | `p.get('edge_weight_type')` is `None` -> `None.__format__` raises `TypeError`; fixed via `p.get('edge_weight_type') or 'N/A'` + regression test | Resolved 2026-10-26 |
| F8 | Fixed | `to_json_format` drops explicit distance matrix | Correctness / JSON | `transformer.py:187` | Added `edge_weight_matrix` to forwarded keys; un-xfailed `test_json_carries_the_explicit_matrix` | Resolved 2026-10-26 |
| F9 | Fixed | JSON writer path traversal via `name`/`type` | Security / JSON | `json_writer.py:60,119` | Sanitized with `Path(str(...)).name.strip()` + regression test `test_write_problem_prevents_path_traversal` | Resolved 2026-10-26 |
| F10 | Fixed | `--workers 0` crashes with `ValueError` | CLI / validation | `commands.py:72` | Added `if workers <= 0: raise click.BadParameter` + regression test `test_process_with_zero_workers_fails` | Resolved 2026-10-26 |

### Typing register (opened 2026-10-23)

_First full `mypy src` run. Every row is reproduced by the command, not inferred._

| ID | Severity | Problem | Where | Cause | Blocked on |
| --- | --- | --- | --- | --- | --- |
| T1 | Major | One module accounts for a third of the mypy debt and most of the editor noise | `utils/parallel.py:51,59,89,158,178,242` | Bare `Callable`, untyped `Queue()`, `_start_time` inferred `None`, and a `dict[str, Any]` producer contract that leaks `Unknown` through `Future`/`as_completed` (6 errors under mypy; 7 in the workspace Pylance pass, 17 when the file is analyzed alone) | Worker-result contract (design decision pending) |
| T2 | Major | 7 mypy errors: untyped module cache plus `object` arithmetic | `utils/update.py:37,205,207,209,213,214,218` | `_change_cache` has no annotation → values are `object`, so `+ int` and `.append` fail | — |
| T3 | Major | 3 mypy errors: `Path`/`str` mix-up and indexing a possibly-`None` tuple | `output/parquet_writer.py:73,74,224` | Same parameter reassigned from `str` to `Path`; `fetchone()` result indexed without a guard | — |
| T4 | Minor | 1 mypy error: indexing a possibly-`None` tuple | `cli/commands.py:552` | `fetchone()` result indexed without a guard | — |
| T5 | Minor | 1 missing-stub note | `converter/config.py:7` | `pyyaml` ships no `py.typed`; needs `types-PyYAML` (dev) or a targeted override | — |
| T6 | Fixed | `mypy`, `pytest`, `ruff` were runtime dependencies | `pyproject.toml` `dependencies` | `uv add` defaults to the main group; the `dev` extra already listed older pins | Resolved 2026-10-23: `uv add --dev` + `uv remove`; runtime deps are now `click, duckdb, pandas, psutil, pyyaml`; the pip-facing `dev` extra is documented as a mirror of `[dependency-groups].dev`! |
| T7 | Minor | 6 pyright-strict-only items in `tsplib_parser` (mypy is clean there) | `models.py:203,217`; `parser.py:542`; `transformers.py:93` (×2); `types.py:132` | Private descriptor access, an unnecessary `isinstance`, and lambda inference | Decision: commit a pyrightconfig and treat it as a second gate |
