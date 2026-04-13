from __future__ import annotations

from argparse import Namespace

from vaultctl.cli.output import emit
from vaultctl.services.audit_service import run_audit


def run(args: Namespace) -> None:
    emit(run_audit(args.audit_mode, args.source, args.n), args.json)
