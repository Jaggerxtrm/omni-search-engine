---
title: Qwen OAuth Credential Rotation System
version: 1.0.0
updated: 2026-02-05T23:59:00+01:00
status: implemented
scope: authentication, credential-rotation, qwen-cli
category: infra
subcategory: authentication
domain: [infra, authentication, reliability]
tags: [qwen, oauth, rotation, round-robin, atomic-operations]
changelog:
  - 1.0.0 (2026-02-05): Initial implementation. Automatic credential rotation for Qwen CLI with 5 accounts, atomic operations, and comprehensive testing.
---

# Qwen OAuth Credential Rotation System

## Objective
Provide automatic credential rotation when using the Qwen CLI with OAuth authentication. The system addresses quota exhaustion scenarios by implementing round-robin rotation across multiple Qwen accounts, with automatic failover and manual management utilities.

## 1. Architecture Overview

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
│  • Call qwen CLI                                                │
│  • Check for quota error patterns                               │
│  • If quota exhausted: call AccountManager.switch_next()        │
│  • Retry with new account                                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ switches
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      account_manager.py                          │
│  • Atomic symlink update with flock                             │
│  • Read/write state.yaml                                        │
│  • Audit logging to rotation.log                                │
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
```

## 2. Credential Storage Structure

### Directory Layout
```bash
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
```

## 3. Core Components

### AccountManager (`qwen_credential/account_manager.py`)

**Purpose:** Manages atomic account switching with file locking.

**Key Features:**
- Thread-safe operations using `fcntl.flock()`
- Atomic symlink updates via `os.replace()`
- State persistence in YAML format
- Audit logging with JSON entries

**Key Methods:**
- `switch_to(index: int)` - Switch to specific account
- `switch_next()` - Round-robin to next account
- `list_accounts()` - Get all accounts with status
- `get_stats()` - Get usage statistics

**Data Classes:**
```python
@dataclass
class RotationState:
    current_index: int = 1
    total_accounts: int = 5
    last_switch: str | None = None
    switches_total: int = 0
    accounts: dict[str, AccountStats] = field(default_factory=dict)
```

### QwenWrapper (`qwen_credential/qwen_wrapper.py`)

**Purpose:** Wrapper for Qwen CLI with automatic retry and rotation.

**Key Features:**
- Automatic quota pattern detection
- Retry with account switching on quota errors
- Configurable max retries
- Fallback message support

**Quota Detection Patterns:**
```python
QUOTA_PATTERNS = (
    "quota exhausted",
    "rate limit",
    "rate_limit",
    "quota exceeded",
    "usage limit",
    "insufficient quota",
    "rate-limited",
    "403",  # Forbidden
    "429",  # Too Many Requests
)
```

**Usage Example:**
```python
wrapper = QwenWrapper(max_retries=5)
result = wrapper.call_with_fallback(
    "Analyze this code",
    fallback_message="Analysis unavailable",
    timeout=45
)
```

### account-qwen CLI (`qwen_credential/account_qwen.py`)

**Purpose:** Management utility for credential operations.

**Commands:**
```bash
account-qwen --setup           # Interactive setup for initial accounts
account-qwen --list            # List all configured accounts with status
account-qwen --switch <index>  # Manually switch to specific account
account-qwen --switch-next     # Switch to next account (silent, for auto-rotation)
account-qwen --stats           # Display usage statistics
```

**Installation:**
```bash
# Alias in ~/.zshrc
alias account-qwen='PYTHONPATH=/path/to/project python -m qwen_credential.account_qwen'
```

## 4. Integration Points

### watcher.py Integration

**Two locations modified:**

1. **Git Commit Analysis** (~line 118):
```python
# OLD:
qwen_result = subprocess.run(["qwen", prompt, "--output-format", "text"], ...)
ai_analysis = qwen_result.stdout.strip() if qwen_result.returncode == 0 else "Could not generate summary."

# NEW:
ai_analysis = self.qwen_wrapper.call_with_fallback(
    prompt,
    fallback_message="Could not generate summary.",
    timeout=45
)
```

2. **File Change Analysis** (~line 299):
```python
# OLD:
qwen_result = subprocess.run(["qwen", prompt, "--output-format", "text"], ...)
summary = qwen_result.stdout.strip() if qwen_result.returncode == 0 else "Analysis failed"

# NEW:
summary = self.qwen_wrapper.call_with_fallback(
    prompt,
    fallback_message="Analysis failed",
    timeout=30
)
```

### Initialization in ShadowObserver.__init__
```python
from qwen_credential import QwenWrapper

# In __init__
self.qwen_wrapper = QwenWrapper(max_retries=5)
```

## 5. Data Flow

### Normal Operation
```
watcher.py → QwenWrapper.call(prompt)
           → subprocess.run(["qwen", prompt])
           → qwen CLI reads ~/.qwen/oauth_creds.json (points to account1)
           → Success
```

### Quota Exhausted Flow
```
watcher.py → QwenWrapper.call(prompt)
           → subprocess.run(["qwen", prompt])
           → Error: "quota exhausted"
           → QwenWrapper detects quota pattern
           → AccountManager.switch_next()
           → Symlink updated: oauth_creds.json → account2/oauth_creds_2.json
           → Retry: subprocess.run(["qwen", prompt])
           → Success with account2
```

## 6. Testing

### Test Coverage: 25/25 tests passing

**AccountManager Tests (13 tests):**
- State management and validation
- Atomic symlink operations
- Round-robin rotation logic
- Concurrent access safety (threading)
- Audit logging functionality

**QwenWrapper Tests (9 tests):**
- Quota pattern detection
- Automatic retry with account switching
- All accounts exhausted scenario
- Error handling (CLI not found, timeout)

**Integration Tests (2 tests):**
- End-to-end quota recovery
- State initialization

### Running Tests
```bash
cd /path/to/worktree
PYTHONPATH=. python -m pytest tests/test_qwen_credential.py -v
```

## 7. Docker Compatibility

**No changes needed to docker-compose.yml:**

The existing mount covers all credential rotation files:
```yaml
volumes:
  - ~/.qwen:/root/.qwen:rw,Z  # Includes accounts/, symlink, state, logs
```

## 8. Security Considerations

- **File Locking:** Uses `flock` to prevent concurrent modifications
- **Atomic Operations:** Symlink updates use `os.replace()` for atomicity
- **Credential Storage:** OAuth credentials stored in `~/.qwen/` (user directory)
- **Audit Trail:** All switches logged to `rotation.log`
- **No Hardcoded Secrets:** All credentials externalized

## 9. Limitations and Known Issues

1. **Qwen CLI Fixed Path:** As of Aug 2025, Qwen CLI does not respect custom credential paths - always uses `~/.qwen/oauth_creds.json`
2. **Manual Setup Required:** Each account requires interactive OAuth setup via browser
3. **No Quota Prediction:** System doesn't predict quota exhaustion - reactive only
4. **Python Dependency:** Requires Python 3.10+ for installation

## 10. Future Enhancements

### Short Term
- [ ] Per-account quota tracking (if API provides this info)
- [ ] Configurable backoff strategy (exponential delay)
- [ ] Webhook notifications for critical failures

### Long Term
- [ ] Generic credential rotation framework (openai, anthropic, etc.)
- [ ] Multi-CLI support pattern
- [ ] Dashboard/monitoring UI
- [ ] Standalone pip package distribution

## 11. References

### Design Document
- `docs/plans/2026-02-05-qwen-credential-rolling-design.md`

### Implementation Files
- `qwen_credential/account_manager.py` - Core rotation logic
- `qwen_credential/qwen_wrapper.py` - CLI wrapper with retry
- `qwen_credential/account_qwen.py` - Management CLI
- `watcher.py` - Integration points

### Tests
- `tests/test_qwen_credential.py` - Comprehensive test suite

### External Documentation
- Qwen CLI npm: `@qwen-code/qwen-code`
- Python atomic operations: `os.replace()`, `fcntl.flock()`
