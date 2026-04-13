from __future__ import annotations

from argparse import Namespace

from vaultctl.mcp.server import serve_stdio


def run(args: Namespace) -> None:
    if args.transport != "stdio":
        raise ValueError(f"Unsupported transport: {args.transport}")
    serve_stdio()
