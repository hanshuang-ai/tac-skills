# Android XML Layout Generation Rules (v3.0 - Three-Step)

> These rules MUST be followed during code generation.
> They are derived from real production bugs and LLM-specific failure patterns.
> Rules marked [LINT] are automatically verified by lint_layout.py after generation.

## Rule 1: Container Height [LINT]
- When a container (LinearLayout, FrameLayout, etc.) holds TEXT or dynamically sized children, use `android:layout_height="wrap_content"`.
- Fixed dp height ONLY for leaf nodes (standalone ImageView, divider View, solid color block).

## Rule 2: Horizontal Distribution
- NEVER use absolute x-position margins to distribute multiple items horizontally.
- Use `ConstraintLayout` horizontal chain (`spread` or `spread_inside`) with fixed child widths.
- Fixed `marginStart` is OK for single-axis positioning (e.g., left padding).

## Rule 3: LinearLayout Weight
- Do NOT use equal `layout_weight` when children have intentionally different sizes in the design.
- Use `ConstraintLayout` chain instead: each child keeps its design-specified width, chain distributes spacing.

## Rule 4: MaterialButton [LINT]
- NEVER use `<Button>` with `android:background` in MaterialComponents projects.
- Outlined: `MaterialButton` with `style="@style/Widget.MaterialComponents.Button.OutlinedButton"`
- Solid: `MaterialButton` with `app:backgroundTint="@color/..."`.
- Always set `android:insetTop="0dp"` and `android:insetBottom="0dp"`.

## Rule 5: Circular Images [LINT]
- `shapeAppearanceOverlay` only works on `ShapeableImageView`, NOT plain `ImageView`.
- For circular avatars (MasterGo SVG_ELLIPSE with image fill):
  ```xml
  <com.google.android.material.imageview.ShapeableImageView
      app:shapeAppearanceOverlay="@style/CircleImageView" />
  ```

## Rule 6: Custom Fonts
- Non-system fonts require a bundled `.ttf` in `res/font/`.
- File names: lowercase, alphanumeric, underscores only.
- Reference: `android:fontFamily="@font/font_name"`.

## Rule 7: Dynamic Lists [LINT]
- For repeating elements (lists, grids, carousels), NEVER hardcode all items or download as a single image.
- Implement a single reusable item layout + `RecyclerView` (or other dynamic container).
- Generate the Adapter class + data model + dummy data.
- Resolve list geometry from the blueprint first:
  - If `list_metrics_ref` is non-null, it MUST match an exact `structural_hints.json.list_metrics[].container_id`; use that entry as the list geometry contract.
  - If `list_metrics_ref` is null, use `list_metrics_override` only when it contains `source: "dsl_manual"` and explicit coordinate evidence.
  - Item layout width/height MUST equal `item_width` / `item_height`.
  - Sibling gap MUST be implemented on the list/container layer (`RecyclerView.ItemDecoration`, item margins, or parent spacing), not by increasing item layout height/width.
  - `item_pitch` = item size + `item_gap`; do not confuse pitch with item size.
  - If `divider.kind = bottom_stroke`, render the divider inside the item at the item bottom and keep the following `item_gap` outside the item.

## Rule 8: Accessibility
- All `ImageView` and icon elements MUST have `android:contentDescription` or `android:importantForAccessibility="no"` (for decorative images).
- All clickable elements must have minimum 48dp x 48dp touch target.

## Rule 9: No Raw SVG -- Use PNG Only
- Android `res/` directories only accept `.xml`, `.png`, `.jpg`, `.gif`, `.9.png`.
- All bitmap assets default to **PNG** export. Never use `.svg` in resource directories.
- Before downloading, check for existing equivalent drawables and reuse them.

## Rule 10: Preserve Existing Resource Files
- Never overwrite `colors.xml`, `dimens.xml`, or `text_appearances.xml` wholesale. 
- Always MERGE new tokens from the generated `*_patch.xml` files with existing entries.
- Existing attribute entries in the project take precedence over newly extracted values from the design.
- After pipeline execution, verify theme colors and previous styling are still present.
- Generated patch artifacts stay outside the Android `res/` tree until they are selectively merged. Never create ad-hoc files such as `app/src/main/res/text_appearances.xml`.

---


## Rule 11: Semantic Resource Key Names
- Do NOT use raw auto-generated keys like `fill_Frame_123_0` in final layout XML.
- Rename all resource references to semantic names during code generation:
  - Background: `bg_{context}` (e.g., `bg_card_primary`)
  - Text color: `text_{context}` (e.g., `text_title`)
  - Stroke: `stroke_{context}` (e.g., `stroke_divider`)
  - Radius: `radius_{size}` (e.g., `radius_small`)
  - Spacing: `spacing_{context}` (e.g., `spacing_list_item`)
- Update `colors.xml` / `dimens.xml` entries to match the renamed keys.

## Rule 12: Container Selection Priority [LINT]
- Single child or overlay -> `FrameLayout`
- Simple row/column -> `LinearLayout`
- Complex relative positioning -> `ConstraintLayout`
- **Never use ConstraintLayout for 0-1 children** -- lint will flag this.

## Rule 13: Overdraw Prevention [LINT]
- Do NOT set `android:background` on both a parent ViewGroup AND its direct child.
- Remove the parent background if the child fully covers it.
- Lint will flag parent-child pairs that both define `android:background`.

## Rule 14: View Hierarchy Depth Limit [LINT]
- Maximum **5 levels** of nesting depth for AI-generated layouts.
- If depth exceeds the limit, flatten with `ConstraintLayout` or extract via `<include>`.
- Lint will flag layouts deeper than 5 levels.

## Rule 15: Never Use Composite Asset as Widget Background
- MasterGo components (e.g., Tab Bar, Toolbar) may be exported as a single PNG with pre-rendered icons/text baked in. Using this as `android:background` on a widget that also self-renders content causes **duplicate elements**.
- **Detection**: Check if the source node **contains child nodes** (icons, text, shapes). If yes, it's a composite snapshot, not a pure background.
- `BottomNavigationView`, `TabLayout`, `Toolbar`, `NavigationView` -> NEVER use composite PNGs as background.

---

## Rule 16: Query Scripts as Sole Access Path for Queryable Artifacts

- Do **NOT** call chat/MCP getDsl during rendering and do **NOT** read `mastergo_raw.json` directly.
- Query the cached DSL with bounded script output for each component:
  `python scripts/query/dsl_query.py node <work_dir>/mastergo_raw.json --node-id <nodeId> --depth 1 --max-children 20`
- Do **NOT** read `semantic_mapping.json` directly. Query semantic hints for the specific node IDs being rendered:
  `python scripts/query/query_semantic_mapping.py --mapping <work_dir>/semantic_mapping.json <nodeId> ...`
- Do **NOT** read `widget_registry.snapshot.json` directly. Query widget/text/color registry evidence with `scripts/query/query_widget_registry.py`.
- Increase `--depth` only for the current component being generated. Keep `--max-children` explicit. Use `--include-path-data` or `--include-urls` only for a specific asset/path node.
- **Data source hierarchy**:
  1. Bounded `scripts/query/dsl_query.py` output from cached DSL files -> **PRIMARY** (all structural/style properties)
  2. Bounded `scripts/query/query_semantic_mapping.py` output -> **SECONDARY** (widget/attr/text/color hints only)
  3. `token_registry.json` -> **TERTIARY** (semantic resource name lookup)
  4. Intermediate artifacts/prose notes -> **NEVER** used as geometry ground truth

- **Style resolution**: MasterGo DSL uses a `styles` dict with keyed entries:
  - `paint_*`: Colors, gradients, image URLs. Resolve via `dsl.styles["paint_xxx"].value`
  - `font_*`: Typography. Resolve via `dsl.styles["font_xxx"].value`
  - `effect_*`: Shadows, blurs. Resolve via `dsl.styles["effect_xxx"].value`

## Rule 17: Spacing from Coordinates -- Never Guess Margins/Paddings
- LLMs tend to fill margins and paddings with arbitrary "comfortable" values (16dp, 8dp). This is the #1 cause of layout inaccuracy.
- **Rule**:
  1. Always consult `layout_spacing` for spacing values.
  1a. For repeated lists, consult `list_metrics` first. It is the authoritative source for `item_width`, `item_height`, `item_pitch`, `item_gap`, and divider ownership.
  2. If missing, compute manually from DSL:
     - Parent padding-left = `first_child.relativeX`
     - Sibling gap = `next_sibling.relativeX - (prev_sibling.relativeX + prev_sibling.width)`
  3. **Never use hardcoded fallback values** (16dp, 8dp, etc.).
  4. **Never absorb sibling gap into item dimensions.** If DSL says `item_height=160` and the next item starts at `y=336` from a `y=136` item, generate a 160dp item and a 40dp list gap, not a 200dp item.

## Rule 18: Dimension Precision -- Never Guess Component Heights/Widths
- For any fixed-size element, retrieve exact dimensions from the DSL sub-tree data.
- Never "eyeball" or use typical default sizes.

## Rule 19: Recursive Parent Constraint Passing
- During recursive top-down generation, each child layout MUST receive its **parent constraint**:
  ```
  parent_constraint:
    container_type: LinearLayout
    orientation: vertical
    allocated_width: match_parent
    allocated_height: 676dp
    position_in_parent: 2
  ```
- The child layout MUST NOT assume a different parent container type than what is declared.

## Rule 20: VectorDrawable from PATH Data
- MasterGo PATH nodes contain `path.data` using standard SVG path syntax (M, L, Q, C, Z commands).
- This syntax is **directly compatible** with Android `android:pathData`.
- For icon-sized PATH nodes, convert to VectorDrawable XML.
- Resolve the fill color from the PATH node's `path[].fill` paint reference.

## Rule 21: Low-Priority Field Handling
- The following DSL fields are **not geometry truth** for Android code generation:
- `componentInfo`: semantic metadata only; use it for widget selection, never for size or position
- `componentId`: design tool internal reference. It is used for icon fetching in Phase D, and it is also a valid semantic fallback key when an INSTANCE node lacks enough local widget metadata but its component master carries WT widget semantics.
  - `textMode`: Redundant with `android:maxLines`
  - `strokeType`: Always "solid" in practice
  - `mask`: Rendering clip hint, no Android equivalent
- If `scripts/query/query_semantic_mapping.py` output provides `resolvedWidget`, `attrs`, or text/color resource hints, consume them first.
- If `scripts/query/query_semantic_mapping.py` output marks an item as `unresolved`, fall back to normal View or patch logic instead of inventing a control-library mapping.

## Rule 21A: Matched Widgets Keep Library Default Appearance
- If `scripts/query/query_semantic_mapping.py` output resolves a WT widget, generate it and keep its default visual styling (background, corners, built-in text styling).
- Do **NOT** re-apply widget-owned styling from DSL unless explicit `attrs` overrides dictate it.
- **Size Exception**: `layout_width`, `layout_height`, `minWidth`, and `minHeight` must ALWAYS come from DSL geometry, never from widget defaults.
- Apply DSL properties for layout positioning, placeholders, and missing visuals. Mark `[UNRESOLVED: widget style gap]` if needed.
- If INSTANCE lacks semantics but component master resolves to WT widget (via `componentId`), render the WT widget. Do NOT downgrade to `MaterialButton` or generic composition.

## Rule 21B: Reusable Layouts Reuse Structure, Not Instance Size
- For `reusable: true`, `template_id`, or `reuse_template` nodes: Reuse the layout FILE only.
- Resolve each instance's dimensions from its **own** `layoutStyle`. Never let a template or widget default size override concrete instance geometry.

---

## Rule 22: Text Placeholder Rule (NEW in v3.0)

> [!IMPORTANT]
> **All text content from DSL is UNRELIABLE.** MasterGo getDsl API returns component library
> defaults (e.g., "Primary Text", "标题文字", "小按钮") instead of the designer's actual typed text.

- **For ALL `TEXT` nodes**, set `android:text="{{TEXT:<node_id>}}"` as a placeholder.
- Add an XML comment with the DSL's default value for reference:
  ```xml
  <!-- DSL default: "Primary Text" | font: font_4:893 | color: paint_4:858 -->
  <TextView
      android:id="@+id/tv_app_name"
      android:text="{{TEXT:22:38587/63:27036}}"
      android:textSize="20sp"
      android:textColor="@color/text_title" />
  ```
- **Typography attributes** (textSize, textColor, fontFamily, lineHeight) are resolved from DSL normally -- only the text STRING is unreliable.
- If queried semantic mapping output has `text.styleRef` and `text.ownership.kind = direct_text`, apply `style="@style/..."` on the generated `TextView` and do **NOT** restate `textSize`, `textStyle`, `lineSpacingExtra`, or `fontFamily` manually.
- If that `styleRef` resolves to a shared WT text style such as `@style/WTTextStyle...`, reuse it directly and do **NOT** generate or merge a same-metrics local text appearance entry for that text node.
- If queried semantic mapping output has `text.color.ref`, ALWAYS apply that DSL-derived text color even when `styleRef` is also present. `styleRef` never authorizes dropping DSL text color.
- If queried semantic mapping output has `text.color.value` but `text.color.ref` does not, use that exact hex value as the fallback text color instead of silently reverting to a library default.
- Prefer the structured queried semantic `text.color.*` fields. For older artifacts that only contain legacy `text.colorRef` / `text.colorValue`, treat them as equivalent fallbacks.
- If queried semantic mapping output has `text.ownership.kind = widget_attr` and `preferredAttr` exists, write that attr on the matched WT widget instead of styling a child `TextView`.
- If queried semantic mapping output has `text.color.ownership.kind = widget_attr` and `preferredAttr` exists, write the DSL-derived color to that widget attr instead of dropping it.
- If queried semantic mapping output has `text.ownership.kind = widget_default`, do **NOT** generate or restyle the widget's internal `TEXT` descendant. Keep the widget's library-default text appearance.
- If queried semantic mapping output has `text.color.ownership.kind = widget_default` and no writable widget color attr exists, keep the DSL color visible in comments and mark `[UNRESOLVED: widget text color gap]` rather than silently assuming the default widget color is correct.
- If queried semantic mapping output has `text.conflicts`, trust `TEXT.text[].font` / `TEXT.textColor[]` over `TEXT.name` and keep the conflict note visible in comments rather than guessing.
- Record every text placeholder in `placeholder_manifest.json`.

## Rule 22A: Text Color Context Conflict Guard

DSL text color is the default style source, but do not let a contextless or placeholder-looking text node override a verified existing visual context.

- Before changing text or icon colors in an existing layout, inspect the current XML color, the nearest visible background/surface, and the available design scope.
- Treat text color as **context-conflicted** when all of these are true:
  1. The design input is a partial subtree or component snippet without the surrounding page background.
  2. The DSL text value is a component default such as `Primary Text`, `标题文字`, `小按钮`, or similarly generic placeholder copy.
  3. The DSL-derived color would flip contrast direction against the current implementation (for example black text/icon on a known dark page, or white text/icon on a known light page).
  4. No design screenshot, full-page DSL, or explicit user instruction confirms the color flip.
- In a context-conflicted case, preserve the existing explicit text/icon color and apply only the reliable typography metrics (`styleRef`, size, weight, lineHeight). Add an XML comment with the DSL color evidence and `[UNRESOLVED: text color context conflict]`.
- If a screenshot, full-page DSL background, or user instruction confirms the DSL color, apply the DSL color and document that evidence in the comment.
- This guard only handles contrast/context conflicts. It does not weaken Rule 22's normal requirement to propagate DSL text color when the page context is available or not contradictory.

## Rule 23: Icon Placeholder Rule (NEW in v3.0)

> [!IMPORTANT]
> **Default convention: app icons come from the shared WT widget library.**
> If the DSL icon name exposes a canonical token such as `ic_all_account`, Phase D should
> replace the placeholder with that shared drawable first. Separate extraction is only the
> fallback for icons that do not map to a canonical shared-library drawable.

- For all icon references (INSTANCE nodes identified as icons in the blueprint or render plan), use:
  ```xml
  <ImageView
      android:src="@drawable/ph_icon_<sanitized_name>"
      android:layout_width="56dp"
      android:layout_height="56dp" />
  ```
- **Dimensions** (width, height) are resolved from DSL normally -- only the drawable reference is a placeholder.
- Record every icon placeholder in `placeholder_manifest.json` with its `componentId`.
- When the icon name contains a canonical `ic_...` token, Phase D should replace the placeholder with that exact shared drawable name (for example `All/ic_all_account` -> `@drawable/ic_all_account`).
- Only when no canonical shared-library drawable can be derived should Phase D fetch/generate a local drawable fallback.
- **NEVER** substitute a different icon just because it already exists locally.

---

## Rule 24: System Chrome Exclusion and Coordinate Normalization (R-SYS-OFFSET)

> [!WARNING]
> Top/bottom shell chrome is usually context, not target UI. Only render nodes approved by the blueprint.

- **Skip Excluded Nodes**: Do NOT generate XML for any node marked `type: system_component` and `exclude_from_layout: true` in the blueprint, unless the user explicitly requested a full-shell screen.
- **Normalize Root Coordinates**: Read `recursive_blueprint.json.coordinate_normalization` for excluded insets and prefer machine-readable blueprint bounds over prose notes.
  - For depth-0 renderable nodes, use `node.bounds.normalized.x/y/width/height` directly.
  - If normalized bounds are unavailable, compute `normalized_x = node.bounds.raw.x - left_inset` and `normalized_y = node.bounds.raw.y - top_inset`; treat missing bounds as a preflight failure.
- **Honor Blueprint Coordinate Space**: For depth-0 renderable nodes marked `coordinate_space: "root_normalized"`, never write raw DSL `relativeX` / `relativeY` directly into XML margins. Use `bounds.normalized` or compute from `bounds.raw` minus the matching inset.
- **Descendants Stay Parent-Relative**: For child nodes marked `coordinate_space: "parent_relative"` or omitted because they are below a normalized root node, use `node.bounds.parent_relative`. Do not subtract root chrome insets again.
- **No Double-Subtract**: Compensate once at the first renderable root level. Descendants inherit the normalized coordinate space.
- **Document**: Annotate normalized margins in XML comments: `<!-- original=Xdp minus Ydp excluded_system_chrome -->`

## Rule 25: Text Container Width Safety (R-TEXT-SIZING)

> [!WARNING]
> **DSL text width is a measurement, not a constraint.** Font engine differences between
> MasterGo and Android cause 1-3dp variance, breaking fixed-width single-line text.

- **Single-line short text** (titles, labels, buttons): Use `wrap_content` width
- **Multi-line text** (descriptions, comments): Use `match_parent` or `0dp` with constraints
- **Fixed-width text**: Only when design intends clipping; add `ellipsize="end"` + `singleLine="true"`
- **Buttons**: Always `wrap_content` with padding for text content
- **Container propagation**: When a child uses `wrap_content`, ALL ancestor containers in that axis
  must ALSO use `wrap_content` or `match_parent`. A fixed-dp parent silently clips `wrap_content` children.
  - Bug example: TextView `wrap_content` inside LinearLayout fixed 270dp -> child clipped at 174dp -> wraps
- **Last-in-chain text blocks**: For the last multiline text in a ConstraintLayout, use `0dp` height +
  `constraintBottom_toBottomOf="parent"` instead of fixed dp height. DSL height is a measurement, not a clip constraint.
- Example bug: "应用推荐" at 44sp needs ~176dp; DSL reports 174dp -> 2dp shortfall causes wrapping

---

> REMINDER: After generating the layout, lint_layout.py will automatically check Rules 1, 4, 5, 7, 12, 13, and 14.
> Fix any violations before finalizing. Maximum 2 lint-fix iterations allowed.
> Rules 9, 10, 11, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, and 25 must be checked MANUALLY before build verification.
