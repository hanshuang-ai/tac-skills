#!/usr/bin/env python3
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add a Nexus-hosted dependency to an Android Gradle project."
    )
    parser.add_argument("--project-root", default=".", help="Android project root")
    parser.add_argument("--module", default="app", help="Target Gradle module name")
    parser.add_argument("--repository-url", required=True, help="Nexus repository URL")
    parser.add_argument("--dependency", required=True, help="Dependency in group:artifact:version form")
    parser.add_argument(
        "--configuration",
        default="implementation",
        help="Gradle configuration, e.g. implementation, api, kapt",
    )
    parser.add_argument("--alias", help="Version catalog alias. Defaults to the artifact name.")
    parser.add_argument("--version-key", help="Version catalog key. Defaults to the alias.")
    parser.add_argument(
        "--credentials-mode",
        choices=["none", "env"],
        default="none",
        help="Use env/Gradle-property backed credentials for the Maven repo.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing files")
    args = parser.parse_args()

    parts = args.dependency.split(":")
    if len(parts) != 3:
        parser.error("--dependency must be in group:artifact:version form")
    args.group, args.artifact, args.version = parts
    return args


@dataclass
class ProjectFiles:
    settings: Path
    module_build: Path
    catalog: Optional[Path]


def find_project_files(project_root: Path, module_name: str) -> ProjectFiles:
    settings_candidates = [project_root / "settings.gradle.kts", project_root / "settings.gradle"]
    settings = next((path for path in settings_candidates if path.exists()), None)
    if not settings:
        raise FileNotFoundError("Could not find settings.gradle.kts or settings.gradle")

    module_candidates = [
        project_root / module_name / "build.gradle.kts",
        project_root / module_name / "build.gradle",
    ]
    module_build = next((path for path in module_candidates if path.exists()), None)
    if not module_build:
        raise FileNotFoundError(f"Could not find build file for module '{module_name}'")

    catalog = project_root / "gradle" / "libs.versions.toml"
    return ProjectFiles(settings=settings, module_build=module_build, catalog=catalog if catalog.exists() else None)


def sanitize_alias(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    if not value:
        value = "dependency"
    if value[0].isdigit():
        value = f"dep-{value}"
    return value


def accessor_from_alias(alias: str) -> str:
    return alias.replace("-", ".")


def indent_of_line(text: str, index: int) -> str:
    line_start = text.rfind("\n", 0, index) + 1
    return text[line_start:index]


def find_block(text: str, anchor: str, start_index: int = 0) -> Tuple[int, int]:
    anchor_index = text.find(anchor, start_index)
    if anchor_index == -1:
        raise ValueError(f"Could not find block anchored by '{anchor}'")
    open_index = text.find("{", anchor_index)
    if open_index == -1:
        raise ValueError(f"Could not find opening brace for '{anchor}'")

    depth = 0
    for index in range(open_index, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return open_index, index
    raise ValueError(f"Could not find closing brace for '{anchor}'")


def build_maven_block(repository_url: str, credentials_mode: str, indent: str) -> str:
    lines = [
        f"{indent}maven {{",
        f'{indent}    url = uri("{repository_url}")',
    ]
    if repository_url.startswith("http://"):
        lines.append(f"{indent}    isAllowInsecureProtocol = true")
    if credentials_mode == "env":
        lines.extend(
            [
                f"{indent}    credentials {{",
                f'{indent}        username = providers.gradleProperty("nexusUsername").orElse(providers.environmentVariable("NEXUS_USERNAME")).orNull',
                f'{indent}        password = providers.gradleProperty("nexusPassword").orElse(providers.environmentVariable("NEXUS_PASSWORD")).orNull',
                f"{indent}    }}",
            ]
        )
    lines.append(f"{indent}}}")
    return "\n".join(lines) + "\n"


def ensure_repository(settings_text: str, repository_url: str, credentials_mode: str) -> Tuple[str, bool]:
    if repository_url in settings_text:
        return settings_text, False

    dep_open, dep_close = find_block(settings_text, "dependencyResolutionManagement")
    _, repos_close = find_block(settings_text, "repositories", dep_open)
    repos_indent = indent_of_line(settings_text, settings_text.find("repositories", dep_open))
    child_indent = repos_indent + "    "
    insertion = build_maven_block(repository_url, credentials_mode, child_indent)
    updated = settings_text[:repos_close] + insertion + settings_text[repos_close:]
    return updated, True


def ensure_catalog_entry(
    catalog_text: str,
    group: str,
    artifact: str,
    version: str,
    alias: str,
    version_key: str,
) -> Tuple[str, bool]:
    changed = False

    version_pattern = re.compile(rf"^{re.escape(version_key)}\s*=\s*\"([^\"]+)\"\s*$", re.MULTILINE)
    version_match = version_pattern.search(catalog_text)
    if version_match:
        if version_match.group(1) != version:
            raise ValueError(
                f"Version key '{version_key}' already exists with value '{version_match.group(1)}'. "
                "Provide --version-key to avoid overwriting an unrelated dependency."
            )
    else:
        catalog_text = insert_into_toml_section(
            catalog_text,
            "versions",
            f'{version_key} = "{version}"',
        )
        changed = True

    library_pattern = re.compile(rf"^{re.escape(alias)}\s*=\s*\{{([^\n]+)\}}\s*$", re.MULTILINE)
    library_match = library_pattern.search(catalog_text)
    expected_library = f'{alias} = {{ group = "{group}", name = "{artifact}", version.ref = "{version_key}" }}'
    if library_match:
        full_line = library_match.group(0).strip()
        if full_line != expected_library:
            raise ValueError(
                f"Library alias '{alias}' already exists with different coordinates. "
                "Provide --alias to avoid overwriting an unrelated dependency."
            )
    else:
        catalog_text = insert_into_toml_section(catalog_text, "libraries", expected_library)
        changed = True

    return catalog_text, changed


def insert_into_toml_section(text: str, section_name: str, line_to_add: str) -> str:
    header = f"[{section_name}]"
    header_index = text.find(header)
    if header_index == -1:
        raise ValueError(f"Could not find [{section_name}] in version catalog")
    next_section_match = re.search(r"^\[.+\]\s*$", text[header_index + len(header):], re.MULTILINE)
    if next_section_match:
        insert_at = header_index + len(header) + next_section_match.start()
    else:
        insert_at = len(text)
    insertion = line_to_add + "\n"
    return text[:insert_at] + insertion + text[insert_at:]


def ensure_module_dependency(module_text: str, dependency_line: str) -> Tuple[str, bool]:
    if dependency_line in module_text:
        return module_text, False
    _, deps_close = find_block(module_text, "dependencies")
    deps_indent = indent_of_line(module_text, module_text.find("dependencies"))
    child_indent = deps_indent + "    "
    updated = module_text[:deps_close] + f"{child_indent}{dependency_line}\n" + module_text[deps_close:]
    return updated, True


def write_if_changed(path: Path, original: str, updated: str, dry_run: bool) -> bool:
    if original == updated:
        return False
    if dry_run:
        print(f"[dry-run] Would update {path}")
        return True
    path.write_text(updated, encoding="utf-8")
    print(f"Updated {path}")
    return True


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()

    try:
        files = find_project_files(project_root, args.module)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    alias = sanitize_alias(args.alias or args.artifact)
    version_key = sanitize_alias(args.version_key or alias)

    settings_text = files.settings.read_text(encoding="utf-8")
    updated_settings, settings_changed = ensure_repository(settings_text, args.repository_url, args.credentials_mode)

    catalog_changed = False
    dependency_ref: str
    if files.catalog:
        catalog_text = files.catalog.read_text(encoding="utf-8")
        try:
            updated_catalog, catalog_changed = ensure_catalog_entry(
                catalog_text,
                args.group,
                args.artifact,
                args.version,
                alias,
                version_key,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 3
        dependency_ref = f"{args.configuration}(libs.{accessor_from_alias(alias)})"
        if args.dry_run and catalog_changed:
            print(f"[dry-run] Would update {files.catalog}")
    else:
        updated_catalog = ""
        dependency_ref = f'{args.configuration}("{args.group}:{args.artifact}:{args.version}")'

    module_text = files.module_build.read_text(encoding="utf-8")
    updated_module, module_changed = ensure_module_dependency(module_text, dependency_ref)

    if args.dry_run:
        print(f"Project root: {project_root}")
        print(f"Settings file: {files.settings}")
        print(f"Module file: {files.module_build}")
        if files.catalog:
            print(f"Version catalog: {files.catalog}")
        print(f"Repository URL: {args.repository_url}")
        print(f"Dependency: {args.group}:{args.artifact}:{args.version}")
        print(f"Catalog alias: {alias}")
        print(f"Version key: {version_key}")
        print(f"Module entry: {dependency_ref}")

    changes = 0
    if write_if_changed(files.settings, settings_text, updated_settings, args.dry_run):
        changes += 1
    if files.catalog and catalog_changed and not args.dry_run:
        files.catalog.write_text(updated_catalog, encoding="utf-8")
        print(f"Updated {files.catalog}")
        changes += 1
    elif files.catalog and catalog_changed and args.dry_run:
        changes += 1
    if write_if_changed(files.module_build, module_text, updated_module, args.dry_run):
        changes += 1

    if changes == 0:
        print("No changes were required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
