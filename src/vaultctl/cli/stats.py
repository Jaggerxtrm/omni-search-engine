from __future__ import annotations

from argparse import Namespace

from vaultctl.cli.output import emit
from vaultctl.services.stats_service import stats


def run(args: Namespace) -> None:
    emit(stats(), args.json)
