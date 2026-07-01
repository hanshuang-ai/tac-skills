# Widget Registry Query

Use the checked-in widget registry snapshot only through the query script with progressive disclosure.
Do not load the full snapshot into agent/chat context directly.

## Default Data Source

- Snapshot file: `references/widget_registry.snapshot.json`
- Query script: `scripts/query/query_widget_registry.py`
- Library config: `references/library_config.json`

`references/widget_registry.snapshot.json` is the compatibility snapshot for the
currently prepared active library. Library-specific cached snapshots live under
`references/libraries/<library-id>/widget_registry.snapshot.json`.

## Progressive Disclosure Rule

1. Start with `summary` level.
2. If one candidate looks right, re-run with `detail`.
3. Use `full` only when exact raw fields are needed for debugging or schema work.

Do not load the whole snapshot into agent/chat context. If query output is insufficient, refine the query, increase `--level` for a narrow target, or update the query script.

## Example Commands

Query a widget by name:

```bash
python scripts/query/query_widget_registry.py WTButton
```

Expand the selected widget:

```bash
python scripts/query/query_widget_registry.py WTButton --kind widget --level detail
```

Inspect a text style family:

```bash
python scripts/query/query_widget_registry.py Body2 --kind text-style
```

Inspect a color resource:

```bash
python scripts/query/query_widget_registry.py wt_primary_main_color --kind color
```

Query a library-specific snapshot without changing the active snapshot:

```bash
python scripts/query/query_widget_registry.py CAUIButton --registry references/libraries/caui/widget_registry.snapshot.json --level detail
```

Force raw output for a single widget:

```bash
python scripts/query/query_widget_registry.py WTLoadingButton --kind widget --level full --limit 1
```

## What Each Level Returns

- `summary`: identity, class name, render kind, attr count, variant count
- `detail`: adds attrs, variant names, style refs, size hints, text-style attrs
- `full`: returns the raw entry from the snapshot

## Refresh Policy

Library snapshots are cached after AAR parsing. Refresh a library snapshot only
when the underlying AAR changes or when semantic rules are updated.

Manual refresh commands:

```bash
python scripts/pipeline/build_widget_registry.py --library wt --refresh-snapshot
python scripts/pipeline/build_widget_registry.py --library caui --refresh-snapshot
```

To prepare the compatibility snapshot for a pipeline run, pass the library id:

```bash
python scripts/pipeline/pipeline.py mastergo_raw.json output/ res/ --library caui
```
