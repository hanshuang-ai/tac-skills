# Mode A Summary Template (Deprecated)

Mode A no longer generates a standalone `mode_a_summary.md` by default.

The user-facing summary must live in:

```text
handoff_facts.json#summary_view
```

Reason: keeping the summary inside the canonical handoff excerpt index avoids duplicated facts and prevents information drift between Markdown documents and machine-readable handoff data.

If a standalone Markdown summary is explicitly requested by a user, generate it as a thin export from `handoff_facts.json.summary_view` only. Do not add new facts or reinterpret scope, coordinates, module inclusion/exclusion, or unresolved items.
