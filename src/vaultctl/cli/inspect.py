from __future__ import annotations

from argparse import Namespace

from vaultctl.cli.output import emit
from vaultctl.services.inspect_service import context, find, status, tree


def run_find(args: Namespace) -> None:
    emit(find(args.pattern, args.source, args.root, args.n), args.json)


def run_tree(args: Namespace) -> None:
    emit(tree(args.root_arg, args.source, args.depth), args.json)


def run_context(args: Namespace) -> None:
    emit(context(args.target), args.json)


def run_status(args: Namespace) -> None:
    emit(status(), args.json)
