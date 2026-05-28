import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

TOOL_DEF = {
    "name": "kagi_search",
    "description": (
        "Search the web via the Kagi Search API. Returns a numbered list of "
        "results (title, URL, snippet) plus related-search suggestions. "
        "Requires KAGI_API_KEY in the environment."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results (1-10). Defaults to 5.",
                "default": 5,
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["query"],
    },
}

API_URL = "https://kagi.com/api/v0/search"
TIMEOUT_SECONDS = 30
DEFAULT_LIMIT = 5
MAX_LIMIT = 10


def _fetch(query: str, limit: int, api_key: str) -> dict:
    qs = urllib.parse.urlencode({"q": query, "limit": limit})
    req = urllib.request.Request(  # noqa: S310 (https URL is fixed)
        f"{API_URL}?{qs}",
        headers={"Authorization": f"Bot {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310
        return json.loads(resp.read())


def _format_results(payload: dict) -> str:
    data = payload.get("data") or []
    results = [item for item in data if item.get("t") == 0]
    related = next(
        (item.get("list", []) for item in data if item.get("t") == 1),
        [],
    )

    if not results:
        return "No results."

    lines = []
    for idx, item in enumerate(results, start=1):
        title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        snippet = item.get("snippet", "").strip()
        lines.append(f"{idx}. {title}\n   {url}")
        if snippet:
            lines.append(f"   {snippet}")

    if related:
        lines.append("")
        lines.append("Related: " + ", ".join(related))

    return "\n".join(lines)


def execute(query: str, limit: int = DEFAULT_LIMIT) -> str:
    api_key = os.environ.get("KAGI_API_KEY")
    if not api_key:
        return "Error: KAGI_API_KEY is not set in the environment."

    limit = max(1, min(MAX_LIMIT, int(limit)))

    try:
        payload = _fetch(query, limit, api_key)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        return f"Kagi API error (HTTP {e.code}): {body}"
    except urllib.error.URLError as e:
        return f"Network error calling Kagi: {e.reason}"
    except (TimeoutError, json.JSONDecodeError) as e:
        logger.exception("Kagi search failed")
        return f"Kagi search failed: {e}"

    if payload.get("error"):
        return f"Kagi API error: {payload['error']}"

    return _format_results(payload)
