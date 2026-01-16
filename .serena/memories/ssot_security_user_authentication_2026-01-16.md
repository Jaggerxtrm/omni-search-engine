---
title: SSOT User Authentication System
version: 0.1.0
updated: 2026-01-16T12:00:00+01:00
scope: security
category: security
subcategory: authentication
domain: [security, auth, user-management]
changelog:
  - 0.1.0 (2026-01-16): Initial documentation of user authentication feature
---

## Feature Overview
User authentication system providing secure login and logout functionality for the omni-search-engine MCP server. Enables user identity verification, session management, and access control for semantic search operations.

## Architecture

### Components
- **Authentication Service**: `services/auth_service.py` - Core business logic for credential validation
- **Session Manager**: `services/session_manager.py` - Handles session creation, validation, and expiration
- **Auth Models**: `models/auth_models.py` - Pydantic models for login requests, sessions, and user data
- **Auth Middleware**: Server-side middleware for request authentication and authorization
- **User Repository**: `repositories/user_repository.py` - Data access for user credentials and profiles

### Data Storage
- **User Credentials**: Stored securely with hashed passwords (bcrypt/argon2)
- **Active Sessions**: In-memory or Redis-backed session storage with TTL
- **Session Metadata**: Login timestamp, last activity, user agent, IP address

## Login Flow

### Process Sequence
1. **Credential Submission**: Client sends login request with username/password
2. **Validation**: Auth service validates input format and required fields
3. **Credential Verification**: Retrieves user record and verifies password hash
4. **Session Creation**: Generates unique session token with expiration
5. **Response**: Returns session token and user profile to client

### Login Endpoint
- **MCP Tool**: `login`
- **Inputs**: `username` (str), `password` (str)
- **Output**: Session token, user profile, expiration timestamp
- **Error Handling**: Invalid credentials, account locked, rate limiting

### Security Measures
- Password hashing with salt (bcrypt work factor >= 12)
- Rate limiting on login attempts (5 attempts per 15 minutes)
- Account lockout after failed attempts (30 minute cooldown)
- Session token generation using cryptographically secure RNG
- No password logging or exposure in error messages

## Logout Flow

### Process Sequence
1. **Session Validation**: Verifies session token is valid and active
2. **Session Invalidation**: Removes session from active session store
3. **Cleanup**: Clears any associated temporary data or caches
4. **Confirmation**: Returns success response to client

### Logout Endpoint
- **MCP Tool**: `logout`
- **Inputs**: `session_token` (str)
- **Output**: Success status, timestamp
- **Error Handling**: Invalid session token, session already expired

## Session Management

### Session Lifecycle
- **Creation**: Upon successful login
- **Validation**: On each authenticated request
- **Refresh**: Optional token refresh mechanism
- **Expiration**: Default 24-hour inactivity timeout
- **Destruction**: On explicit logout or expiration

### Session Token Structure
- **Format**: UUID v4 or JWT (JSON Web Token)
- **Storage**: Client-side (Bearer token) or secure HTTP-only cookie
- **Payload**: User ID, role, creation timestamp, expiration
- **Signing**: HMAC-SHA256 or asymmetric key (RSA)

### Authentication Middleware
- **Request Interception**: Validates session token on protected endpoints
- **User Context Injection**: Adds user information to request context
- **Session Refresh**: Automatic refresh for active sessions
- **Audit Logging**: Tracks authentication events for security monitoring

## Configuration

### Environment Variables
- `AUTH_ENABLED`: Enable/disable authentication (default: false for local dev)
- `SESSION_TTL_MINUTES`: Session timeout in minutes (default: 1440)
- `MAX_LOGIN_ATTEMPTS`: Failed attempt threshold (default: 5)
- `LOCKOUT_DURATION_MINUTES`: Account lockout duration (default: 30)
- `JWT_SECRET`: Secret key for token signing (required for JWT mode)
- `PASSWORD_HASH_ROUNDS`: Bcrypt work factor (default: 12)

### Settings Schema
See `settings.py` for `AuthConfig` Pydantic model with validation rules.

## User Roles & Permissions

### Role Types
- **admin**: Full system access, user management, configuration changes
- **user**: Standard search and indexing access
- **readonly**: Read-only search access, no indexing operations

### Permission Matrix
| Operation        | Admin | User | Readonly |
|------------------|-------|------|----------|
| semantic_search  | ✓     | ✓    | ✓        |
| reindex_vault    | ✓     | ✓    | ✗        |
| index_note       | ✓     | ✓    | ✗        |
| suggest_links    | ✓     | ✓    | ✗        |
| get_index_stats  | ✓     | ✓    | ✓        |
| user_management  | ✓     | ✗    | ✗        |

## Security Considerations

### Best Practices Implemented
- Credentials never logged or exposed in error messages
- All authentication operations use async/await for non-blocking I/O
- Session tokens are stored securely with HTTP-only, Secure, SameSite flags
- Password requirements enforced (min 8 chars, mixed case, numbers/symbols)
- Timing attack prevention on credential verification
- Audit trail for all authentication events (login, logout, failures)

### Threat Mitigation
- **Brute Force**: Rate limiting and account lockout
- **Session Hijacking**: Secure token storage, IP validation (optional)
- **CSRF**: SameSite cookie policy, token validation
- **XSS**: Input sanitization, output encoding
- **Replay Attacks**: Session expiration, token binding to client attributes

## Integration Points

### Protected MCP Tools
The following tools require authentication when `AUTH_ENABLED=true`:
- `semantic_search`
- `reindex_vault`
- `index_note`
- `suggest_links`
- `get_vault_structure`
- `search_notes`

### Public Tools
These tools remain available without authentication:
- `login`
- `logout`
- `get_index_stats` (diagnostic)

## Dependencies
- `passlib`: Password hashing library
- `bcrypt`: Cryptographic password hashing
- `pyjwt`: JWT token generation and validation (if using JWT)
- `python-dateutil`: Session timestamp handling
- `redis` (optional): Distributed session storage

## Testing
- Unit tests for password hashing/verification
- Integration tests for login/logout flows
- Session expiration and refresh tests
- Rate limiting and lockout behavior tests
- Security tests for common attack vectors

## Future Enhancements
- Multi-factor authentication (MFA/2FA)
- OAuth2/OIDC integration for external identity providers
- Password reset flow via email
- User self-registration (with approval workflow)
- Session revocation and audit UI
- LDAP/Active Directory integration
