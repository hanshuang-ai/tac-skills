# Phase D: Concurrent Asset Extraction (v2 Three-Step)

> Read this file BEFORE executing Phase D of the workflow.

## Table of Contents

1. [Workflow Overview](#workflow-overview)
2. [Using the Extraction Script](#using-the-extraction-script)
3. [Concurrent Component Fetching](#concurrent-component-fetching)
4. [Placeholder Replacement](#placeholder-replacement)
5. [Critical Rules](#critical-rules)
6. [Checkpoint Gate](#checkpoint-gate)

---

## Workflow Overview

MasterGo designs contain two types of visual assets:

1. **Raster Images (Bitmaps)**: Backgrounds and photos stored as CDN URLs. Downloaded directly as `.png`.
2. **Vector Icons**: Drawn using shapes/paths. Converted to Android `VectorDrawable` XML for lossless scaling.

> [!IMPORTANT]
> **Project convention**: default app icons are expected to come from the shared WT widget library.
> If a placeholder corresponds to a canonical icon token such as `ic_all_account`, replace it with
> that shared drawable name first. Only generate a local VectorDrawable when no canonical shared
> drawable name can be derived.

### Key difference from v1

In v2, asset extraction is **manifest-driven**:
- `placeholder_manifest.json` (generated during Phase C) contains the precise list of icons that need extraction.
- The script does NOT use `width <= 64` heuristic for icon detection.
- Missing components are output as structured JSON, enabling concurrent fetching.

---

## Using the Extraction Script

Run the extraction script with the manifest:

```bash
# Primary extraction: manifest-driven, no 3rd-party libs required
python scripts/pipeline/extract_assets.py extract app/src/main/res/drawable/ mastergo_raw.json --manifest placeholder_manifest.json
```

The script will automatically parse JSON files passed as path arguments. Agents must not inspect those JSON files directly in chat/context.

The script will automatically:
1. Scan `mastergo_raw.json` for CDN image URLs and download them into the provided drawable output directory as `.png`.
2. Reuse shared widget-library icons directly when the canonical drawable token can be derived from the icon name.
3. Find remaining COMPONENT nodes listed in the manifest that have valid `path[].data`, generate local VectorDrawable XMLs into the provided drawable directory.
4. Output `missing_components.json` for any unresolved fallback icons whose component masters are not in the loaded JSONs.

---

## Concurrent Component Fetching

> [!IMPORTANT]
> **This is the critical improvement over v1.** In v1, missing components were fetched
> one-by-one in an iterative loop that exhausted context. In v2, they are fetched
> **concurrently in a single turn**.

When `extract_assets.py` generates `missing_components.json`, it contains:

```json
{
  "file_id": "190623756597653",
  "total_missing": 8,
  "missing": [
    {"name": "ic_all_delete", "component_id": "20:07975"},
    {"name": "ic_all_autorenew", "component_id": "4:5761"},
    ...
  ],
  "instruction": "Use scripts/pipeline/getdsl_to_file.py --file-id --layer-id for ALL items..."
}
```

**Action**:
1. Read `missing_components.json`.
2. In a **single shell step**, fetch ALL component IDs with `scripts/pipeline/getdsl_to_file.py`:
   ```
   python scripts/pipeline/getdsl_to_file.py comp_20_07975.json --file-id 190623756597653 --layer-id 20:07975 --skip-file-context
   python scripts/pipeline/getdsl_to_file.py comp_4_5761.json --file-id 190623756597653 --layer-id 4:5761 --skip-file-context
   python scripts/pipeline/getdsl_to_file.py comp_4_7835.json --file-id 190623756597653 --layer-id 4:7835 --skip-file-context
   ...
   ```
3. Save each result to `comp_<component_id>.json` (replace `:` with `_` in filename).
4. Re-run the extraction with all JSONs:
   ```bash
   python scripts/pipeline/extract_assets.py extract app/src/main/res/drawable/ mastergo_raw.json comp_*.json --manifest placeholder_manifest.json
   ```
5. Verify that `missing_components.json` is either gone or empty.

---

## Placeholder Replacement

After all icons are extracted, replace the placeholders in layout XMLs:

```bash
python scripts/pipeline/extract_assets.py replace app/src/main/res/layout/ placeholder_manifest.json
```

This replaces `@drawable/ph_icon_xxx` with the canonical shared drawable name when available
(for example `@drawable/ph_icon_all_ic_all_account` -> `@drawable/ic_all_account`).
If no canonical shared drawable token exists, the placeholder is replaced with the generated
local drawable filename.

---

## Critical Rules

These rules from `prompts/layout_android_xml.md` apply during asset processing:

- **Rule 9 (Native Resource Types)**: Only `.xml` for vectors, `.png` for bitmaps. Never `.svg`.
- **Rule 10 (Preserve Existing Resources)**: Never overwrite `colors.xml` -- always MERGE.
- **Rule 15 (No Composite Asset as Widget Background)**: Never use composite node snapshots as `android:background` on dynamic widgets.
- **Rule 23 (Icon Placeholder)**: All icon references use `@drawable/ph_icon_xxx` format until Phase D replacement.

---

## Checkpoint Gate

Before proceeding to Phase E, verify:

1. `extract_assets.py` reports **ZERO missing component masters**.
2. Bitmap assets exist in the target drawable directory as `.png` files when needed.
3. Vector fallback icons exist in the target drawable directory as `.xml` files when needed.
4. All `@drawable/ph_icon_xxx` placeholders have been replaced in layout XMLs.
5. `missing_components.json` is either absent or contains zero entries.

**PASS**: Proceed to Phase E (Text Calibration).
**FAIL**: Resolve missing components via direct-to-disk `scripts/pipeline/getdsl_to_file.py` fetch, then inspect with bounded `scripts/query/dsl_query.py` if needed, and re-run.
