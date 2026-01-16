import json
import os
import re
from pathlib import Path
from typing import Any


# Mock Config and Vault Path for testing without full server
class MockConfig:
    def __init__(self):
        # Use actual vault path from env or default
        self.vault_path = Path(os.environ.get("VAULT_PATH", "/home/dawid/second-mind"))


def get_vault_structure_impl(root_path: str | None = None, depth: int = 2) -> dict[str, Any]:
    config = MockConfig()
    base_path = config.vault_path

    if root_path:
        target_path = base_path / root_path
    else:
        target_path = base_path

    if not target_path.exists():
        return {"error": f"Path not found: {target_path}"}

    def build_tree(current_path: Path, current_depth: int) -> dict[str, Any]:
        if current_depth > depth:
            return "..."  # Truncate

        tree = {}
        try:
            # Sort: directories first, then files
            items = sorted(
                list(current_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower())
            )

            for item in items:
                if item.name.startswith("."):
                    continue  # Skip hidden

                if item.is_dir():
                    tree[item.name] = build_tree(item, current_depth + 1)
                elif item.suffix == ".md":
                    tree[item.name] = "file"
        except PermissionError:
            return "ACCESS_DENIED"

        return tree

    return build_tree(target_path, 0)


def search_notes_impl(
    pattern: str, root_path: str | None = None, max_results: int = 50
) -> list[str]:
    config = MockConfig()
    base_path = config.vault_path

    if root_path:
        search_dir = base_path / root_path
    else:
        search_dir = base_path

    if not search_dir.exists():
        return [f"Error: Path not found {search_dir}"]

    results = []
    regex = re.compile(pattern, re.IGNORECASE)

    for item in search_dir.rglob("*.md"):
        if "/." in str(item):  # Skip hidden folders
            continue

        rel_path = str(item.relative_to(base_path))

        if regex.search(rel_path):
            results.append(rel_path)
            if len(results) >= max_results:
                break

    return results


def test_analytics():
    print("Testing get_vault_structure...")
    structure = get_vault_structure_impl(depth=1)
    print(json.dumps(structure, indent=2))

    print("\nTesting search_notes (pattern='trading')...")
    results = search_notes_impl("trading", max_results=5)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    test_analytics()
