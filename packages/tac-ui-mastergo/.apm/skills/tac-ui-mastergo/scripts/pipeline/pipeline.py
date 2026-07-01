"""
MasterGo Pipeline Orchestrator (v3.0 - Three-Step Architecture)

Orchestrates preprocessing steps with graceful degradation.
Asset scanning is deferred to Phase D (manifest-driven extract_assets.py).
Semantic mapping is resolved into a single `semantic_mapping.json` artifact.

Pipeline steps:
1. extract_skeleton        -> skeleton_tree.json
2. extract_tokens          -> token_registry.json + Android XML resources
3. extract_semantic_mapping -> widget_registry.json + semantic_mapping.json
4. analyze_structure       -> structural_hints.json

Changes from v2.3:
- Removed scan_assets step (asset identification now driven by placeholder_manifest.json in Phase D)
- Pipeline produces only structural/style artifacts, no asset registry

Usage:
    python pipeline.py <input_mastergo.json> <output_dir> <android_res_dir>
"""

import json
import logging
import os
import shutil
import sys
import time
import re
from pathlib import Path

DEFAULT_WIDGET_ROOT = os.environ.get("WT_WIDGET_ROOT", r"D:\code\WT02_Widget")
DEFAULT_REFERENCES_DIR = Path(__file__).resolve().parent.parent.parent / "references"
DEFAULT_WIDGET_REGISTRY_SNAPSHOT = (
    DEFAULT_REFERENCES_DIR / "widget_registry.snapshot.json"
)

# Add pipeline and parent scripts dir to path for imports
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)


def _prepare_widget_registry(
    output_dir: str,
    widget_root: str,
    widget_registry_snapshot: str = "",
    rebuild_widget_registry: bool = False,
    library: str = "",
    project_root: str | Path | None = None,
) -> tuple[str, dict]:
    """Prepare widget_registry for semantic mapping.

    Return the resolved path to the checked-in snapshot (references/widget_registry.snapshot.json
    inside the skill) instead of copying it into the case/handoff directory.
    If rebuild_widget_registry is True, rebuild directly to the snapshot path.
    """
    config_path = DEFAULT_REFERENCES_DIR / "library_config.json"
    legacy_env_snapshot = os.environ.get("WT_WIDGET_REGISTRY_SNAPSHOT") if not config_path.exists() else ""
    explicit_snapshot = widget_registry_snapshot or legacy_env_snapshot
    if explicit_snapshot and not library:
        snapshot_path = Path(explicit_snapshot)
        if not rebuild_widget_registry and snapshot_path.exists():
            return str(snapshot_path.resolve()), {
                "source": "snapshot",
                "snapshotPath": str(snapshot_path.resolve()),
            }

        from build_widget_registry import build_widget_registry

        build_widget_registry(widget_root=widget_root, output_path=str(snapshot_path))
        return str(snapshot_path.resolve()), {
            "source": "live_build",
            "widgetRoot": widget_root,
            "snapshotPath": str(snapshot_path.resolve()),
        }

    if library or not explicit_snapshot:
        from build_widget_registry import _load_provider, _provider_dir, build_registry_for_provider

        provider = _load_provider(library or None)
        registry = build_registry_for_provider(
            provider,
            Path(project_root or Path.cwd()),
            refresh=rebuild_widget_registry,
        )
        library_dir = _provider_dir(provider)
        library_snapshot_path = library_dir / provider.get("snapshotFile", "widget_registry.snapshot.json")
        snapshot_path = DEFAULT_WIDGET_REGISTRY_SNAPSHOT
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        if library_snapshot_path.resolve() != snapshot_path.resolve():
            shutil.copy2(library_snapshot_path, snapshot_path)
        return str(snapshot_path.resolve()), {
            "source": "provider",
            "libraryId": registry.get("meta", {}).get("libraryId", provider.get("libraryId")),
            "providerPath": provider.get("_providerPath"),
            "librarySnapshotPath": str(library_snapshot_path.resolve()),
            "snapshotPath": str(snapshot_path.resolve()),
        }


def _write_json(data: dict, path: str) -> None:
    """Write dict to JSON file, creating directories as needed."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _parse_file_id_from_url(url: str) -> str:
    """Extract fileId from a MasterGo redirect URL.
    
    Example URL:
      https://uxd.tinnove.com.cn/file/141979230296189?devMode=true&file=141979230296189&...
    
    Returns:
        fileId string, or empty string if not found.
    """
    # Try 'file=' parameter first
    match = re.search(r'[?&]file=(\d+)', url)
    if match:
        return match.group(1)
    # Try path segment /file/<id>
    match = re.search(r'/file/(\d+)', url)
    if match:
        return match.group(1)
    return ""


def _parse_layer_id_from_url(url: str) -> str:
    """Extract layerId from a MasterGo redirect URL.
    
    Example: ...&layer_id=22%3A34698&...
    """
    match = re.search(r'[?&]layer_id=([^&]+)', url)
    if match:
        from urllib.parse import unquote
        return unquote(match.group(1))
    return ""


def run_pipeline(
    input_path: str,
    output_dir: str,
    res_dir: str,
    short_link: str = "",
    widget_root: str = DEFAULT_WIDGET_ROOT,
    widget_registry_snapshot: str = "",
    rebuild_widget_registry: bool = False,
    library: str = "",
    project_root: str | Path | None = None,
) -> dict:
    """Execute the full preprocessing pipeline.

    Args:
        input_path: Path to raw MasterGo DSL JSON file (saved direct-to-disk by getdsl_to_file.py).
        output_dir: Directory for intermediate artifacts.
        res_dir: Android res/values/ directory for generated XML resources.
        short_link: Optional MasterGo short link for fileId extraction.

    Returns:
        Pipeline result dict with status, artifact paths, and any warnings.
    """
    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)

    result = {
        "status": "SUCCESS",
        "artifacts": {},
        "warnings": [],
        "errors": [],
        "timing": {},
    }

    # Try to load existing file_context from pipeline_result.json if it exists
    existing_res_path = os.path.join(output_dir, "pipeline_result.json")
    if os.path.exists(existing_res_path):
        try:
            with open(existing_res_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if "file_context" in existing_data:
                    result["file_context"] = existing_data["file_context"]
        except Exception:
            pass

    # -------------------------------------------------------------------
    # Step 0: Parse fileId from short link (if provided)
    # -------------------------------------------------------------------
    if short_link:
        logger.info("Step 0: Parsing fileId from short link...")
        try:
            import urllib.request
            response = urllib.request.urlopen(short_link)
            redirect_url = response.url
            file_id = _parse_file_id_from_url(redirect_url)
            layer_id = _parse_layer_id_from_url(redirect_url)

            file_context = {
                "fileId": file_id,
                "rootLayerId": layer_id,
                "redirectUrl": redirect_url,
                "shortLink": short_link,
            }
            result["file_context"] = file_context

            logger.info("  fileId=%s, rootLayerId=%s", file_id, layer_id)
        except Exception as e:
            logger.warning("fileId parsing failed (non-fatal): %s", e)
            result["warnings"].append(f"fileId parsing failed: {e}")

    # -------------------------------------------------------------------
    # Step 1: Extract Skeleton -> skeleton_tree.json
    # CRITICAL: If this fails, we DEGRADE
    # -------------------------------------------------------------------
    logger.info("Step 1/3: Extracting skeleton tree...")
    step_start = time.time()
    try:
        from extract_skeleton import extract_skeleton

        skeleton_result = extract_skeleton(input_path)
        skeleton_path = os.path.join(output_dir, "skeleton_tree.json")
        _write_json(skeleton_result, skeleton_path)
        result["artifacts"]["skeleton_tree"] = skeleton_path

        metadata = skeleton_result.get("metadata", {})
        logger.info(
            "  Extracted skeleton: %d nodes, %.1f%% compression",
            metadata.get("total_nodes", 0),
            metadata.get("compression_percent", 0),
        )
        result["timing"]["extract_skeleton"] = round(time.time() - step_start, 2)

    except Exception as e:
        logger.error("Step 1 FAILED: skeleton extraction error: %s", e)
        result["status"] = "DEGRADED"
        result["errors"].append(f"skeleton extraction failed: {e}")
        result["warnings"].append(
            "Skeleton extraction failed -- LLM must analyze raw MasterGo DSL directly. "
            "This is the fallback mode with larger context."
        )
        result["timing"]["total"] = round(time.time() - start_time, 2)
        return result

    # -------------------------------------------------------------------
    # Step 2: Extract design tokens -> token_registry.json + Android XMLs
    # Non-fatal
    # -------------------------------------------------------------------
    logger.info("Step 2/3: Extracting design tokens...")
    step_start = time.time()
    try:
        from extract_tokens import extract_all_tokens

        token_registry = extract_all_tokens(input_path, res_dir)
        token_path = os.path.join(output_dir, "token_registry.json")
        _write_json(token_registry, token_path)
        result["artifacts"]["token_registry"] = token_path

        summary = token_registry.get("summary", {})
        logger.info(
            "  Extracted %d colors, %d text styles, %d dimensions",
            summary.get("color_count", 0),
            summary.get("type_count", 0),
            summary.get("dimen_count", 0),
        )
        result["timing"]["extract_tokens"] = round(time.time() - step_start, 2)

    except Exception as e:
        logger.warning("Step 2 partial failure (non-fatal): %s", e)
        result["warnings"].append(f"Token extraction failed: {e}")
        result["timing"]["extract_tokens"] = round(time.time() - step_start, 2)

    # -------------------------------------------------------------------
    # Step 3: Prepare registry + semantic mapping -> semantic_mapping.json
    # Non-fatal.
    # -------------------------------------------------------------------
    logger.info("Step 3/4: Extracting semantic mappings...")
    step_start = time.time()
    try:
        from extract_semantic_mapping import extract_semantic_mapping

        semantic_path = os.path.join(output_dir, "semantic_mapping.json")
        registry_path, registry_meta = _prepare_widget_registry(
            output_dir=output_dir,
            widget_root=widget_root,
            widget_registry_snapshot=widget_registry_snapshot,
            rebuild_widget_registry=rebuild_widget_registry,
            library=library,
            project_root=project_root,
        )
        extract_semantic_mapping(input_path, registry_path, semantic_path)

        result["artifacts"]["semantic_mapping"] = semantic_path
        result["widget_registry"] = registry_meta
        logger.info("  Widget registry source: %s", registry_meta["source"])
        result["timing"]["extract_semantic_mapping"] = round(time.time() - step_start, 2)

    except Exception as e:
        logger.warning("Step 3 partial failure (non-fatal): %s", e)
        result["warnings"].append(f"Semantic mapping failed: {e}")
        result["timing"]["extract_semantic_mapping"] = round(time.time() - step_start, 2)

    # -------------------------------------------------------------------
    # Step 4: Analyze structure -> structural_hints.json
    # Non-fatal. Asset scanning is deferred to Phase D (manifest-driven).
    # -------------------------------------------------------------------
    logger.info("Step 4/4: Analyzing structure...")
    step_start = time.time()
    try:
        from analyze_structure import analyze_structure

        # Use raw DSL so spacing/list metrics keep exact relative positions.
        # The analyzer normalizes the MasterGo tree internally.
        with open(input_path, "r", encoding="utf-8") as f:
            raw_tree = json.load(f)
        hints = analyze_structure(raw_tree)
        hints_path = os.path.join(output_dir, "structural_hints.json")
        _write_json(hints, hints_path)
        result["artifacts"]["structural_hints"] = hints_path

        logger.info(
            "  Detected %d repeating groups, %d anchors, %d clusters, %d scroll candidates, %d list metrics",
            len(hints.get("repeating_groups", [])),
            len(hints.get("positional_anchors", [])),
            len(hints.get("size_clusters", [])),
            len(hints.get("scroll_candidates", [])),
            len(hints.get("list_metrics", [])),
        )
        result["timing"]["analyze_structure"] = round(time.time() - step_start, 2)

    except Exception as e:
        logger.warning("Step 4 partial failure (non-fatal): %s", e)
        result["warnings"].append(f"Structure analysis failed: {e}")
        result["timing"]["analyze_structure"] = round(time.time() - step_start, 2)

    # -------------------------------------------------------------------
    # Final summary
    # -------------------------------------------------------------------
    result["timing"]["total"] = round(time.time() - start_time, 2)

    if result["warnings"]:
        logger.warning("Pipeline completed with %d warnings", len(result["warnings"]))
    else:
        logger.info("Pipeline completed successfully in %.2fs", result["timing"]["total"])

    return result


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 4:
        print(
            "Usage: python pipeline.py <input_mastergo.json> <output_dir> <android_res_dir> "
            "[--short-link URL] [--widget-root PATH] "
            "[--widget-registry-snapshot PATH] [--rebuild-widget-registry] "
            "[--library LIBRARY] [--project-root PATH]"
        )
        print()
        print("Arguments:")
        print("  input_mastergo  Path to raw MasterGo DSL data file (JSON)")
        print("  output_dir      Directory for pipeline intermediate artifacts")
        print("  android_res_dir Android res/values/ directory for XML resources")
        print("  --short-link    Optional MasterGo short link for fileId extraction")
        print("  --widget-root   WT02 widget repository root (used only when rebuilding registry)")
        print("  --widget-registry-snapshot  Prebuilt registry snapshot to copy into the case directory")
        print("  --rebuild-widget-registry   Force a live rebuild instead of using the snapshot")
        print("  --library       Registered library id from references/library_config.json")
        print("  --project-root  Android project root used to discover Gradle AAR cache")
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    res_dir = sys.argv[3]
    short_link = ""

    widget_root = DEFAULT_WIDGET_ROOT
    widget_registry_snapshot = ""
    rebuild_widget_registry = False
    library = ""
    project_root = str(Path.cwd())

    # Parse optional arguments
    for i, arg in enumerate(sys.argv):
        if arg == "--short-link" and i + 1 < len(sys.argv):
            short_link = sys.argv[i + 1]
        if arg == "--widget-root" and i + 1 < len(sys.argv):
            widget_root = sys.argv[i + 1]
        if arg == "--widget-registry-snapshot" and i + 1 < len(sys.argv):
            widget_registry_snapshot = sys.argv[i + 1]
        if arg == "--rebuild-widget-registry":
            rebuild_widget_registry = True
        if arg == "--library" and i + 1 < len(sys.argv):
            library = sys.argv[i + 1]
        if arg == "--project-root" and i + 1 < len(sys.argv):
            project_root = sys.argv[i + 1]

    result = run_pipeline(
        input_path,
        output_dir,
        res_dir,
        short_link,
        widget_root,
        widget_registry_snapshot,
        rebuild_widget_registry,
        library,
        project_root,
    )

    # Write pipeline result
    result_path = os.path.join(output_dir, "pipeline_result.json")
    _write_json(result, result_path)

    # Print summary to stdout
    print(json.dumps(result, indent=2))

    # Exit code: 0 for SUCCESS, 1 for DEGRADED
    sys.exit(0 if result["status"] == "SUCCESS" else 1)


if __name__ == "__main__":
    main()
