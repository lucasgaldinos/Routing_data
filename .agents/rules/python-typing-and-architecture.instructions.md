---
# --- Antigravity rule keys ---
trigger: glob
globs: "**/*.py, !**/.agents/**, !**/.github/**"
description: "Use when writing, typing, refactoring, or reviewing Python 3.12+ code in routing_data: import root, PEP 695/698 typing, TypeGuard and descriptor patterns, DuckDB transactional safety without SAVEPOINT, and TSPLIB95 parser invariants." # shared with VS Code
# --- VS Code instruction keys ---
name: "Python 3.12, Typing & Parser/Converter Architecture"
applyTo: "**/*.py, !**/.agents/**, !**/.github/**"
---

# python 3.12+, Typing & Parser/Converter Architecture Standards (routing_data)

## 1. Architecture Precedes Typing

- Establish functional behavior, database schemas, and input/output contracts **before** pursuing strict static type gymnastics. Never invest passes typing broken or unverified pipelines.
- Never silently strip forward-compatibility stubs or planned enum/section branches without user confirmation via `ask-clarification-questions`.
- Comments and docstrings must explain **domain/business rules and algorithmic provenance** (WHY — e.g., TSPLIB95 section grammar, Reinelt 1991 GEO coordinate truncation, DuckDB transaction semantics), never restate python syntax.

## 2. Import Root & Configuration Authority

- `src/` is the import root (`pythonpath = ["src"]`, `mypy_path = ["src"]`), **not** an importable package.
  + **Banned:** `from src.*` and cross-package relative escaping (`from ..converter import ...`).
  + **Allowed:** Absolute package imports (`from tsplib_parser.types import ProblemType`) and intra-package relative imports (`from .validation import ...`).
- [pyproject.toml](../../pyproject.toml) is the single configuration source of truth for `mypy`, `ruff`, and `pytest`. Never reintroduce `mypy.ini`, `ruff.toml`, or `setup.cfg`.
- Run linters and type checkers via `rtk .venv/bin/python -m ruff check <files>` and `rtk .venv/bin/python -m mypy <files>` (never bare system `pytest`/`mypy`).

## 3. Modern python 3.12+ Static Typing

Every public and private function carries explicit parameter and return annotations (`-> None` included):

- **PEP 585 & PEP 604:** Use built-in generics (`list[T]`, `dict[K, V]`, `tuple[T, ...]`, `set[T]`) and `X | Y | None` unions. Imports of `List`, `Dict`, `Tuple`, `Set`, `Optional`, and `Union` from `typing` are banned.
- **PEP 695 (`requires-python >= 3.12`):** Use `type Alias = ...` and `class Box[T]:` / `def fn[T](x: T) -> T:` instead of legacy `TypeVar` and `TypeAlias`. Ensure `pyproject.toml` declares `requires-python = ">=3.12"` whenever PEP 695 syntax is used.
- **PEP 698:** Decorate every implementation of a `Protocol` or `ABC` method with `@override` (`from typing import override`).
- **`object` Narrowing via `TypeGuard`:** At untrusted JSON/dict boundaries, `isinstance(x, dict)` on `object` or `Any` narrows to `dict[Unknown, Unknown]` under Pyright strict mode, and `cast("dict[str, Any]", x)` triggers `reportRedundantCast`. Write a dedicated `TypeGuard` helper (`def _is_str_dict(val: object) -> TypeGuard[dict[str, Any]]: return isinstance(val, dict)`) instead.
- **Non-Data Descriptors on Class Bodies:** Pyright synthesizes typed attribute writes only for data descriptors (defining `__set__`). When a class body uses non-data descriptors (`__get__` only) populated into `instance.__dict__` at parse time, type the class attribute with `cast("TargetType", SomeField(...))` (and use `cast("Callable[[str], T]", lambda x: x)` for polymorphic identity defaults).
- **No Unjustified Suppressions:** `# type: ignore[code]` and `# noqa: CODE` require a specific error code and concrete inline reason; never use bare suppressions as a shortcut.

## 4. DuckDB & Converter Database Invariants

- **No SQL `SAVEPOINT` in DuckDB (v1.5.6):**
  + DuckDB does not support SQL `SAVEPOINT`. A single failed statement in a transaction aborts the entire transaction block.
  + In batch conversion and loading pipelines, always validate data pre-flight with Pydantic/dataclasses or execute per-item transactions with `ON CONFLICT DO UPDATE`.
  + Isolate multi-file conversion batches so that failure of a single malformed problem or tour does not corrupt or roll back previously validated instances.
- **Database Schema & Queries:**
  + Guard nullable `cursor.fetchone()` calls with a typed helper (`_one(row, error_msg)`).
  + Mirror SQL column names as constants in `schema.py`.
  + Type all insert and update payloads with `TypedDict`.

## 5. TSPLIB95 & Extended Specification Authority

- **TSPLIB95 Node and Depot IDs:**
  + TSPLIB node and depot IDs in problem/tour files are **1-based**; `.sol` files use customer ordinals. Verify all tour and route indexing against coordinate cost recomputation.
  + `GEO` coordinate conversion truncates degrees toward zero via `int(coord_val)` (Reinelt 1991), **never** nearest-integer `_nint(coord_val)` (`burma14` `d(1,3) == 510`, not `560`).
  + Reject malformed sections loudly (`ParseError`); never swallow section errors into empty arrays or launder `ValidationError` into `ParseError`.
- **Corpus Independence:**
  + Never hardcode corpus file paths, fixed file dimensions, or assumptions about problem dimensions in parsing algorithms.
