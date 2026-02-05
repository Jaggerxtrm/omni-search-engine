"""
Qwen Credential Rotation Package

This package provides automatic OAuth credential rotation for the Qwen CLI
when quota is exhausted. It includes:
- AccountManager: Atomic account switching with file locking
- QwenWrapper: Wrapper with automatic retry and rotation
- account_qwen CLI: Management utility
"""

from qwen_credential.account_manager import (
    DEFAULT_LOCK_FILE,
    DEFAULT_QWEN_DIR,
    DEFAULT_TOTAL_ACCOUNTS,
    ACCOUNTS_DIR_NAME,
    OAUTH_CREDS_LINK,
    STATE_FILE,
    ROTATION_LOG,
    AccountManager,
    AccountNotFoundError,
    AccountStats,
    LockError,
    RotationState,
    SwitchReason,
    create_initial_state,
)

from qwen_credential.qwen_wrapper import (
    QUOTA_PATTERNS,
    CallResult,
    QwenWrapper,
    WrapperResult,
)

__all__ = [
    # AccountManager
    "AccountManager",
    "AccountNotFoundError",
    "AccountStats",
    "LockError",
    "RotationState",
    "SwitchReason",
    "create_initial_state",
    # Constants
    "DEFAULT_LOCK_FILE",
    "DEFAULT_QWEN_DIR",
    "DEFAULT_TOTAL_ACCOUNTS",
    "ACCOUNTS_DIR_NAME",
    "OAUTH_CREDS_LINK",
    "STATE_FILE",
    "ROTATION_LOG",
    # QwenWrapper
    "QwenWrapper",
    "WrapperResult",
    "CallResult",
    "QUOTA_PATTERNS",
]

__version__ = "0.1.0"
