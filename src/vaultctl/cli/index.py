from __future__ import annotations

import time
from argparse import Namespace

from vaultctl.cli.output import emit
from vaultctl.services.index_service import index_sources


def run_index(args: Namespace) -> None:
    emit(index_sources(source=args.source, full=args.full), args.json)


def run_watch(args: Namespace) -> None:
    debounce_seconds = max(args.debounce_ms, 100) / 1000.0
    try:
        while True:
            counters = index_sources(source=args.source, full=False)
            emit({"indexed": counters, "debounce_ms": args.debounce_ms}, args.json)
            time.sleep(debounce_seconds)
    except KeyboardInterrupt:
        emit({"stopped": True}, args.json)
