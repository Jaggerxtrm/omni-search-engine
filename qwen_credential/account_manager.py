"""
Qwen Account Rotation Manager

This module provides atomic account switching with file locking for
safe credential rotation across multiple Qwen OAuth accounts.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Final

import yaml

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TOTAL_ACCOUNTS: Final[int] = 5
DEFAULT_QWEN_DIR: Final[Path] = Path.home() / ".qwen"
DEFAULT_LOCK_FILE: Final[str] = "/tmp/qwen_rotation.lock"
ACCOUNTS_DIR_NAME: Final[str] = "accounts"
OAUTH_CREDS_LINK: Final[str] = "oauth_creds.json"
STATE_FILE: Final[str] = "state.yaml"
ROTATION_LOG: Final[str] = "rotation.log"


class SwitchReason(Enum):
    """Reason for account switch."""
    AUTO_QUOTA = "auto_quota"
    MANUAL = "manual"
    TEST = "test"


@dataclass
class AccountStats:
    """Statistics for a single account."""
    switches_count: int = 0
    last_used: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "switches_count": self.switches_count,
            "last_used": self.last_used,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> AccountStats:
        if data is None:
            return cls()
        return cls(
            switches_count=data.get("switches_count", 0),
            last_used=data.get("last_used"),
        )


@dataclass
class RotationState:
    """Complete rotation state."""
    current_index: int = 1
    total_accounts: int = DEFAULT_TOTAL_ACCOUNTS
    last_switch: str | None = None
    switches_total: int = 0
    accounts: dict[str, AccountStats] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_index": self.current_index,
            "total_accounts": self.total_accounts,
            "last_switch": self.last_switch,
            "switches_total": self.switches_total,
            "accounts": {
                k: v.to_dict() for k, v in self.accounts.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RotationState:
        accounts = {
            k: AccountStats.from_dict(v)
            for k, v in data.get("accounts", {}).items()
        }
        return cls(
            current_index=data.get("current_index", 1),
            total_accounts=data.get("total_accounts", DEFAULT_TOTAL_ACCOUNTS),
            last_switch=data.get("last_switch"),
            switches_total=data.get("switches_total", 0),
            accounts=accounts,
        )


class LockError(Exception):
    """Raised when lock acquisition fails."""
    pass


class AccountNotFoundError(Exception):
    """Raised when target account credentials don't exist."""
    pass


class AccountManager:
    """
    Manages Qwen account rotation with atomic operations.

    This class provides thread-safe account switching using:
    - File locking (flock) to prevent race conditions
    - Atomic symlink updates via os.replace()
    - Persistent state tracking in state.yaml
    - Audit logging to rotation.log

    Example:
        >>> manager = AccountManager()
        >>> manager.switch_next()
        True
        >>> state = manager.get_state()
        >>> print(state.current_index)
        2
    """

    def __init__(
        self,
        qwen_dir: Path | None = None,
        total_accounts: int = DEFAULT_TOTAL_ACCOUNTS,
    ) -> None:
        """
        Initialize the AccountManager.

        Args:
            qwen_dir: Path to .qwen directory. Defaults to ~/.qwen
            total_accounts: Total number of configured accounts.
        """
        self.qwen_dir = qwen_dir or DEFAULT_QWEN_DIR
        self.total_accounts = total_accounts
        self.state_file = self.qwen_dir / STATE_FILE
        self.lock_file = Path(DEFAULT_LOCK_FILE)
        self.accounts_dir = self.qwen_dir / ACCOUNTS_DIR_NAME
        self.creds_link = self.qwen_dir / OAUTH_CREDS_LINK
        self.log_file = self.qwen_dir / ROTATION_LOG

    def get_state(self) -> RotationState:
        """
        Read current rotation state.

        Returns:
            Current RotationState, or default if state file doesn't exist.
        """
        if not self.state_file.exists():
            return RotationState(total_accounts=self.total_accounts)

        try:
            with open(self.state_file, "r") as f:
                data = yaml.safe_load(f) or {}
            return RotationState.from_dict(data)
        except (yaml.YAMLError, IOError) as e:
            logger.error(f"Failed to read state file: {e}")
            return RotationState(total_accounts=self.total_accounts)

    def _write_state(self, state: RotationState) -> None:
        """
        Write state file atomically.

        Uses a temporary file and os.replace() for atomicity.

        Args:
            state: State to write.
        """
        temp_file = self.state_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w") as f:
                yaml.dump(state.to_dict(), f, default_flow_style=False)
            os.replace(temp_file, self.state_file)
        except (IOError, OSError) as e:
            logger.error(f"Failed to write state file: {e}")
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()
            raise

    def _validate_account_exists(self, index: int) -> Path:
        """
        Validate that account credential file exists.

        Args:
            index: Account index (1-based).

        Returns:
            Path to the credential file.

        Raises:
            AccountNotFoundError: If credential file doesn't exist.
        """
        creds_file = self.accounts_dir / f"oauth_creds_{index}.json"
        if not creds_file.exists():
            raise AccountNotFoundError(
                f"Account {index} credentials not found: {creds_file}"
            )
        return creds_file

    def _atomic_symlink_update(self, target: Path) -> None:
        """
        Atomically update the oauth_creds.json symlink.

        Uses os.replace() which is atomic on POSIX systems.

        Args:
            target: Path to target credential file.
        """
        temp_link = self.creds_link.with_suffix(".json.tmp")

        try:
            # Remove temp link if it exists
            if temp_link.exists():
                temp_link.unlink()

            # Create temporary symlink
            temp_link.symlink_to(target)

            # Atomic replace
            os.replace(temp_link, self.creds_link)

        except OSError as e:
            logger.error(f"Failed to update symlink: {e}")
            # Clean up temp file if it exists
            if temp_link.exists():
                temp_link.unlink()
            raise

    def _update_account_stats(
        self,
        state: RotationState,
        account_index: int,
    ) -> None:
        """
        Update statistics for an account after switch.

        Args:
            state: State to update.
            account_index: Index of account being switched to.
        """
        account_key = f"account{account_index}"
        if account_key not in state.accounts:
            state.accounts[account_key] = AccountStats()

        stats = state.accounts[account_key]
        stats.switches_count += 1
        stats.last_used = datetime.now().isoformat()

    def _log_switch(
        self,
        from_index: int,
        to_index: int,
        reason: SwitchReason,
    ) -> None:
        """
        Log switch event to rotation.log.

        Args:
            from_index: Previous account index.
            to_index: New account index.
            reason: Reason for the switch.
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "event": "account_switch",
            "from": from_index,
            "to": to_index,
            "reason": reason.value,
            "trigger": "auto" if reason == SwitchReason.AUTO_QUOTA else "manual",
        }

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except IOError as e:
            logger.error(f"Failed to write to rotation log: {e}")

    def _with_lock(self, func) -> Any:
        """
        Execute function with file lock held.

        Args:
            func: Function to execute while holding lock.

        Returns:
            Function result.

        Raises:
            LockError: If lock acquisition fails.
        """
        lock_fd = None
        try:
            lock_fd = open(self.lock_file, "w")
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
            return func()
        except (IOError, OSError) as e:
            logger.error(f"Failed to acquire lock: {e}")
            raise LockError(f"Could not acquire lock: {e}") from e
        finally:
            if lock_fd:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                lock_fd.close()

    def switch_to(self, index: int, reason: SwitchReason = SwitchReason.MANUAL) -> bool:
        """
        Switch to specific account by index.

        Args:
            index: Target account index (1-based).
            reason: Reason for the switch.

        Returns:
            True if switch successful.

        Raises:
            AccountNotFoundError: If target account doesn't exist.
            LockError: If lock acquisition fails.
        """
        def _do_switch() -> bool:
            state = self.get_state()
            current_index = state.current_index

            # Validate index
            if index < 1 or index > state.total_accounts:
                raise ValueError(f"Invalid account index: {index}")

            # Validate credentials exist
            target_creds = self._validate_account_exists(index)

            # Atomic symlink update
            self._atomic_symlink_update(target_creds)

            # Update state
            state.current_index = index
            state.last_switch = datetime.now().isoformat()
            state.switches_total += 1
            self._update_account_stats(state, index)

            self._write_state(state)
            self._log_switch(current_index, index, reason)

            logger.info(f"Switched from account{current_index} to account{index}")
            return True

        return self._with_lock(_do_switch)

    def switch_next(self, reason: SwitchReason = SwitchReason.AUTO_QUOTA) -> tuple[bool, int]:
        """
        Switch to next account in round-robin fashion.

        Args:
            reason: Reason for the switch.

        Returns:
            (success, new_index) tuple.
            - success: True if switched, False if all accounts exhausted (wrapped to 1)
            - new_index: The new account index
        """
        def _do_switch() -> tuple[bool, int]:
            state = self.get_state()
            current_index = state.current_index

            # Calculate next index (round-robin)
            next_index = (current_index % state.total_accounts) + 1

            # Check if we've completed a full cycle
            wrapped = next_index == 1 and current_index == state.total_accounts

            if wrapped:
                logger.warning("All accounts exhausted, cycling back to account1")

            # Validate credentials exist
            target_creds = self._validate_account_exists(next_index)

            # Atomic symlink update
            self._atomic_symlink_update(target_creds)

            # Update state
            state.current_index = next_index
            state.last_switch = datetime.now().isoformat()
            state.switches_total += 1
            self._update_account_stats(state, next_index)

            self._write_state(state)
            self._log_switch(current_index, next_index, reason)

            logger.info(f"Switched from account{current_index} to account{next_index}")
            return (not wrapped, next_index)

        return self._with_lock(_do_switch)

    def list_accounts(self) -> dict[str, dict[str, Any]]:
        """
        List all configured accounts with status.

        Returns:
            Dictionary mapping account names to their status info.
        """
        state = self.get_state()
        result = {}

        for i in range(1, state.total_accounts + 1):
            account_key = f"account{i}"
            creds_file = self.accounts_dir / f"oauth_creds_{i}.json"
            stats = state.accounts.get(account_key, AccountStats())

            result[account_key] = {
                "index": i,
                "active": i == state.current_index,
                "exists": creds_file.exists(),
                "switches_count": stats.switches_count,
                "last_used": stats.last_used,
            }

        return result

    def get_stats(self) -> dict[str, Any]:
        """
        Get usage statistics.

        Returns:
            Dictionary with usage statistics.
        """
        state = self.get_state()
        accounts = self.list_accounts()

        # Find most used account
        most_used = max(
            accounts.items(),
            key=lambda x: x[1]["switches_count"],
            default=("account1", {"switches_count": 0})
        )

        return {
            "accounts": {
                k: v["switches_count"] for k, v in accounts.items()
            },
            "total_switches": state.switches_total,
            "last_switch": state.last_switch,
            "current_account": f"account{state.current_index}",
            "most_used_account": most_used[0],
            "most_used_count": most_used[1]["switches_count"],
        }


def create_initial_state(
    qwen_dir: Path | None = None,
    total_accounts: int = DEFAULT_TOTAL_ACCOUNTS,
) -> RotationState:
    """
    Create initial state file for a new setup.

    This should be called after setting up account credentials.

    Args:
        qwen_dir: Path to .qwen directory.
        total_accounts: Total number of configured accounts.

    Returns:
        The created RotationState.
    """
    manager = AccountManager(qwen_dir=qwen_dir, total_accounts=total_accounts)
    state = RotationState(total_accounts=total_accounts)
    manager._write_state(state)
    return state
