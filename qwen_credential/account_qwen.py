#!/usr/bin/env python3
"""
account-qwen CLI - Qwen Account Rotation Management Utility

This script manages multiple Qwen OAuth accounts with automatic
round-robin rotation when quota is exhausted.

Usage:
    account-qwen --setup           Interactive setup for initial accounts
    account-qwen --list            List all configured accounts
    account-qwen --switch <index>  Manually switch to specific account
    account-qwen --switch-next     Switch to next account (silent, for auto-rotation)
    account-qwen --stats           Display usage statistics
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from textwrap import dedent

from qwen_credential.account_manager import (
    DEFAULT_QWEN_DIR,
    DEFAULT_TOTAL_ACCOUNTS,
    AccountManager,
    AccountNotFoundError,
    LockError,
    SwitchReason,
)

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_success(msg: str) -> None:
    """Print success message in green."""
    print(f"{GREEN}✓{RESET} {msg}")


def print_warning(msg: str) -> None:
    """Print warning message in yellow."""
    print(f"{YELLOW}⚠{RESET} {msg}")


def print_error(msg: str) -> None:
    """Print error message in red."""
    print(f"{RED}✗{RESET} {msg}")


def print_info(msg: str) -> None:
    """Print info message in blue."""
    print(f"{BLUE}ℹ{RESET} {msg}")


def print_header(msg: str) -> None:
    """Print header in bold."""
    print(f"\n{BOLD}{msg}{RESET}\n")


def check_qwen_installed() -> bool:
    """Check if qwen CLI is installed."""
    return shutil.which("qwen") is not None


def get_qwen_creds_path() -> Path:
    """Get the path to qwen OAuth credentials."""
    return DEFAULT_QWEN_DIR / "oauth_creds.json"


def setup_accounts(total_accounts: int = DEFAULT_TOTAL_ACCOUNTS) -> int:
    """
    Interactive setup for Qwen account credentials.

    Guides the user through OAuth login for each account, storing
    credentials in accounts/oauth_creds_N.json.

    Args:
        total_accounts: Number of accounts to set up.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    print_header(f"Qwen Account Rotation Setup ({total_accounts} accounts)")
    print_info("This will guide you through logging into multiple Qwen accounts.")
    print_info("Each account requires a separate OAuth flow in your browser.\n")

    # Check qwen CLI is installed
    if not check_qwen_installed():
        print_error("qwen CLI is not installed!")
        print("Install it with: npm install -g @qwen-code/qwen-code")
        return 1

    # Create accounts directory
    qwen_dir = DEFAULT_QWEN_DIR
    accounts_dir = qwen_dir / "accounts"

    if not accounts_dir.exists():
        accounts_dir.mkdir(parents=True)
        print_success(f"Created accounts directory: {accounts_dir}")
    else:
        print_info(f"Accounts directory exists: {accounts_dir}")

    # Setup each account
    creds_path = get_qwen_creds_path()

    for i in range(1, total_accounts + 1):
        print_header(f"Account {i}/{total_accounts}")

        print("To add a new Qwen account:")
        print(f"  1. Open a {BOLD}NEW terminal{RESET}")
        print(f"  2. Run: {BOLD}qwen{RESET}")
        print(f"  3. Complete the OAuth login in your browser")
        print(f"  4. When you see the qwen prompt, close that terminal")
        print(f"  5. Return here and press {BOLD}ENTER{RESET}\n")

        input("Press ENTER when you have completed the OAuth login...")

        # Verify credentials were created
        if not creds_path.exists():
            print_error(f"No credentials found at {creds_path}")
            retry = input("Try again? (y/N): ").strip().lower()
            if retry == "y":
                # Retry this account
                i -= 1
                continue
            else:
                return 1

        # Move credentials to accounts directory
        target_creds = accounts_dir / f"oauth_creds_{i}.json"

        if target_creds.exists():
            sys.stdout.write(f"{YELLOW}⚠{RESET} Account {i} credentials already exist. Overwrite? (y/N): ")
            sys.stdout.flush()
            overwrite = input().strip().lower()
            if overwrite != "y":
                print_info(f"Skipping account {i}")
                continue

        shutil.move(str(creds_path), str(target_creds))
        print_success(f"Saved credentials as: {target_creds}")

        # Clean up any remaining oauth_creds.json
        if creds_path.exists():
            creds_path.unlink()

    # Create initial state
    print_header("Creating Initial State")
    AccountManager(total_accounts=total_accounts)

    # Create symlink to first account
    first_creds = accounts_dir / "oauth_creds_1.json"
    creds_link = qwen_dir / "oauth_creds.json"

    if creds_link.exists():
        creds_link.unlink()

    creds_link.symlink_to(first_creds)
    print_success(f"Created symlink: {creds_link} → {first_creds}")

    # Initialize state
    from qwen_credential.account_manager import create_initial_state
    create_initial_state(total_accounts=total_accounts)
    print_success(f"Created state file with {total_accounts} accounts")

    print_header("Setup Complete!")
    print_success("All accounts configured successfully.")
    print(f"\nYou can now use:")
    print(f"  {BOLD}account-qwen --list{RESET}    - View all accounts")
    print(f"  {BOLD}account-qwen --stats{RESET}   - View usage statistics")

    return 0


def list_accounts() -> int:
    """
    List all configured accounts with their status.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    manager = AccountManager()
    accounts = manager.list_accounts()

    print_header("Configured Qwen Accounts")

    for name, info in sorted(accounts.items()):
        index = info["index"]
        active_marker = f"{GREEN}[ACTIVE]{RESET}" if info["active"] else "        "
        exists_marker = "✓" if info["exists"] else "✗"
        switches = info["switches_count"]
        last_used = info["last_used"] or "never"

        print(f"  {active_marker} [{index}] {name} {exists_marker}")
        print(f"                Switches: {switches}, Last used: {last_used}")

    return 0


def switch_account(index: int | None) -> int:
    """
    Switch to a specific account by index.

    Args:
        index: Account index to switch to (1-based). If None, switches to next.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    manager = AccountManager()

    try:
        if index is not None:
            # Switch to specific account
            state = manager.get_state()

            if index < 1 or index > state.total_accounts:
                print_error(f"Invalid account index: {index}")
                print(f"Valid range: 1-{state.total_accounts}")
                return 1

            prev = f"account{state.current_index}"
            manager.switch_to(index, reason=SwitchReason.MANUAL)
            print_success(f"Switched from {prev} to account{index}")
            print(f"Updated symlink: oauth_creds.json → accounts/oauth_creds_{index}.json")
        else:
            # Switch to next account (silent mode for auto-rotation)
            switched, next_index = manager.switch_next(reason=SwitchReason.AUTO_QUOTA)
            if not switched:
                print_warning("All accounts exhausted, cycled back to account1")
            print_success(f"Switched to account{next_index}")

        return 0

    except AccountNotFoundError as e:
        print_error(str(e))
        return 1
    except LockError as e:
        print_error(f"Could not acquire lock: {e}")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


def show_stats() -> int:
    """
    Display usage statistics.

    Returns:
        Exit code (0 for success).
    """
    manager = AccountManager()
    stats = manager.get_stats()

    print_header("Account Usage Statistics")

    # Per-account usage
    print("Switches per account:")
    for account, count in sorted(stats["accounts"].items()):
        print(f"  {account}: {count}")

    print()
    print(f"  Total rotations: {stats['total_switches']}")
    print(f"  Last rotation: {stats['last_switch'] or 'never'}")
    print(f"  Current account: {GREEN}{stats['current_account']}{RESET}")
    print(f"  Most used: {stats['most_used_account']} ({stats['most_used_count']} switches)")

    return 0


def main() -> int:
    """Main entry point for account-qwen CLI."""
    parser = argparse.ArgumentParser(
        prog="account-qwen",
        description="Qwen Account Rotation Management Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""
            Examples:
              account-qwen --setup           Set up 5 accounts interactively
              account-qwen --list            List all accounts with status
              account-qwen --switch 3        Switch to account 3
              account-qwen --switch-next     Switch to next account (round-robin)
              account-qwen --stats           Show usage statistics
        """),
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--setup",
        action="store_true",
        help="Interactive setup for initial account configuration",
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="List all configured accounts with status",
    )
    group.add_argument(
        "--switch",
        metavar="INDEX",
        type=int,
        help="Switch to specific account by index (1-based)",
    )
    group.add_argument(
        "--switch-next",
        action="store_true",
        help="Switch to next account in round-robin (silent, for auto-rotation)",
    )
    group.add_argument(
        "--stats",
        action="store_true",
        help="Display usage statistics",
    )

    args = parser.parse_args()

    # Route to appropriate handler
    if args.setup:
        return setup_accounts()
    elif args.list:
        return list_accounts()
    elif args.switch is not None:
        return switch_account(args.switch)
    elif args.switch_next:
        return switch_account(None)
    elif args.stats:
        return show_stats()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
