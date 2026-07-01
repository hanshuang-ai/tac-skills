#!/usr/bin/env python3
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query a Nexus Maven repository for dependency versions."
    )
    parser.add_argument("--base-url", required=True, help="Nexus base URL, e.g. https://nexus.example.com")
    parser.add_argument("--repository", required=True, help="Nexus repository name, e.g. maven-public")
    parser.add_argument(
        "--package",
        help="Package name to resolve. Prefer group:artifact, but artifact-only search is also supported.",
    )
    parser.add_argument("--group", help="Exact Maven group when not using --package")
    parser.add_argument("--artifact", help="Exact Maven artifact when not using --package")
    parser.add_argument("--username", help="Nexus username; defaults to NEXUS_USERNAME")
    parser.add_argument("--password", help="Nexus password; defaults to NEXUS_PASSWORD")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds")
    parser.add_argument("--allow-insecure", action="store_true", help="Allow insecure HTTP URLs")
    parser.add_argument("--list-all", action="store_true", help="Print all discovered versions")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable text")
    args = parser.parse_args()

    if not args.package and not (args.group and args.artifact):
        parser.error("Provide --package or both --group and --artifact.")

    if args.package and ":" in args.package:
        parts = args.package.split(":")
        if len(parts) < 2:
            parser.error("--package must be artifact-only or group:artifact")
        args.group = parts[0]
        args.artifact = parts[1]
    elif args.package and not args.artifact:
        args.artifact = args.package

    if args.base_url.startswith("http://") and not args.allow_insecure:
        parser.error("Refusing insecure HTTP base URL. Re-run with --allow-insecure if this is intentional.")

    return args


def build_auth_header(username: Optional[str], password: Optional[str]) -> Dict[str, str]:
    if not username:
        return {}
    token = base64.b64encode(f"{username}:{password or ''}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def http_get_json(url: str, headers: Dict[str, str], timeout: int) -> dict:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def http_get_text(url: str, headers: Dict[str, str], timeout: int) -> str:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def version_sort_key(version: str) -> Tuple:
    tokens: List[Tuple[int, object]] = []
    current = ""
    digit_mode: Optional[bool] = None
    for ch in version:
        if ch.isdigit():
            if digit_mode is False:
                tokens.append((1, current.lower()))
                current = ch
            else:
                current += ch
            digit_mode = True
        elif ch.isalpha():
            if digit_mode is True:
                tokens.append((0, int(current)))
                current = ch
            else:
                current += ch
            digit_mode = False
        else:
            if current:
                if digit_mode:
                    tokens.append((0, int(current)))
                else:
                    tokens.append((1, current.lower()))
            current = ""
            digit_mode = None
    if current:
        if digit_mode:
            tokens.append((0, int(current)))
        else:
            tokens.append((1, current.lower()))
    return tuple(tokens)


@dataclass
class CoordinateVersions:
    group: str
    artifact: str
    versions: List[str]
    latest_version: Optional[str]
    source: str


def extract_version_style(version: str) -> str:
    match = re.match(r"^(.*?)-\d+(?:\.\d+)+(?:[._-].*)?$", version)
    if match and match.group(1):
        return match.group(1)
    return version.split("-", 1)[0]


def build_style_groups(versions: List[str]) -> Dict[str, List[str]]:
    grouped: Dict[str, List[str]] = defaultdict(list)
    for version in versions:
        grouped[extract_version_style(version)].append(version)
    return dict(grouped)


def parse_metadata_versions(xml_text: str) -> Tuple[List[str], Optional[str]]:
    root = ET.fromstring(xml_text)
    latest = root.findtext("./versioning/release") or root.findtext("./versioning/latest")
    versions = [node.text for node in root.findall("./versioning/versions/version") if node.text]
    versions = sorted(set(versions), key=version_sort_key, reverse=True)
    if not latest and versions:
        latest = versions[0]
    return versions, latest


def fetch_metadata_versions(
    base_url: str,
    repository: str,
    group: str,
    artifact: str,
    headers: Dict[str, str],
    timeout: int,
) -> Optional[CoordinateVersions]:
    group_path = group.replace(".", "/")
    metadata_url = f"{base_url.rstrip('/')}/repository/{repository}/{group_path}/{artifact}/maven-metadata.xml"
    try:
        xml_text = http_get_text(metadata_url, headers, timeout)
    except urllib.error.URLError:
        return None
    versions, latest = parse_metadata_versions(xml_text)
    return CoordinateVersions(group=group, artifact=artifact, versions=versions, latest_version=latest, source="maven-metadata.xml")


def search_nexus(
    base_url: str,
    repository: str,
    group: Optional[str],
    artifact: str,
    headers: Dict[str, str],
    timeout: int,
) -> Dict[Tuple[str, str], List[str]]:
    packages: Dict[Tuple[str, str], set] = defaultdict(set)
    continuation_token: Optional[str] = None

    while True:
        query = {"repository": repository, "name": artifact}
        if group:
            query["group"] = group
        if continuation_token:
            query["continuationToken"] = continuation_token
        url = f"{base_url.rstrip('/')}/service/rest/v1/search?{urllib.parse.urlencode(query)}"
        data = http_get_json(url, headers, timeout)
        for item in data.get("items", []):
            item_group = item.get("group")
            item_artifact = item.get("name")
            version = item.get("version")
            if not item_group or not item_artifact or not version:
                continue
            packages[(item_group, item_artifact)].add(version)
        continuation_token = data.get("continuationToken")
        if not continuation_token:
            break

    return {
        coords: sorted(versions, key=version_sort_key, reverse=True)
        for coords, versions in packages.items()
    }


def resolve_versions(args: argparse.Namespace) -> List[CoordinateVersions]:
    username = args.username or os.getenv("NEXUS_USERNAME")
    password = args.password or os.getenv("NEXUS_PASSWORD")
    headers = build_auth_header(username, password)

    if args.group and args.artifact:
        metadata_result = fetch_metadata_versions(
            args.base_url,
            args.repository,
            args.group,
            args.artifact,
            headers,
            args.timeout,
        )
        if metadata_result and metadata_result.versions:
            return [metadata_result]

    search_results = search_nexus(
        args.base_url,
        args.repository,
        args.group,
        args.artifact,
        headers,
        args.timeout,
    )
    resolved: List[CoordinateVersions] = []
    for (group, artifact), versions in sorted(search_results.items()):
        latest = versions[0] if versions else None
        resolved.append(
            CoordinateVersions(
                group=group,
                artifact=artifact,
                versions=versions,
                latest_version=latest,
                source="search",
            )
        )
    return resolved


def emit_human(results: List[CoordinateVersions], list_all: bool) -> int:
    if not results:
        print("No matching package was found in Nexus.", file=sys.stderr)
        return 2

    if len(results) == 1:
        result = results[0]
        style_groups = build_style_groups(result.versions)
        print(f"Coordinate: {result.group}:{result.artifact}")
        print(f"Latest: {result.latest_version or 'unknown'}")
        print(f"Source: {result.source}")
        if len(style_groups) > 1:
            print("Version styles:")
            for style, versions in sorted(
                style_groups.items(),
                key=lambda item: version_sort_key(item[1][0]),
                reverse=True,
            ):
                print(f"  - {style}: {versions[0]}")
            print("Selection required: multiple naming styles detected. Choose a style before integrating.")
        if list_all or len(result.versions) > 1:
            print("Versions:")
            for version in result.versions:
                marker = " (latest)" if version == result.latest_version else ""
                print(f"  - {version}{marker}")
        return 0

    print("Multiple coordinates matched the requested package:")
    for result in results:
        summary = ", ".join(result.versions[:5])
        if len(result.versions) > 5:
            summary += ", ..."
        print(f"- {result.group}:{result.artifact}")
        print(f"  latest: {result.latest_version or 'unknown'}")
        print(f"  versions: {summary or 'none'}")
    return 0


def emit_json(results: List[CoordinateVersions]) -> int:
    print(
        json.dumps(
            [
                {
                    "group": result.group,
                    "artifact": result.artifact,
                    "latestVersion": result.latest_version,
                    "versions": result.versions,
                    "styleGroups": build_style_groups(result.versions),
                    "source": result.source,
                }
                for result in results
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    args = parse_args()
    try:
        results = resolve_versions(args)
    except urllib.error.HTTPError as exc:
        print(f"Nexus request failed: HTTP {exc.code} {exc.reason}", file=sys.stderr)
        return 3
    except urllib.error.URLError as exc:
        print(f"Nexus request failed: {exc.reason}", file=sys.stderr)
        return 3
    except ET.ParseError as exc:
        print(f"Failed to parse maven-metadata.xml: {exc}", file=sys.stderr)
        return 4

    if args.json:
        return emit_json(results)
    return emit_human(results, args.list_all)


if __name__ == "__main__":
    sys.exit(main())
