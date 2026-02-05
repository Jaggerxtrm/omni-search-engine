---
title: Qwen OAuth Credential Rolling System
version: 0.1.0
created: 2026-02-05
status: design
scope: authentication, credential-rotation, qwen-cli
domain: [infra, authentication, reliability]
tags: [qwen, oauth, rotation, round-robin, atomic-operations]
---

# Qwen OAuth Credential Rolling System - Design Document

## Executive Summary

This document describes a **Proof of Concept** system for automatic credential rotation when using the Qwen CLI with OAuth authentication. The system addresses quota exhaustion scenarios by implementing round-robin rotation across multiple Qwen accounts, with automatic failover and manual management utilities.

**Status:** Design phase - pending implementation and testing.

**Use Case Template:** This design serves as a reference pattern for any CLI-based tool requiring credential rotation with quota limits.

---

## Problem Statement

### Current Situation
- **Project:** omni-search-engine uses Qwen CLI for AI-powered change analysis in `watcher.py`
- **Authentication:** OAuth via `~/.qwen/oauth_creds.json` (single account)
- **Issue:** When quota is exhausted, the system fails completely
- **Manual Recovery:** User must re-authenticate manually, causing downtime

### Constraints Discovered
1. **Fixed Path Bug:** Qwen CLI (as of Aug 2025) does not respect custom credential paths - always uses `~/.qwen/oauth_creds.json`
2. **No Native Rotation:** CLI has no built-in account switching mechanism
3. **OAuth Flow:** Login happens on first `qwen` interaction, not via separate command

### Requirements
- **Automatic Detection:** Detect "quota exhausted" errors and switch accounts automatically
- **Manual Control:** CLI utility for listing, switching, and managing accounts
- **Round-Robin:** Rotate through 4-5 accounts cyclically (1→2→3→4→5→1...)
- **Atomic Operations:** No race conditions during credential switching
- **Docker Compatible:** Must work within containerized environment

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         watcher.py                               │
│                    (existing code)                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │ calls
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      qwen_wrapper.py                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Call qwen CLI                                        │  │
│  │  2. Check for quota error patterns                       │  │
│  │  3. If quota exhausted: call account-qwen --switch-next  │  │
│  │  4. Retry with new account                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ switches
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      account-qwen CLI                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Atomic symlink update with flock:                       │  │
│  │  1. Acquire lock                                        │  │
│  │  2. Read state.yaml for current index                   │  │
│  │  3. Calculate next index (round-robin)                  │  │
│  │  4. Validate target credential file exists              │  │
│  │  5. Create temp symlink                                 │  │
│  │  6. Atomic replace (os.replace)                         │  │
│  │  7. Update state.yaml                                   │  │
│  │  8. Release lock                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ updates
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ~/.qwen/ structure                            │
│  ├── accounts/                                                  │
│  │   ├── oauth_creds_1.json                                   │
│  │   ├── oauth_creds_2.json                                   │
│  │   ├── oauth_creds_3.json                                   │
│  │   ├── oauth_creds_4.json                                   │
│  │   └── oauth_creds_5.json                                   │
│  ├── oauth_creds.json → symlink to accounts/oauth_creds_N.json│
│  ├── state.yaml                                                │
│  └── rotation.log                                              │
└─────────────────────────────────────────────────────────────────┘
                            │ qwen CLI reads
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      qwen CLI (npm)                             │
│              Always reads ~/.qwen/oauth_creds.json              │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

**Normal Operation:**
```
watcher.py → qwen_wrapper.call(prompt)
           → subprocess.run(["qwen", prompt])
           → qwen CLI reads ~/.qwen/oauth_creds.json (points to account1)
           → Success
```

**Quota Exhausted Flow:**
```
watcher.py → qwen_wrapper.call(prompt)
           → subprocess.run(["qwen", prompt])
           → Error: "quota exhausted"
           → qwen_wrapper detects quota pattern
           → account_qwen.switch_next()
           → Symlink updated: oauth_creds.json → account2/oauth_creds_2.json
           → Retry: subprocess.run(["qwen", prompt])
           → Success with account2
```

---

## Credential Storage Structure

### Directory Layout
```
~/.qwen/
├── accounts/
│   ├── oauth_creds_1.json    # Account 1 credentials
│   ├── oauth_creds_2.json    # Account 2 credentials
│   ├── oauth_creds_3.json    # Account 3 credentials
│   ├── oauth_creds_4.json    # Account 4 credentials
│   └── oauth_creds_5.json    # Account 5 credentials
├── oauth_creds.json          # Symlink → accounts/oauth_creds_N.json
├── state.yaml                # Current account state
└── rotation.log              # Audit log of switches
```

### state.yaml Format
```yaml
current_index: 1              # Currently active account (1-indexed)
total_accounts: 5             # Total configured accounts
last_switch: "2026-02-05T10:30:00Z"
switches_total: 43            # Total rotations performed
accounts:                     # Per-account stats
  account1:
    switches_count: 15
    last_used: "2026-02-05T10:28:00Z"
  account2:
    switches_count: 8
    last_used: "2026-02-05T10:30:00Z"
  # ... etc
```

### rotation.log Format
```json
{"timestamp":"2026-02-05T10:30:00Z","level":"INFO","event":"account_switch",
 "from":1,"to":2,"reason":"quota_exhausted","trigger":"auto"}

{"timestamp":"2026-02-05T11:15:00Z","level":"INFO","event":"account_switch",
 "from":5,"to":1,"reason":"manual","trigger":"account-qwen --switch"}
```

---

## Component Specifications

### 1. account-qwen CLI

**Purpose:** Management utility for Qwen credential rotation.

**Commands:**

#### `account-qwen --setup`
Interactive setup for initial account configuration.

```bash
$ account-qwen --setup
Setting up Qwen account rotation (5 accounts)...

=== Account 1/5 ===
1. Open a NEW terminal
2. Run: qwen
3. Complete the OAuth login in browser
4. Press ENTER here when done...

[Verifying ~/.qwen/oauth_creds.json...]
✓ Credentials found! Saved as accounts/oauth_creds_1.json
✓ Cleaned up ~/.qwen/oauth_creds.json

=== Account 2/5 ===
...
```

**Implementation Notes:**
- Run `qwen` in separate terminal (OAuth requires browser interaction)
- After user presses ENTER, verify `~/.qwen/oauth_creds.json` exists
- Move file to `accounts/oauth_creds_N.json`
- Clean up `~/.qwen/oauth_creds.json` for next account
- Create initial `state.yaml`

#### `account-qwen --list`
List all configured accounts with status.

```bash
$ account-qwen --list
Available Qwen accounts:
  [1] account1 - ACTIVE (last used: 2m ago, 15 switches total)
  [2] account2 (last used: 3h ago, 8 switches total)
  [3] account3 (never used)
  [4] account4 (last used: 1d ago, 12 switches total)
  [5] account5 (last used: 5d ago, 5 switches total)
```

#### `account-qwen --switch <index>`
Manually switch to specific account.

```bash
$ account-qwen --switch 3
Switched from account1 to account3
Updated symlink: oauth_creds.json → accounts/oauth_creds_3.json
```

#### `account-qwen --switch-next`
Silent automatic switch (used by wrapper).

**Exit codes:**
- `0` - Success (switched to next account)
- `1` - All accounts exhausted (wrapped back to 1)

#### `account-qwen --stats`
Display usage statistics.

```bash
$ account-qwen --stats
Account Usage Statistics:
  account1: 15 switches (most used)
  account2: 8 switches
  account3: 3 switches
  account4: 12 switches
  account5: 5 switches
Total rotations: 43
Last rotation: 2 minutes ago
Current account: account1
```

---

### 2. qwen_wrapper.py

**Purpose:** Wrapper for Qwen CLI calls with automatic quota detection and retry.

```python
import subprocess
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("qwen_wrapper")

# Patterns indicating quota/rate limit errors
QUOTA_PATTERNS = [
    "quota exhausted",
    "rate limit",
    "rate_limit",
    "quota exceeded",
    "usage limit",
    "insufficient quota",
    "403",
    "429"
]

class QwenWrapper:
    """Wrapper for qwen CLI with automatic credential rotation on quota errors."""

    def __init__(self, max_retries: int = 5):
        self.max_retries = max_retries
        self.account_manager = AccountManager()

    def call(self, prompt: str, timeout: int = 45) -> Tuple[bool, str]:
        """
        Call qwen CLI with automatic account rotation on quota errors.

        Args:
            prompt: The prompt to send to qwen
            timeout: Command timeout in seconds

        Returns:
            (success, output) tuple
        """
        for attempt in range(self.max_retries):
            result = subprocess.run(
                ["qwen", prompt, "--output-format", "text"],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Check for quota errors
            if self._is_quota_error(result):
                logger.warning(
                    f"Quota exhausted on attempt {attempt + 1}/{self.max_retries}"
                )

                # Try switching to next account
                if not self.account_manager.switch_next():
                    logger.error("All accounts exhausted")
                    return False, result.stderr

                # Retry with new account
                logger.info("Retrying with new account")
                continue

            # Success or other error
            if result.returncode == 0:
                return True, result.stdout
            else:
                logger.error(f"Qwen failed: {result.stderr}")
                return False, result.stderr

        return False, "Max retries exceeded"

    def _is_quota_error(self, result: subprocess.CompletedProcess) -> bool:
        """Check if result indicates a quota/rate limit error."""
        combined = result.stderr.lower() + result.stdout.lower()
        return any(pattern in combined for pattern in QUOTA_PATTERNS)
```

**Integration in watcher.py:**

Replace direct subprocess calls:
```python
# OLD:
qwen_result = subprocess.run(["qwen", prompt, "--output-format", "text"],
                             capture_output=True, text=True, timeout=45)
ai_analysis = qwen_result.stdout.strip()

# NEW:
from qwen_wrapper import QwenWrapper
wrapper = QwenWrapper()
success, output = wrapper.call(prompt)
if success:
    ai_analysis = output
else:
    ai_analysis = "Could not generate summary."
```

---

### 3. AccountManager (Internal Module)

**Purpose:** Handles atomic account switching with locking.

```python
import fcntl
import os
import yaml
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger("account_manager")

class AccountManager:
    """Manages Qwen account rotation with atomic operations."""

    def __init__(self, qwen_dir: Path = None):
        self.qwen_dir = qwen_dir or Path.home() / ".qwen"
        self.state_file = self.qwen_dir / "state.yaml"
        self.lock_file = "/tmp/qwen_rotation.lock"

    def switch_next(self) -> bool:
        """
        Switch to next account in round-robin fashion.

        Returns:
            True if switched successfully, False if all accounts exhausted
        """
        with self._lock():
            state = self._read_state()
            current_index = state["current_index"]
            total_accounts = state["total_accounts"]

            # Calculate next index (round-robin)
            next_index = (current_index % total_accounts) + 1

            # Check if we've completed a full cycle
            if next_index == 1:
                logger.warning("All accounts exhausted, cycling back to account1")

            # Validate target credential file exists
            target_creds = self.qwen_dir / "accounts" / f"oauth_creds_{next_index}.json"
            if not target_creds.exists():
                raise FileNotFoundError(f"Account {next_index} credentials not found: {target_creds}")

            # Atomic symlink update
            self._atomic_symlink_update(target_creds)

            # Update state
            state["current_index"] = next_index
            state["last_switch"] = datetime.now().isoformat()
            state["switches_total"] = state.get("switches_total", 0) + 1
            self._write_state(state)

            self._log_switch(from_index=current_index, to_index=next_index, reason="auto")
            return True

    def _atomic_symlink_update(self, target: Path) -> None:
        """
        Atomically update the oauth_creds.json symlink.

        Uses os.replace() which is atomic on POSIX systems.
        """
        current_link = self.qwen_dir / "oauth_creds.json"
        temp_link = self.qwen_dir / "oauth_creds.json.tmp"

        # Create temp symlink
        if temp_link.exists():
            temp_link.unlink()
        temp_link.symlink_to(target)

        # Atomic replace
        os.replace(temp_link, current_link)

    def _lock(self):
        """Context manager for file locking."""
        class Lock:
            def __init__(self, lock_path):
                self.lock_path = lock_path
                self.lock_fd = None

            def __enter__(self):
                self.lock_fd = open(self.lock_path, 'w')
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX)
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()

        return Lock(self.lock_file)

    def _read_state(self) -> dict:
        """Read state.yaml, return defaults if not exists."""
        if not self.state_file.exists():
            return {
                "current_index": 1,
                "total_accounts": 5,
                "last_switch": None,
                "switches_total": 0,
                "accounts": {}
            }
        with open(self.state_file, 'r') as f:
            return yaml.safe_load(f)

    def _write_state(self, state: dict) -> None:
        """Write state.yaml atomically."""
        temp_file = self.state_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            yaml.dump(state, f, default_flow_style=False)
        os.replace(temp_file, self.state_file)

    def _log_switch(self, from_index: int, to_index: int, reason: str) -> None:
        """Log switch event to rotation.log."""
        import json
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "event": "account_switch",
            "from": from_index,
            "to": to_index,
            "reason": reason,
            "trigger": "auto" if reason == "auto" else "manual"
        }
        log_file = self.qwen_dir / "rotation.log"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
```

---

## Docker Integration

### docker-compose.yml
```yaml
services:
  omni-search-engine:
    build: .
    container_name: omni-search-engine
    environment:
      - OPENAI_API_KEY
      - OBSIDIAN_VAULT_PATH=/vault
      - CHROMADB_PATH=/data/chromadb
      - WATCH_MODE=true
      - SHADOW_AI_DEBOUNCE=30
    volumes:
      # Mount source code for development
      - .:/app:z
      # Mount the vault
      - ${VAULT_PATH:-/home/user/vault}:/vault:rw,Z
      # Persist ChromaDB data
      - chroma_data:/data/chromadb
      # Mount Qwen credentials (includes accounts, symlink, state)
      - ~/.qwen:/root/.qwen:rw,Z
    stdin_open: true
    tty: false
    command: ["python", "server.py", "--sse"]
    ports:
      - "8765:8765"

volumes:
  chroma_data:
```

**Note:** The single `~/.qwen:/root/.qwen` mount covers:
- `accounts/` directory with all credential files
- `oauth_creds.json` symlink
- `state.yaml`
- `rotation.log`

No Dockerfile changes needed - qwen CLI is already installed.

---

## Testing Strategy

### Unit Tests

#### Test 1: Atomic Symlink Update
```python
def test_atomic_symlink_update():
    """Verify symlink update is atomic and race-condition free."""
    manager = AccountManager(test_qwen_dir)

    # Create multiple threads attempting to switch simultaneously
    threads = []
    results = []

    def switch_thread():
        try:
            manager.switch_next()
            results.append("success")
        except Exception as e:
            results.append(f"error: {e}")

    for _ in range(10):
        t = threading.Thread(target=switch_thread)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Verify: no errors, final state is consistent
    assert "error" not in results
    assert Path(test_qwen_dir / "oauth_creds.json").exists()
```

#### Test 2: Quota Pattern Detection
```python
def test_quota_pattern_detection():
    """Verify all quota error patterns are correctly detected."""
    wrapper = QwenWrapper()

    quota_errors = [
        "Error: quota exhausted",
        "Rate limit exceeded (429)",
        "403 Forbidden - usage limit",
        "insufficient quota for this request"
    ]

    for error_msg in quota_errors:
        result = subprocess.CompletedProcess(
            args=["qwen", "test"],
            returncode=1,
            stdout=b"",
            stderr=error_msg.encode()
        )
        assert wrapper._is_quota_error(result), f"Failed to detect: {error_msg}"
```

#### Test 3: Round-Robin Rotation
```python
def test_round_robin_rotation():
    """Verify accounts rotate correctly in round-robin fashion."""
    manager = AccountManager(test_qwen_dir)

    # Setup: 3 accounts, starting at 1
    state = {"current_index": 1, "total_accounts": 3}
    manager._write_state(state)

    # Sequence: 1 → 2 → 3 → 1
    expected_sequence = [2, 3, 1]

    for expected in expected_sequence:
        manager.switch_next()
        actual = manager._read_state()["current_index"]
        assert actual == expected, f"Expected {expected}, got {actual}"
```

### Integration Tests

#### Test 4: End-to-End Quota Recovery
```bash
#!/bin/bash
# Simulate quota exhausted scenario

# Setup mock qwen that returns quota error on first call
export PATH="$TEST_MOCKS:$PATH"

# Run wrapper
python3 -c "
from qwen_wrapper import QwenWrapper
wrapper = QwenWrapper()
success, output = wrapper.call('test prompt')
assert success == True
assert 'account2' in output  # Verify switch happened
"
```

#### Test 5: Docker Credential Mount
```bash
#!/bin/bash
# Verify credentials are accessible inside container

docker-compose up -d
docker exec omni-search-engine ls -la /root/.qwen/
# Should show: accounts/, oauth_creds.json@, state.yaml

docker exec omni-search-engine cat /root/.qwen/oauth_creds.json
# Should show content of currently active account
```

### Manual Test: Real OAuth Flow
```bash
# 1. Run setup
account-qwen --setup

# 2. For each account, complete OAuth in separate terminal

# 3. Verify setup
account-qwen --list

# 4. Test rotation
account-qwen --switch 2
account-qwen --list  # Verify account2 is now ACTIVE

# 5. Test automatic rotation
# (Force a quota error scenario in watcher.py)
```

---

## Implementation Checklist

### Phase 1: Core Components
- [ ] Create `account-qwen` CLI script
  - [ ] `--setup` command (interactive OAuth setup)
  - [ ] `--list` command (display accounts)
  - [ ] `--switch <index>` command (manual switch)
  - [ ] `--switch-next` command (automatic, silent)
  - [ ] `--stats` command (usage statistics)

- [ ] Create `account_manager.py` module
  - [ ] Atomic symlink operations
  - [ ] File locking with flock
  - [ ] State persistence (state.yaml)
  - [ ] Audit logging (rotation.log)

- [ ] Create `qwen_wrapper.py`
  - [ ] Quota pattern detection
  - [ ] Automatic retry logic
  - [ ] Integration with AccountManager

### Phase 2: Integration
- [ ] Update `watcher.py`
  - [ ] Import QwenWrapper
  - [ ] Replace direct subprocess calls
  - [ ] Add error handling for wrapper failures

- [ ] Update `docker-compose.yml`
  - [ ] Verify `~/.qwen:/root/.qwen` mount exists

### Phase 3: Testing
- [ ] Write unit tests
  - [ ] Test atomic symlink operations
  - [ ] Test quota pattern detection
  - [ ] Test round-robin rotation
  - [ ] Test concurrent access (race conditions)

- [ ] Write integration tests
  - [ ] Test end-to-end quota recovery
  - [ ] Test Docker credential mount
  - [ ] Test with real OAuth flow

- [ ] Manual testing
  - [ ] Setup 4-5 real Qwen accounts
  - [ ] Trigger quota exhaustion scenario
  - [ ] Verify automatic rotation works

### Phase 4: Documentation
- [ ] Update SSOT with new credential system
- [ ] Add usage examples to README
- [ ] Document troubleshooting steps

---

## Future Enhancements (Post-PoC)

1. **Per-Account Quota Tracking**
   - Track remaining quota per account (if API provides this info)
   - Prioritize accounts with most available quota
   - Predictive switching before exhaustion

2. **Configurable Backoff Strategy**
   - Exponential backoff when all accounts exhausted
   - Configurable retry delays
   - Webhook notifications for critical failures

3. **Multi-CLI Support**
   - Abstract the pattern for other CLIs (openai, anthropic, etc.)
   - Generic credential rotation framework

4. **Dashboard/Monitoring**
   - Real-time view of active account
   - Usage metrics per account
   - Rotation history visualization

---

## References

### Qwen CLI Documentation
- npm package: `@qwen-code/qwen-code`
- OAuth credential location: `~/.qwen/oauth_creds.json`
- Known issue: Custom credential paths not respected (Aug 2025)

### Atomic Operations
- `os.replace()` for atomic file operations (Python 3.3+)
- `fcntl.flock()` for file locking

### Design Patterns Used
- **Wrapper Pattern:** qwen_wrapper.py encapsulates retry logic
- **State Machine:** AccountManager tracks current state
- **Template Method:** Setup flow for each account

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-02-05 | Initial design document - pending implementation |

---

## Appendix: Quick Reference

### Directory Structure After Setup
```
~/.qwen/
├── accounts/
│   ├── oauth_creds_1.json
│   ├── oauth_creds_2.json
│   ├── oauth_creds_3.json
│   ├── oauth_creds_4.json
│   └── oauth_creds_5.json
├── oauth_creds.json → accounts/oauth_creds_1.json
├── state.yaml
└── rotation.log
```

### Command Reference
```bash
# Setup (one-time)
account-qwen --setup

# List accounts
account-qwen --list

# Manual switch
account-qwen --switch 3

# View statistics
account-qwen --stats

# Automatic switch (used by wrapper)
account-qwen --switch-next
```

### Integration Code
```python
# In watcher.py
from qwen_wrapper import QwenWrapper

wrapper = QwenWrapper()
success, output = wrapper.call(prompt, timeout=45)
if success:
    ai_analysis = output
else:
    logger.error(f"Qwen failed after all retries: {output}")
    ai_analysis = "Analysis unavailable"
```

---

**Document Status:** 📝 Design - Ready for Implementation

**Next Steps:** Create isolated worktree, begin Phase 1 implementation.
