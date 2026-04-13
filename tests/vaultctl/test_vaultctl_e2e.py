from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from vaultctl.mcp.adapters import legacy_tool_adapters


@pytest.fixture()
def temp_vault_env(tmp_path: Path) -> dict[str, Path]:
    home = tmp_path / "home"
    config_dir = home / ".config" / "vaultctl"
    data_dir = home / ".local" / "share" / "vaultctl"
    vault_root = tmp_path / "vault"
    transcripts_root = tmp_path / "transcripts"

    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    (vault_root / "folder-a").mkdir(parents=True)
    (vault_root / "folder-b").mkdir(parents=True)
    (vault_root / "secret").mkdir(parents=True)
    transcripts_root.mkdir(parents=True)

    (vault_root / "folder-a" / "alpha.md").write_text(
        """---
"""
        "title: Alpha Note\n"
        "tags: [repo, finance]\n"
        "status: permanent\n"
        "---\n"
        "# Alpha\n"
        "repo market liquidity alpha signal\n"
        "See [[Beta Note]] and [[Shared Duplicate]].\n",
        encoding="utf-8",
    )
    (vault_root / "folder-a" / "beta.md").write_text(
        """---
"""
        "title: Beta Note\n"
        "tags: [macro]\n"
        "status: active\n"
        "---\n"
        "# Beta\n"
        "beta macro content\n",
        encoding="utf-8",
    )
    duplicate_body = (
        """---
"""
        "title: Shared Duplicate\n"
        "tags: [dup]\n"
        "status: active\n"
        "---\n"
        "# Dup\n"
        "duplicated content\n"
    )
    (vault_root / "folder-b" / "duplicate.md").write_text(duplicate_body, encoding="utf-8")
    (vault_root / "folder-b" / "duplicate-copy.md").write_text(duplicate_body, encoding="utf-8")
    (vault_root / "folder-b" / "orphan.md").write_text(
        """---
"""
        "title: Lonely Note\n"
        "tags: [solo]\n"
        "status: draft\n"
        "---\n"
        "No links here\n",
        encoding="utf-8",
    )
    (vault_root / "secret" / "hidden.md").write_text(
        "# Hidden\nShould never be indexed\n", encoding="utf-8"
    )

    (transcripts_root / "lesson.analysis.md").write_text(
        """---
"""
        "title: Transcript Lesson\n"
        "tags: [transcript]\n"
        "status: draft\n"
        "---\n"
        "repo transcript signal\n",
        encoding="utf-8",
    )

    config_content = f"""db_path = \"{(data_dir / 'index.db').as_posix()}\"\n\n[[sources]]\nid = \"vault\"\nroot = \"{vault_root.as_posix()}\"\ninclude_glob = \"**/*.md\"\nexclude_glob = \"secret/**\"\n\n[[sources]]\nid = \"transcripts\"\nroot = \"{transcripts_root.as_posix()}\"\ninclude_glob = \"*.analysis.md\"\n"""
    (config_dir / "config.toml").write_text(config_content, encoding="utf-8")

    return {
        "home": home,
        "vault_root": vault_root,
        "transcripts_root": transcripts_root,
        "db_path": data_dir / "index.db",
    }


def run_vaultctl_json(*args: str, home: Path) -> Any:
    env = os.environ.copy()
    env["HOME"] = str(home)
    src_path = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONPATH"] = src_path if "PYTHONPATH" not in env else f"{src_path}:{env['PYTHONPATH']}"
    result = subprocess.run(
        [sys.executable, "-m", "vaultctl.cli.app", *args],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def normalize_search_results(results: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "source_id": row["source_id"],
            "rel_path": row["rel_path"],
            "title": row["title"],
            "tags": row["tags"],
            "status": row["status"],
            "score_type": type(row["score"]).__name__,
            "snippet_type": type(row["snippet"]).__name__,
        }
        for row in results
    ]


def test_e2e_vaultctl_features(temp_vault_env: dict[str, Path]) -> None:
    home = temp_vault_env["home"]
    vault_root = temp_vault_env["vault_root"]

    initial = run_vaultctl_json("index", "--json", home=home)
    assert initial == {"vault": 5, "transcripts": 1}

    incremental = run_vaultctl_json("index", "--json", home=home)
    assert incremental == {"vault": 0, "transcripts": 0}

    time.sleep(1.05)
    alpha_path = vault_root / "folder-a" / "alpha.md"
    alpha_path.write_text(alpha_path.read_text(encoding="utf-8") + "\nnew mtime marker\n", encoding="utf-8")
    touched = run_vaultctl_json("index", "--json", home=home)
    assert touched == {"vault": 1, "transcripts": 0}

    full = run_vaultctl_json("index", "--full", "--json", home=home)
    assert full == {"vault": 5, "transcripts": 1}

    search_results = run_vaultctl_json("search", "repo", "-n", "10", "--json", home=home)
    assert isinstance(search_results, list)
    normalized_search = normalize_search_results(search_results)
    expected_search_snapshot = [
        {
            "source_id": "vault",
            "rel_path": "folder-a/alpha.md",
            "title": "Alpha Note",
            "tags": ["finance", "repo"],
            "status": "permanent",
            "score_type": "float",
            "snippet_type": "str",
        },
        {
            "source_id": "transcripts",
            "rel_path": "lesson.analysis.md",
            "title": "Transcript Lesson",
            "tags": ["transcript"],
            "status": "draft",
            "score_type": "float",
            "snippet_type": "str",
        },
    ]
    assert normalized_search[:2] == expected_search_snapshot

    source_filtered = run_vaultctl_json("search", "repo", "--source", "transcripts", "--json", home=home)
    assert [row["source_id"] for row in source_filtered] == ["transcripts"]

    folder_filtered = run_vaultctl_json("search", "repo", "--folder", "folder-a", "--json", home=home)
    assert [row["rel_path"] for row in folder_filtered] == ["folder-a/alpha.md"]

    tag_filtered = run_vaultctl_json("search", "repo", "--tag", "repo", "--json", home=home)
    assert [row["title"] for row in tag_filtered] == ["Alpha Note"]

    status_filtered = run_vaultctl_json("search", "repo", "--status", "draft", "--json", home=home)
    assert [row["source_id"] for row in status_filtered] == ["transcripts"]

    write_result = run_vaultctl_json(
        "note",
        "write",
        "folder-a/new-note.md",
        "new unique token",
        "--source",
        "vault",
        "--json",
        home=home,
    )
    assert write_result["source_id"] == "vault"

    read_result = run_vaultctl_json(
        "note", "read", "folder-a/new-note.md", "--source", "vault", "--json", home=home
    )
    assert read_result == {"content": "new unique token"}

    append_result = run_vaultctl_json(
        "note",
        "append",
        "folder-a/new-note.md",
        "extra line",
        "--source",
        "vault",
        "--json",
        home=home,
    )
    assert append_result["source_id"] == "vault"

    appended_read = run_vaultctl_json(
        "note", "read", "folder-a/new-note.md", "--source", "vault", "--json", home=home
    )
    assert appended_read == {"content": "new unique token\nextra line"}

    auto_reindex_search = run_vaultctl_json("search", "unique token", "--json", home=home)
    assert [row["rel_path"] for row in auto_reindex_search] == ["folder-a/new-note.md"]

    delete_result = run_vaultctl_json(
        "note", "delete", "folder-a/new-note.md", "--source", "vault", "--json", home=home
    )
    assert delete_result["source_id"] == "vault"
    after_delete_search = run_vaultctl_json("search", "unique token", "--json", home=home)
    assert after_delete_search == []

    index_note_result = run_vaultctl_json(
        "note", "index", "folder-a/alpha.md", "--source", "vault", "--json", home=home
    )
    assert index_note_result == {"indexed": "folder-a/alpha.md", "source_id": "vault"}

    find_result = run_vaultctl_json("find", "folder-a", "--json", home=home)
    assert find_result == [
        {"source_id": "vault", "rel_path": "folder-a/alpha.md", "title": "Alpha Note"},
        {"source_id": "vault", "rel_path": "folder-a/beta.md", "title": "Beta Note"},
    ]

    tree_result = run_vaultctl_json("tree", "folder-a", "--depth", "2", "--json", home=home)
    assert tree_result == [
        {"source_id": "vault", "rel_path": "folder-a/alpha.md"},
        {"source_id": "vault", "rel_path": "folder-a/beta.md"},
    ]

    context_result = run_vaultctl_json("context", "vault:folder-a/beta.md", "--json", home=home)
    assert context_result == {
        "source_id": "vault",
        "rel_path": "folder-a/beta.md",
        "title": "Beta Note",
        "status": "active",
        "tags": ["macro"],
        "links": [],
        "backlinks": [
            {"source_id": "vault", "rel_path": "folder-a/alpha.md", "title": "Alpha Note"}
        ],
    }

    status_result = run_vaultctl_json("status", "--json", home=home)
    assert status_result == {
        "db_path": str(temp_vault_env["db_path"]),
        "db_exists": True,
        "documents": 6,
        "sources": ["vault", "transcripts"],
    }

    stats_result = run_vaultctl_json("stats", "--json", home=home)
    stats_snapshot = {
        "documents": stats_result["documents"],
        "sections": stats_result["sections"],
        "last_updated_type": type(stats_result["last_updated"]).__name__,
        "sources": stats_result["sources"],
    }
    assert stats_snapshot == {
        "documents": 6,
        "sections": 6,
        "last_updated_type": "str",
        "sources": [
            {
                "id": "transcripts",
                "root": str(temp_vault_env["transcripts_root"]),
                "include_glob": "*.analysis.md",
            },
            {
                "id": "vault",
                "root": str(temp_vault_env["vault_root"]),
                "include_glob": "**/*.md",
            },
        ],
    }

    orphans = run_vaultctl_json("audit", "orphans", "--json", home=home)
    assert {row["title"] for row in orphans} >= {"Alpha Note", "Lonely Note", "Transcript Lesson"}

    linked = run_vaultctl_json("audit", "linked", "--json", home=home)
    assert linked == [{"source_id": "vault", "rel_path": "folder-a/alpha.md", "title": "Alpha Note"}]

    duplicates = run_vaultctl_json("audit", "duplicates", "--json", home=home)
    assert duplicates == [{"source_id": "vault", "title": "Shared Duplicate", "count": 2}]


def test_mcp_legacy_adapter_completeness() -> None:
    adapters = legacy_tool_adapters()
    expected_names = {
        "append_to_note",
        "delete_note",
        "get_duplicate_content",
        "get_full_context",
        "get_index_stats",
        "get_most_linked_notes",
        "get_orphaned_notes",
        "get_vault_statistics",
        "get_vault_structure",
        "index_note",
        "read_note",
        "reindex_vault",
        "search_notes",
        "semantic_search",
        "suggest_links",
        "write_note",
    }
    assert set(adapters.keys()) == expected_names
    assert len(adapters) == 16
