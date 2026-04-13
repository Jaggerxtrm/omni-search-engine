from __future__ import annotations

from argparse import Namespace

from vaultctl.cli.output import emit
from vaultctl.services.search_service import run_search


def run(args: Namespace) -> None:
    results = run_search(
        query=args.query,
        limit=args.n,
        source=args.source,
        folder=args.folder,
        tag=args.tag,
        status=args.status,
    )
    emit(results, args.json)
