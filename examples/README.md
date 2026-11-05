---
title: `routing_data/examples` — runnable parser examples
description: >
  Standalone, typed example scripts that demonstrate the public parser API on
  inline fixtures and on corpus files, plus the command that runs each one.
created: 2026-11-03
modifications:
  - date_modified: 2026-11-03
    modifications:
      - description: >
          Created together with the three examples promoted from the one-off
          `tmp/probe_*.py` scratch scripts.
related_files:
  - "[inspect_adjacency_edges.py](./inspect_adjacency_edges.py)"
  - "[scan_corpus_folders.py](./scan_corpus_folders.py)"
  - "[inspect_parse_result.py](./inspect_parse_result.py)"
tags: [guide/setup, guide/etl, guide/cli, notes/overview, analysis/architecture, notes/project]
---

# `routing_data/examples`

Small, self-contained scripts that show how to call the parser package. They are
examples, not library code: nothing under `src/` imports them.

| Script | What it shows | Needs the corpus |
| ------ | ------------- | ---------------- |
| [`inspect_adjacency_edges.py`](./inspect_adjacency_edges.py) | Parses an inline `ADJ_LIST` instance and prints its edges | No |
| [`scan_corpus_folders.py`](./scan_corpus_folders.py) | Parses the first file of every corpus folder, Cordeau included | Yes |
| [`inspect_parse_result.py`](./inspect_parse_result.py) | Prints the type and shape of every `ParseResult` key | Yes |

## Running

```bash
# Inline fixture — no data required
uv run python examples/inspect_adjacency_edges.py

# Corpus walk (defaults to datasets_raw)
uv run python examples/scan_corpus_folders.py

# Parse-result contract (defaults to datasets_raw/problems)
uv run python examples/inspect_parse_result.py
```

## Typing and linting

Every example is fully annotated and must pass the repository gates:

```bash
uv run ruff check examples
uv run mypy examples
```
