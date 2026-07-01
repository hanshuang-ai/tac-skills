# MasterGo DSL Schema Reference

> This is a **lookup table** -- load it when you encounter unfamiliar DSL properties.
> Referenced from `01_data_acquisition.md`, `02_asset_processing.md`, and `04_codegen_rules.md`.

## Table of Contents

1. [Unit Mapping](#unit-mapping)
2. [Style Reference System](#style-reference-system)
3. [Node Property to Android XML Mapping](#node-property-to-android-xml-mapping)
4. [Skeleton Field Abbreviations](#skeleton-field-abbreviations)
5. [Noise Fields (Ignore List)](#noise-fields-ignore-list)

---

## Unit Mapping

**1:1 Unit Mapping**: MasterGo DSL dimensions are in px. Map directly to dp at 1:1 ratio.

```
1 MasterGo px = 1 Android dp
```

---

## Style Reference System

MasterGo DSL uses a `styles` dict with keyed entries. Nodes reference styles via string keys:

| Prefix | Content | Example Key | Example Value |
|:---|:---|:---|:---|
| `paint_*` | Colors, gradients, images | `paint_4:709` | `{value: ["#7A4CD6"], token: "..."}` |
| `font_*` | Typography definitions | `font_4:880` | `{value: {family, size, lineHeight, ...}, token: "..."}` |
| `effect_*` | Shadows, blurs | `effect_4:918` | `{value: ["box-shadow: ..."], token: "..."}` |

### Resolving a Style Reference

1. Read the style key from the node property (e.g., `fill: "paint_4:709"`)
2. Look up `dsl.styles["paint_4:709"]`
3. Read `.value` for the actual data
4. Optionally read `.token` for the design token name

---

## Node Property to Android XML Mapping

| MasterGo Property | Android XML Attribute | Mapping Logic |
|:---|:---|:---|
| `layoutStyle.width` | `android:layout_width` | `width`dp (1:1 mapping) |
| `layoutStyle.height` | `android:layout_height` | `height`dp or `wrap_content` (Rule 1) |
| `layoutStyle.relativeX` | `android:layout_marginStart` | Relative to parent |
| `layoutStyle.relativeY` | `android:layout_marginTop` | Relative to parent |
| `fill` (paint ref -> solid) | `android:background` | `@color/fill_ID` from token registry |
| `fill` (paint ref -> gradient) | `android:background` | `@drawable/gradient_ID` |
| `fill` (paint ref -> image) | `android:src` or background | Download PNG from URL |
| `text[].text` | `android:text` | Raw string or `@string` resource |
| `text[].font` (font ref) | `android:fontFamily` | `@font/font_name` (Rule 6) |
| Font `size` | `android:textSize` | `Xsp` |
| Font weight (inferred) | `android:textFontWeight` | Integer weight from family suffix |
| Font `lineHeight` | `android:lineSpacingExtra` | `lineHeight - fontSize` dp |
| Font `letterSpacing` | `android:letterSpacing` | `letterSpacing / fontSize` em |
| `textColor[].color` (paint ref) | `android:textColor` | Resolve paint ref -> hex |
| `borderRadius` | `app:cornerRadius` or shape drawable | Parse px value -> `Xdp` |
| `effect` (effect ref -> shadow) | `android:elevation` | `Xdp` |
| `strokeColor` / `strokeWidth` | `app:strokeColor` / `app:strokeWidth` | Resolve paint + parse px |
| `opacity` | `android:alpha` | `0.0` to `1.0` |
| `flexContainerInfo` | Layout type hint | `flexDirection: row` -> horizontal layout |
| `path[].data` | VectorDrawable `android:pathData` | Direct SVG path syntax (Rule 20) |

---

## Skeleton Field Abbreviations

The skeleton (from `extract_skeleton.py`) uses abbreviated field names for compression:

| Skeleton Field | Full Name | Description |
|:---|:---|:---|
| `t` | type | `F`=FRAME, `G`=GROUP, `I`=INSTANCE, `T`=TEXT, `P`=PATH, `E`=SVG_ELLIPSE, `L`=LAYER |
| `n` | name | Layer name (truncated to 20 chars) |
| `w`, `h` | width, height | Dimensions in px (integer) |
| `lt` | leaf_type | `IMAGE`, `TEXT`, `ICON`, `SHAPE` (leaf nodes only) |
| `ol` | has_overlap | `true` if children overlap (guides ViewGroup selection) |
| `cid` | componentId | Component ID (INSTANCE nodes only, for homogeneous detection) |
| `cc` | children_count | Descendant count (INSTANCE nodes only, internals collapsed) |
| `ch` | children | Child nodes array (non-INSTANCE nodes with children) |

---

## Noise Fields (Ignore List)

These DSL fields are **not useful** for Android code generation. Do not attempt to map them:

| Field | Reason to Ignore |
|:---|:---|
| `componentInfo` | Design tool variant metadata (e.g., `"属性1": "浅色"`) |
| `componentId` | Used only for homogeneous detection in blueprint phase |
| `textMode` | Redundant with `android:maxLines` |
| `strokeType` | Always "solid" in practice |
| `mask` | Rendering clip hint, no Android equivalent |
