"""
MasterGo DSL API -> File

Fetches the full raw DSL JSON for a single MasterGo node and writes it
directly to disk as `mastergo_raw.json`, avoiding any chat-context payload.

Use this helper only for direct-to-disk acquisition/fallback fetches:
- Mode A root acquisition
- Rare component master acquisition for missing icons/assets

For inspection and Mode B rendering, do not read the output JSON directly;
use scripts/query/dsl_query.py to return bounded, depth-limited slices.

Usage:
    python getdsl_to_file.py <output_json> --short-link <URL>
    python getdsl_to_file.py <output_json> --file-id <ID> --layer-id <ID>
    python getdsl_to_file.py <output_json> --file-id <ID> --layer-id <ID> --skip-file-context

Optional:
    --token <MG_MCP_TOKEN>
    --base-url https://uxd.tinnove.com.cn

Token resolution order:
1. --token
2. MG_MCP_TOKEN env
3. MASTERGO_API_TOKEN env
4. ~/.claude.json -> mcpServers.mastergo-magic-mcp.env.MG_MCP_TOKEN
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_RULES = [
    "token filed must be generated as a variable (colors, shadows, fonts, etc.) and the token field must be displayed in the comment",
    (
        "componentDocumentLinks is a list of frontend component documentation links used in the DSL layer, "
        "designed to help you understand how to use the components. When it exists and is not empty, you need "
        "to use mcp__getComponentLink in a for loop to get the URL content of all components in the list, "
        "understand how to use the components, and generate code using the components."
    ),
]


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def resolve_token(cli_token: str | None) -> str:
    if cli_token:
        return cli_token

    env_token = os.environ.get("MG_MCP_TOKEN") or os.environ.get("MASTERGO_API_TOKEN")
    if env_token:
        return env_token

    claude_config = Path.home() / ".claude.json"
    data = _read_json(claude_config)
    if data:
        try:
            return data["mcpServers"]["mastergo-magic-mcp"]["env"]["MG_MCP_TOKEN"]
        except Exception:
            pass

    raise RuntimeError(
        "MasterGo token not found. Provide --token or set MG_MCP_TOKEN / MASTERGO_API_TOKEN."
    )


def _open_json(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> dict:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def _resolve_short_link(short_link: str, timeout: int = 30) -> tuple[str, str, str]:
    request = urllib.request.Request(short_link)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        redirect_url = response.geturl()

    parsed = urllib.parse.urlparse(redirect_url)
    query = urllib.parse.parse_qs(parsed.query)

    file_id = query.get("file", [""])[0]
    if not file_id:
        match = re.search(r"/file/(\d+)", parsed.path)
        if match:
            file_id = match.group(1)

    layer_id = query.get("layer_id", [""])[0]

    if not file_id or not layer_id:
        raise RuntimeError(f"Could not extract fileId/layerId from redirect URL: {redirect_url}")

    return file_id, layer_id, redirect_url


def _extract_component_document_links(dsl: dict) -> list[str]:
    links: set[str] = set()

    def walk(node: dict) -> None:
        component_info = node.get("componentInfo") or {}
        doc_links = component_info.get("componentSetDocumentLink") or []
        if doc_links and doc_links[0]:
            links.add(doc_links[0])

        for child in node.get("children") or []:
            walk(child)

    for node in dsl.get("nodes") or []:
        walk(node)

    return sorted(links)


def fetch_dsl(
    *,
    base_url: str,
    token: str,
    file_id: str,
    layer_id: str,
    timeout: int = 30,
) -> dict:
    params = urllib.parse.urlencode({"fileId": file_id, "layerId": layer_id})
    url = f"{base_url.rstrip('/')}/mcp/dsl?{params}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-MG-UserAccessToken": token,
    }
    dsl = _open_json(url, headers=headers, timeout=timeout)
    return {
        "dsl": dsl,
        "componentDocumentLinks": _extract_component_document_links(dsl),
        "rules": DEFAULT_RULES,
    }


def write_outputs(
    *,
    output_json: Path,
    payload: dict,
    file_id: str,
    layer_id: str,
    short_link: str | None,
    redirect_url: str | None,
    skip_file_context: bool,
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if skip_file_context:
        return

    file_context = {
        "fileId": file_id,
        "rootLayerId": layer_id,
    }
    if short_link:
        file_context["shortLink"] = short_link
    if redirect_url:
        file_context["redirectUrl"] = redirect_url

    pipeline_result_path = output_json.parent / "pipeline_result.json"
    pr_data = {}
    if pipeline_result_path.exists():
        try:
            with open(pipeline_result_path, "r", encoding="utf-8") as f:
                pr_data = json.load(f)
        except Exception:
            pass

    pr_data["file_context"] = file_context
    pipeline_result_path.write_text(json.dumps(pr_data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch full MasterGo DSL payload and save it to disk without chat-context output."
    )
    parser.add_argument("output_json", help="Path to write mastergo_raw.json")
    parser.add_argument("--short-link", help="MasterGo short link, e.g. https://xxx/goto/abcd")
    parser.add_argument("--file-id", help="MasterGo fileId")
    parser.add_argument("--layer-id", help="MasterGo layerId")
    parser.add_argument("--token", help="MasterGo MCP token")
    parser.add_argument("--base-url", default="https://uxd.tinnove.com.cn", help="MasterGo base URL")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument(
        "--skip-file-context",
        action="store_true",
        help="Write only the requested DSL JSON and skip sibling file_context.json/pipeline_result.json metadata output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.short_link and not (args.file_id and args.layer_id):
        print(
            "Either provide --short-link, or provide both --file-id and --layer-id.",
            file=sys.stderr,
        )
        return 1

    token = resolve_token(args.token)

    if args.short_link:
        file_id, layer_id, redirect_url = _resolve_short_link(args.short_link, timeout=args.timeout)
    else:
        file_id = args.file_id
        layer_id = args.layer_id
        redirect_url = None

    payload = fetch_dsl(
        base_url=args.base_url,
        token=token,
        file_id=file_id,
        layer_id=layer_id,
        timeout=args.timeout,
    )

    output_json = Path(args.output_json)
    write_outputs(
        output_json=output_json,
        payload=payload,
        file_id=file_id,
        layer_id=layer_id,
        short_link=args.short_link,
        redirect_url=redirect_url,
        skip_file_context=args.skip_file_context,
    )

    pipeline_result_output = None if args.skip_file_context else str(output_json.parent / "pipeline_result.json")
    print(
        json.dumps(
            {
                "status": "SUCCESS",
                "output": str(output_json),
                "pipeline_result": pipeline_result_output,
                "fileId": file_id,
                "layerId": layer_id,
                "redirectUrl": redirect_url,
                "componentDocumentLinks": len(payload["componentDocumentLinks"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
