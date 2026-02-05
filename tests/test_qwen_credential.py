"""
Unit tests for Qwen credential rotation system.

Tests cover:
- Atomic symlink operations
- Quota pattern detection
- Round-robin rotation
- Concurrent access safety
"""

from __future__ import annotations

import json
import os
import threading
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import yaml

from qwen_credential.account_manager import (
    AccountManager,
    AccountNotFoundError,
    AccountStats,
    LockError,
    RotationState,
    SwitchReason,
    create_initial_state,
    DEFAULT_TOTAL_ACCOUNTS,
)
from qwen_credential.qwen_wrapper import (
    QwenWrapper,
    WrapperResult,
    QUOTA_PATTERNS,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_qwen_dir():
    """Create a temporary .qwen directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        qwen_dir = Path(tmpdir) / ".qwen"
        qwen_dir.mkdir()
        accounts_dir = qwen_dir / "accounts"
        accounts_dir.mkdir()

        # Create mock credential files
        for i in range(1, 6):
            creds_file = accounts_dir / f"oauth_creds_{i}.json"
            creds_file.write_text(json.dumps({"account": i, "token": f"token_{i}"}))

        # Create initial state
        state_file = qwen_dir / "state.yaml"
        initial_state = RotationState(
            current_index=1,
            total_accounts=5,
            accounts={f"account{i}": AccountStats() for i in range(1, 6)},
        )
        with open(state_file, "w") as f:
            yaml.dump(initial_state.to_dict(), f)

        # Create initial symlink
        creds_link = qwen_dir / "oauth_creds.json"
        creds_link.symlink_to(accounts_dir / "oauth_creds_1.json")

        yield qwen_dir


@pytest.fixture
def account_manager(temp_qwen_dir):
    """Create an AccountManager with temporary directory."""
    # Use a temp lock file to avoid conflicts
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".lock") as f:
        lock_path = f.name

    try:
        manager = AccountManager(qwen_dir=temp_qwen_dir)
        manager.lock_file = Path(lock_path)
        yield manager
    finally:
        try:
            os.unlink(lock_path)
        except FileNotFoundError:
            pass


# =============================================================================
# AccountManager Tests
# =============================================================================

class TestAccountManager:
    """Test suite for AccountManager class."""

    def test_get_state_returns_valid_state(self, account_manager):
        """Test that get_state returns a valid RotationState."""
        state = account_manager.get_state()

        assert isinstance(state, RotationState)
        assert state.current_index == 1
        assert state.total_accounts == 5
        assert state.switches_total == 0

    def test_get_state_returns_default_when_missing(self, temp_qwen_dir):
        """Test that get_state returns default state when file doesn't exist."""
        state_file = temp_qwen_dir / "state.yaml"
        state_file.unlink()

        manager = AccountManager(qwen_dir=temp_qwen_dir)
        state = manager.get_state()

        assert state.current_index == 1
        assert state.total_accounts == DEFAULT_TOTAL_ACCOUNTS

    def test_switch_to_specific_account(self, account_manager):
        """Test switching to a specific account by index."""
        result = account_manager.switch_to(3, reason=SwitchReason.MANUAL)

        assert result is True

        # Verify symlink was updated
        new_state = account_manager.get_state()
        assert new_state.current_index == 3

        # Verify symlink points to correct account
        link_target = account_manager.creds_link.resolve()
        assert link_target == account_manager.accounts_dir / "oauth_creds_3.json"

    def test_switch_to_invalid_index_raises_error(self, account_manager):
        """Test that switching to invalid index raises ValueError."""
        with pytest.raises(ValueError, match="Invalid account index"):
            account_manager.switch_to(0)

        with pytest.raises(ValueError, match="Invalid account index"):
            account_manager.switch_to(6)

    def test_switch_to_missing_account_raises_error(self, temp_qwen_dir):
        """Test that switching to non-existent account raises AccountNotFoundError."""
        # Delete account 3
        accounts_dir = temp_qwen_dir / "accounts"
        (accounts_dir / "oauth_creds_3.json").unlink()

        manager = AccountManager(qwen_dir=temp_qwen_dir)

        with pytest.raises(AccountNotFoundError):
            manager.switch_to(3)

    def test_switch_next_rotates_correctly(self, account_manager):
        """Test that switch_next rotates through accounts in round-robin fashion."""
        # Sequence: 1 → 2 → 3 → 4 → 5 → 1 (wrap)
        expected_sequence = [2, 3, 4, 5, 1]

        for expected in expected_sequence:
            switched, next_index = account_manager.switch_next()
            assert next_index == expected

            # Check if we wrapped around
            if expected == 1:
                assert not switched  # Should indicate all accounts were exhausted
            else:
                assert switched

    def test_switch_next_updates_stats(self, account_manager):
        """Test that switch_next updates account statistics."""
        account_manager.switch_next()
        state = account_manager.get_state()

        assert state.current_index == 2
        assert state.switches_total == 1
        assert "account2" in state.accounts
        assert state.accounts["account2"].switches_count == 1
        assert state.accounts["account2"].last_used is not None

    def test_list_accounts_returns_correct_info(self, account_manager):
        """Test that list_accounts returns correct account information."""
        accounts = account_manager.list_accounts()

        assert len(accounts) == 5
        assert accounts["account1"]["active"] is True
        assert accounts["account2"]["active"] is False
        assert accounts["account1"]["exists"] is True
        assert accounts["account1"]["index"] == 1

    def test_get_stats_returns_correct_summary(self, account_manager):
        """Test that get_stats returns correct usage statistics."""
        # Switch a few times to generate stats
        account_manager.switch_to(3)
        account_manager.switch_to(4)

        stats = account_manager.get_stats()

        assert stats["current_account"] == "account4"
        assert stats["total_switches"] == 2
        assert stats["accounts"]["account3"] == 1
        assert stats["accounts"]["account4"] == 1

    def test_atomic_symlink_update(self, account_manager):
        """Test that symlink update is atomic."""
        target = account_manager.accounts_dir / "oauth_creds_3.json"

        account_manager._atomic_symlink_update(target)

        # Verify symlink points to correct target
        link_target = account_manager.creds_link.resolve()
        assert link_target == target

    def test_write_state_is_atomic(self, account_manager):
        """Test that state writing is atomic (uses temp file)."""
        state = account_manager.get_state()
        state.current_index = 2
        state.switches_total = 42

        account_manager._write_state(state)

        # Verify file was written correctly
        with open(account_manager.state_file, "r") as f:
            data = yaml.safe_load(f)

        assert data["current_index"] == 2
        assert data["switches_total"] == 42

    def test_lock_prevents_concurrent_access(self, account_manager):
        """Test that file locking prevents concurrent modifications."""
        results = []
        errors = []

        def switch_thread(thread_id):
            try:
                for _ in range(5):
                    switched, next_index = account_manager.switch_next()
                    results.append((thread_id, next_index))
                    time.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                errors.append((thread_id, e))

        # Create multiple threads attempting to switch simultaneously
        threads = []
        for i in range(5):
            t = threading.Thread(target=switch_thread, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify final state is consistent
        final_state = account_manager.get_state()
        assert 1 <= final_state.current_index <= 5

    def test_rotation_log_is_written(self, account_manager):
        """Test that rotation events are logged correctly."""
        account_manager.switch_to(3, reason=SwitchReason.MANUAL)

        log_content = account_manager.log_file.read_text()
        logs = [json.loads(line) for line in log_content.strip().split("\n") if line]

        assert len(logs) == 1
        assert logs[0]["event"] == "account_switch"
        assert logs[0]["from"] == 1
        assert logs[0]["to"] == 3
        assert logs[0]["reason"] == "manual"

    def test_validate_account_exists_raises_error_when_missing(self, account_manager):
        """Test that _validate_account_exists raises error for missing accounts."""
        # Delete account 2
        (account_manager.accounts_dir / "oauth_creds_2.json").unlink()

        with pytest.raises(AccountNotFoundError):
            account_manager._validate_account_exists(2)


# =============================================================================
# QwenWrapper Tests
# =============================================================================

class TestQwenWrapper:
    """Test suite for QwenWrapper class."""

    @pytest.fixture
    def mock_account_manager(self):
        """Create a mock AccountManager for testing."""
        manager = Mock(spec=AccountManager)
        manager.get_state.return_value = RotationState(
            current_index=1,
            total_accounts=3,
        )
        return manager

    @pytest.fixture
    def wrapper(self, mock_account_manager):
        """Create a QwenWrapper with mock AccountManager."""
        return QwenWrapper(account_manager=mock_account_manager, max_retries=3)

    def test_quota_pattern_detection(self, wrapper):
        """Test that quota error patterns are correctly detected."""
        quota_errors = [
            "Error: quota exhausted",
            "Rate limit exceeded (429)",
            "403 Forbidden - usage limit",
            "insufficient quota for this request",
            "rate-limited",
        ]

        for error_msg in quota_errors:
            result = Mock()
            result.returncode = 1
            result.stderr = error_msg
            result.stdout = ""

            assert wrapper._is_quota_error(result), f"Failed to detect: {error_msg}"

    def test_non_quota_errors_not_detected(self, wrapper):
        """Test that non-quota errors are not flagged as quota errors."""
        non_quota_errors = [
            "Network error",
            "Invalid token",
            "500 Internal Server Error",
            "Connection refused",
        ]

        for error_msg in non_quota_errors:
            result = Mock()
            result.returncode = 1
            result.stderr = error_msg
            result.stdout = ""

            assert not wrapper._is_quota_error(result), f"False positive: {error_msg}"

    def test_successful_call_returns_result(self, wrapper):
        """Test that successful qwen call returns output."""
        with patch("qwen_credential.qwen_wrapper.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="AI generated response",
                stderr="",
            )

            result = wrapper.call("test prompt", timeout=30)

            assert result.success is True
            assert result.output == "AI generated response"
            assert result.attempts == 1

    def test_quota_error_triggers_account_switch(self, wrapper, mock_account_manager):
        """Test that quota error triggers account switch and retry."""
        # First call: quota error, second call: success
        mock_run_results = [
            Mock(returncode=1, stderr="quota exhausted", stdout=""),
            Mock(returncode=0, stdout="AI response", stderr=""),
        ]

        with patch("qwen_credential.qwen_wrapper.subprocess.run") as mock_run:
            mock_run.side_effect = mock_run_results
            mock_account_manager.switch_next.return_value = (True, 2)

            result = wrapper.call("test prompt", timeout=30)

            assert result.success is True
            assert result.output == "AI response"
            assert result.attempts == 2
            mock_account_manager.switch_next.assert_called_once()

    def test_all_accounts_exhausted_returns_failure(self, wrapper, mock_account_manager):
        """Test that exhausting all accounts returns failure."""
        # All quota errors
        mock_run_results = [
            Mock(returncode=1, stderr="quota exhausted", stdout=""),
            Mock(returncode=1, stderr="quota exhausted", stdout=""),
            Mock(returncode=1, stderr="quota exhausted", stdout=""),
        ]

        with patch("qwen_credential.qwen_wrapper.subprocess.run") as mock_run:
            mock_run.side_effect = mock_run_results
            # Last switch indicates all accounts exhausted
            mock_account_manager.switch_next.return_value = (False, 1)

            result = wrapper.call("test prompt", timeout=30)

            assert result.success is False
            assert "quota exhausted" in result.error.lower()

    def test_call_with_fallback_returns_output_on_success(self, wrapper):
        """Test that call_with_fallback returns output on success."""
        with patch("qwen_credential.qwen_wrapper.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="AI response",
                stderr="",
            )

            output = wrapper.call_with_fallback("test prompt", fallback_message="Fallback")

            assert output == "AI response"

    def test_call_with_fallback_returns_fallback_on_failure(self, wrapper):
        """Test that call_with_fallback returns fallback message on failure."""
        with patch("qwen_credential.qwen_wrapper.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Some error",
            )

            output = wrapper.call_with_fallback("test prompt", fallback_message="Fallback")

            assert output == "Fallback"

    def test_qwen_cli_not_found_returns_error(self, wrapper):
        """Test that missing qwen CLI returns appropriate error."""
        with patch("qwen_credential.qwen_wrapper.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = wrapper.call("test prompt", timeout=30)

            assert result.success is False
            assert "not found" in result.error

    def test_timeout_returns_error(self, wrapper):
        """Test that timeout returns appropriate error."""
        from subprocess import TimeoutExpired

        with patch("qwen_credential.qwen_wrapper.subprocess.run") as mock_run:
            mock_run.side_effect = TimeoutExpired(["qwen", "test"], 30)

            result = wrapper.call("test prompt", timeout=30)

            assert result.success is False
            assert "timed out" in result.error


# =============================================================================
# create_initial_state Tests
# =============================================================================

class TestCreateInitialState:
    """Test suite for create_initial_state function."""

    def test_creates_state_file(self, temp_qwen_dir):
        """Test that create_initial_state creates a valid state file."""
        # Remove existing state
        state_file = temp_qwen_dir / "state.yaml"
        if state_file.exists():
            state_file.unlink()

        state = create_initial_state(qwen_dir=temp_qwen_dir, total_accounts=3)

        assert state_file.exists()
        assert state.total_accounts == 3
        assert state.current_index == 1


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the full credential rotation system."""

    def test_end_to_end_quota_recovery(self, temp_qwen_dir):
        """Test full flow: quota error → account switch → retry → success."""
        manager = AccountManager(qwen_dir=temp_qwen_dir)
        wrapper = QwenWrapper(account_manager=manager, max_retries=3)

        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: quota error
                return Mock(returncode=1, stderr="quota exhausted", stdout="")
            else:
                # Second call: success
                return Mock(returncode=0, stdout="Success!", stderr="")

        with patch("qwen_credential.qwen_wrapper.subprocess.run", side_effect=mock_run):
            result = wrapper.call("test prompt")

        assert result.success is True
        assert result.output == "Success!"
        assert call_count == 2

        # Verify account was switched
        final_state = manager.get_state()
        assert final_state.current_index == 2


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
