"""
Qwen CLI Wrapper with Automatic Credential Rotation

This module wraps the qwen CLI with automatic retry and account
switching when quota exhaustion is detected.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Final

from qwen_credential.account_manager import (
    AccountManager,
    AccountNotFoundError,
    LockError,
)

logger = logging.getLogger(__name__)

# Quota/rate limit error patterns
QUOTA_PATTERNS: Final[tuple[str, ...]] = (
    "quota exhausted",
    "rate limit",
    "rate_limit",
    "quota exceeded",
    "usage limit",
    "insufficient quota",
    "rate-limited",
    "rate limited",
    "403",  # Forbidden - often quota
    "429",  # Too Many Requests
)


class CallResult(Enum):
    """Result of a Qwen wrapper call."""
    SUCCESS = "success"
    QUOTA_EXHAUSTED = "quota_exhausted"
    OTHER_ERROR = "other_error"
    ALL_EXHAUSTED = "all_accounts_exhausted"


@dataclass
class WrapperResult:
    """Result from QwenWrapper.call()."""
    success: bool
    output: str
    error: str | None = None
    attempts: int = 1
    accounts_tried: list[int] | None = None

    def __str__(self) -> str:
        if self.success:
            return f"Success after {self.attempts} attempt(s)"
        return f"Failed: {self.error or 'Unknown error'}"


class QwenWrapper:
    """
    Wrapper for qwen CLI with automatic credential rotation.

    Detects quota exhaustion errors and automatically switches to
    the next available account, retrying the request.

    Example:
        >>> wrapper = QwenWrapper()
        >>> result = wrapper.call("Analyze this code")
        >>> if result.success:
        ...     print(result.output)
    """

    def __init__(
        self,
        max_retries: int = 5,
        account_manager: AccountManager | None = None,
    ) -> None:
        """
        Initialize the QwenWrapper.

        Args:
            max_retries: Maximum number of account switches before giving up.
            account_manager: Custom AccountManager instance (for testing).
        """
        self.max_retries = max_retries
        self.account_manager = account_manager or AccountManager()

    def _is_quota_error(self, result: subprocess.CompletedProcess[str]) -> bool:
        """
        Check if subprocess result indicates a quota/rate limit error.

        Args:
            result: CompletedProcess from subprocess.run()

        Returns:
            True if error matches quota patterns.
        """
        combined = (result.stderr or "").lower() + (result.stdout or "").lower()
        return any(pattern in combined for pattern in QUOTA_PATTERNS)

    def _run_qwen(self, prompt: str, timeout: int) -> subprocess.CompletedProcess[str]:
        """
        Execute qwen CLI command.

        Args:
            prompt: Prompt to send to qwen.
            timeout: Command timeout in seconds.

        Returns:
            CompletedProcess result.
        """
        cmd = ["qwen", prompt, "--output-format", "text"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result
        except subprocess.TimeoutExpired as e:
            logger.error(f"Qwen command timed out after {timeout}s")
            # Return a fake error result
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
            )
        except FileNotFoundError:
            logger.error("qwen CLI not found. Is it installed?")
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=-2,
                stdout="",
                stderr="qwen CLI not found. Please install with: npm install -g @qwen-code/qwen-code",
            )
        except Exception as e:
            logger.error(f"Unexpected error running qwen: {e}")
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=-3,
                stdout="",
                stderr=f"Unexpected error: {e}",
            )

    def call(
        self,
        prompt: str,
        timeout: int = 45,
    ) -> WrapperResult:
        """
        Call qwen CLI with automatic account rotation on quota errors.

        Args:
            prompt: The prompt to send to qwen.
            timeout: Command timeout in seconds.

        Returns:
            WrapperResult with success status and output/error.
        """
        accounts_tried: list[int] = []
        self.account_manager.get_state()  # Get state for side effects (caching)

        for attempt in range(self.max_retries):
            # Track current account
            current_state = self.account_manager.get_state()
            current_account = current_state.current_index
            accounts_tried.append(current_account)

            logger.debug(
                f"Qwen call attempt {attempt + 1}/{self.max_retries} "
                f"(account {current_account})"
            )

            # Run qwen command
            result = self._run_qwen(prompt, timeout)

            # Check for quota errors
            if self._is_quota_error(result):
                logger.warning(
                    f"Quota exhausted on account {current_account} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )

                # Try switching to next account
                try:
                    switched, next_account = self.account_manager.switch_next()
                    if not switched:
                        logger.error("All accounts exhausted")
                        return WrapperResult(
                            success=False,
                            output="",
                            error="All Qwen accounts quota exhausted",
                            attempts=attempt + 1,
                            accounts_tried=accounts_tried,
                        )
                    logger.info(f"Switched to account {next_account}, retrying...")
                    continue

                except (AccountNotFoundError, LockError) as e:
                    logger.error(f"Failed to switch account: {e}")
                    return WrapperResult(
                        success=False,
                        output="",
                        error=f"Account switch failed: {e}",
                        attempts=attempt + 1,
                        accounts_tried=accounts_tried,
                    )

            # Success or other error - return result
            if result.returncode == 0:
                logger.debug(f"Qwen call succeeded on attempt {attempt + 1}")
                return WrapperResult(
                    success=True,
                    output=result.stdout or "",
                    attempts=attempt + 1,
                    accounts_tried=accounts_tried,
                )
            else:
                # Non-quota error - don't retry
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Qwen call failed: {error_msg}")
                return WrapperResult(
                    success=False,
                    output=result.stdout or "",
                    error=error_msg,
                    attempts=attempt + 1,
                    accounts_tried=accounts_tried,
                )

        # Max retries exceeded
        logger.error(f"Max retries ({self.max_retries}) exceeded")
        return WrapperResult(
            success=False,
            output="",
            error=f"Max retries ({self.max_retries}) exceeded",
            accounts_tried=accounts_tried,
        )

    def call_with_fallback(
        self,
        prompt: str,
        fallback_message: str = "AI analysis unavailable",
        timeout: int = 45,
    ) -> str:
        """
        Call qwen CLI with fallback message on failure.

        This is a convenience method for use in watcher.py where
        we want a simple string result.

        Args:
            prompt: The prompt to send to qwen.
            fallback_message: Message to return on failure.
            timeout: Command timeout in seconds.

        Returns:
            Qwen output or fallback message.
        """
        result = self.call(prompt, timeout)
        if result.success:
            return result.output
        return fallback_message

    def check_quota_status(self) -> dict[str, bool]:
        """
        Check quota status of all configured accounts.

        This performs a lightweight test call on each account to
        determine if it has available quota.

        Note: This is expensive as it requires N test calls.
        Consider caching results.

        Returns:
            Dict mapping account names to quota availability status.
        """
        state = self.account_manager.get_state()
        status: dict[str, bool] = {}
        starting_account = state.current_index

        # Test each account
        for i in range(1, state.total_accounts + 1):
            # Switch to account
            try:
                self.account_manager.switch_to(i)
            except (AccountNotFoundError, LockError) as e:
                logger.error(f"Cannot switch to account {i}: {e}")
                status[f"account{i}"] = False
                continue

            # Try a minimal call
            result = self._run_qwen("test", timeout=10)
            has_quota = not self._is_quota_error(result) and result.returncode == 0
            status[f"account{i}"] = has_quota

            logger.info(f"Account {i} quota status: {'available' if has_quota else 'exhausted'}")

        # Restore starting account
        try:
            self.account_manager.switch_to(starting_account)
        except (AccountNotFoundError, LockError):
            logger.warning(f"Could not restore account {starting_account}")

        return status
