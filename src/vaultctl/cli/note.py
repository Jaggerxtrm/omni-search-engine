from __future__ import annotations

from argparse import Namespace

from vaultctl.cli.output import emit
from vaultctl.services.note_service import (
    append_note,
    delete_note,
    extract_links,
    index_note,
    read_note,
    write_note,
)


def run(args: Namespace) -> None:
    action = args.note_command
    if action == "read":
        emit({"content": read_note(args.path, args.source)}, args.json)
        return
    if action == "write":
        emit(write_note(args.path, args.content, args.source), args.json)
        return
    if action == "append":
        emit(append_note(args.path, args.content, args.source), args.json)
        return
    if action == "delete":
        emit(delete_note(args.path, args.source), args.json)
        return
    if action == "index":
        emit(index_note(args.path, args.source), args.json)
        return
    if action == "links":
        emit(extract_links(args.path, args.source), args.json)
        return
    raise ValueError(f"Unsupported note subcommand: {action}")
