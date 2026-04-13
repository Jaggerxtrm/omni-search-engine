from __future__ import annotations

import json
import sys
from typing import Any

from vaultctl.mcp.adapters import legacy_tool_adapters


def serve_stdio() -> None:
    tools = legacy_tool_adapters()
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        request = json.loads(line)
        method = request.get("tool")
        args = request.get("args", {})
        if method == "list_tools":
            sys.stdout.write(json.dumps({"tools": sorted(tools)}) + "\n")
            sys.stdout.flush()
            continue
        if method not in tools:
            sys.stdout.write(json.dumps({"error": f"unknown tool {method}"}) + "\n")
            sys.stdout.flush()
            continue
        result: Any = tools[method](**args)
        sys.stdout.write(json.dumps({"result": result}, ensure_ascii=False) + "\n")
        sys.stdout.flush()
