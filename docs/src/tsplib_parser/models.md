---
title: models — the package core
description: >
  The roles of FileMeta, Problem and StandardProblem, why the base class exists, how this port differs from upstream tsplib95, and the three extension points (keyword, rule, distance). Repo-specific companion to the python-logic series.
created: 2026-10-07
type: guide
scope: repo
status: draft
author:
  - Lucas Galdino
  - GitHub Copilot
modifications:
  - date_modified: 2026-10-07
    modifications:
      - description: >
          First version. Rewrote §1.1 and §1.2 of PARSER-DETAILS.MD as a repo-specific overview: the cast of classes with their failure modes, the four-event creation chain, the upstream comparison condensed to one idea, the keyword/rule/distance extension points with the runnable HexField demo, and the open verdict on the base class.
related_files:
  - [PARSER-DETAILS.MD](../../../src/tsplib_parser/PARSER-DETAILS.MD)
  - [models.py](../../../src/tsplib_parser/models.py)
  - [parser-pipeline.md](./parser-pipeline.md)
  - [descriptors-fields.md](../../studies/python-logic/theoretical/descriptors-fields.md)
tags:
  - guide/tsplib-parser
  - guide/package-overview
  - guide/problem-classes
---

# models — the package core

## What this file is

The map of the three classes in [`models.py`](../../../src/tsplib_parser/models.py) — what each owns, why the split exists, and where the extension points are. Field-level detail lives in [descriptors-fields.md](../../studies/python-logic/theoretical/descriptors-fields.md); the parser around this package is [parser-pipeline.md](./parser-pipeline.md).

## The cast

| Component | Runs when | Owns | If removed |
| --- | --- | --- | --- |
| `FileMeta` | once per class, at import | builds `fields_by_name` and `fields_by_keyword` | `parse` has no keyword index, the `Field.__get__` default-returning lookup dies, `as_dict` cannot enumerate the schema |
| `Problem` | inherited, never instantiated here | `__init__`, `as_dict`/`as_name_dict`/`as_keyword_dict`, the lenient base `parse` | `parser.py` (`as_name_dict()`) breaks; unset fields raise `AttributeError` instead of returning defaults |
| `StandardProblem` | instantiated by `parse` | the 18 TSPLIB95 keywords, the strict `parse`, `create_explicit_matrix` | nothing parses; there is no schema |

`Problem` declares zero `Field` values — [`models.py:629`](../../../src/tsplib_parser/models.py#L629) is a type annotation, not an assignment — so its registries are empty while `StandardProblem`'s hold the 18 real ones. The two dictionaries are separate objects, each built independently for its own class.

### The four-event creation chain

Only the first event involves `FileMeta`; see [metaclasses-new-mro.md](../../studies/python-logic/theoretical/metaclasses-new-mro.md) for its internals.

```ascii
FileMeta.__new__                builds the CLASS       import time, once
        ↓
StandardProblem.parse → cls()   builds the INSTANCE    per call
        ↓
the setattr loop                fills the INSTANCE     per line
        ↓
field.parse(value)              text → python data     per field
```

`StandardProblem` is the class actually called during a parse — [`parser.py:142`](../../../src/tsplib_parser/parser.py#L142) calls `StandardProblem.parse(text, special=...)`, so `cls` is always `StandardProblem` here. `Problem` is never instantiated in this repository; it exists to be inherited from.

### What parse does, in one paragraph

`StandardProblem.parse` ([`models.py:121`](../../../src/tsplib_parser/models.py#L121)) is a single pass over the file lines: blank lines are skipped, `keyword: value` pairs outside sections go through `cls.fields_by_keyword`, `_SECTION`/`EOF` lines open and close a section accumulator that parses each collected body with `field.parse(body)`, and everything else is data. Lexical splitting lives in `tokenization.py`, section storage in the parser itself; the `Field` classes in `fields.py` own the text-to-value conversion. Errors are collected, never raised mid-stream, and one `ParseError` is raised at the end. The line-by-line walk is covered in detail in [parser-pipeline.md](./parser-pipeline.md).

## Why the base class exists

`Problem` answers "what can any field-backed problem do"; `StandardProblem` answers "what does TSPLIB95 add". The split is inherited from upstream [`tsplib95`](https://github.com/rhgrant10/tsplib95/blob/master/tsplib95/models.py), which defines the same three names; this package is a port of that shape.

The port and upstream differ in one idea, seen four ways: upstream writes its index cards by hand and then throws the shopping list (the field declarations) away; this port keeps the shopping list on the class and reprints the index cards from it at every class creation.

| Aspect | Upstream | This port, and the catch |
| --- | --- | --- |
| Where the fields live | taken out of the class; only the index cards stay | fields stay on the class; any loop over the namespace must filter with `isinstance(v, Field)`, and `Problem.name` remains askable as a declaration |
| How text is cut up | one regex splits the whole file at known keywords | a line loop with a small state machine; unknown forms like `FIXED_EDGES :` are understood and bad lines are reported with context |
| Extra index cards | two more maps, one read by its parser, one read by nothing | none — the same information sits on each field object, so there is less to keep in sync |
| Render/IO surface | `render`, `save`, `write`, `load` on `Problem` | not carried over; LKH emission would be a new consumer, not a method squeezed into the model |

The cost lands on lookups (a little filtering and rebuilding); the benefit is a single source of truth for the schema.

## Extension points

Adding a keyword is not the same as adding a rule. `IntegerField` is not a peer of `TransformerField` — it is a child of it:

```text
Field
  ├─ ToursField                    a direct Field subclass, not transformer-backed
  └─ TransformerField              holds self.tf, calls build_transformer()
       ├─ StringField              → FuncT(func=str)
       ├─ IntegerField              → FuncT(func=int)
       ├─ IndexedCoordinatesField
       ├─ DepotsField
       ├─ DemandsField
       ├─ MatrixField
       ├─ EdgeListField
       └─ EdgeDataField
```

| What you want to add | What you write | New class? |
| --- | --- | --- |
| a new keyword, parsed by a rule that exists | one declaration: `intensity = IntegerField("INTENSITY_SECTION")` | no |
| a new keyword, parsed by a rule that does not exist | a `TransformerField` subclass overriding `build_transformer`, plus a declaration of it | yes, one |
| a new rule for a keyword that exists | re-declare the *same attribute name* with the different field class | yes, one |

The third row needs no registry work: the child's declaration overwrites the parent's entry during the base-to-subclass merge.

<details name="demos">
<summary><h5>Demo: the first two rows, runnable (copy and run)</h5></summary>

```python
from tsplib_parser.fields import IntegerField, TransformerField
from tsplib_parser.models import StandardProblem
from tsplib_parser.transformers import FuncT


class HexField(TransformerField):
  """Field that reads its value as a hexadecimal number."""

  @classmethod
  def build_transformer(cls) -> FuncT[int]:
    # the one and only new rule
    return FuncT(func=lambda text: int(text, 16))


class HexProblem(StandardProblem):
  intensity = HexField("INTENSITY_SECTION")        # new rule + new keyword


class PlainProblem(StandardProblem):
  intensity = IntegerField("INTENSITY_SECTION")    # existing rule, new keyword


h = HexProblem.parse("NAME: h\nDIMENSION: 2\nINTENSITY_SECTION: ff\n")
p = PlainProblem.parse("NAME: p\nDIMENSION: 2\nINTENSITY_SECTION: 255\n")
print(h.intensity, p.intensity)
print(len(HexProblem.fields_by_name), len(PlainProblem.fields_by_name))
```

```text
255 255
19 19
```

Both classes end up with 19 registered fields — the 18 inherited ones plus `intensity` — and only `HexProblem` needed a new class to get its extra field parsed.

</details>

### The third extension point: distance

A different distance rule is neither a keyword nor a parse rule. `create_explicit_matrix` lives on `StandardProblem` ([`models.py:167`](../../../src/tsplib_parser/models.py#L167)), but the classification of *where* the weights came from lives one layer up, on the parser: `_identify_weight_source` ([`parser.py:562`](../../../src/tsplib_parser/parser.py#L562)), read into `metadata["weight_source"]` by `_extract_metadata` ([`parser.py:497`](../../../src/tsplib_parser/parser.py#L497)). `Field` classes stop at "text in, value out", so:

- a subclass that changes what numbers **mean** overrides a **method**;
- a subclass that adds a keyword writes a **declaration**.

Two extension points, not one. How matrices are built today — and the numpy question — is part of [parser-pipeline.md](./parser-pipeline.md).

## Why subclass polymorphism is needed

Needed today: `ExtendedProblem` ([`models.py:236`](../../../src/tsplib_parser/models.py#L236)) already subclasses `StandardProblem` to model TSPLIB-extended keywords, while `CordeauProblem` (`cordeau/cordeau_types.py`) is an unrelated `@dataclass` outside this hierarchy. What `cls` buys is extensibility — an `XRayProblem` that adds a keyword still works through the same `parse`, with no edit to `parse` itself:

```python
class XRayProblem(StandardProblem):
    intensity = IntegerField("INTENSITY_SECTION")   # new keyword, registered automatically by FileMeta

XRayProblem.parse(text)   # cls is XRayProblem, so cls() builds an XRayProblem
```

To change how an existing keyword is parsed, re-declare the same attribute with a different field type. The premium for this insurance is one parameter name. See [classes-instances-cls.md](../../studies/python-logic/theoretical/classes-instances-cls.md) for the binding mechanics.

## Open verdict: could a single class do?

`Problem` carries the shared machinery (`__init__`, `as_dict`/`as_name_dict`, the `FileMeta` registries) without any `parse` of its own — parsing belongs strictly to format parsers (`PB6` fixed). Merging the two is still defensible for this repository: the metaclass fires on the merged class, `as_name_dict()` still serves `parser.py`, and the annotations still pass. The split earns its keep as the base for `ExtendedProblem` and future keyword families.

No silent-empty path exists any more: an unregistered keyword or section is reported as an error by `StandardProblem.parse` ([`models.py:121`](../../../src/tsplib_parser/models.py#L121)) instead of being ignored, so the permissive base parser that used to return an empty instance is gone.

## Connections

### Links out

- [parser-pipeline.md](./parser-pipeline.md) — parsing versus validation, the four type mechanisms, and the dead-code findings.
- [descriptors-fields.md](../../studies/python-logic/theoretical/descriptors-fields.md) — the field objects this package registers.
- [metaclasses-new-mro.md](../../studies/python-logic/theoretical/metaclasses-new-mro.md) — how `FileMeta` builds the class.
- [factory-pattern.md](../../studies/python-logic/practical/factory-pattern.md) — the per-call view of `parse`.
- [README.md](../../studies/python-logic/README.md) — the series map of content.

### Backlinks

Files that link here:

- [classes-instances-cls.md](../../studies/python-logic/theoretical/classes-instances-cls.md) — the package overview next to its `cls` theory.
- [factory-pattern.md](../../studies/python-logic/practical/factory-pattern.md) — "what happens at import time" pointers and the parser wrap-up.
- [descriptors-fields.md](../../studies/python-logic/theoretical/descriptors-fields.md) — where upstream differences and the transformer extension point are discussed.
- [attribute-lookup.md](../../studies/python-logic/theoretical/attribute-lookup.md) — the package overview pointer.
- [metaclasses-new-mro.md](../../studies/python-logic/theoretical/metaclasses-new-mro.md) — the upstream merge note.
- [fields-vs-dataclasses.md](../../studies/python-logic/practical/fields-vs-dataclasses.md) — the record-versus-schema summary.
