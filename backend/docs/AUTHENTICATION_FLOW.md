# Authentication Flow Diagram

## 1. Registration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    REGISTRATION FLOW                            │
└─────────────────────────────────────────────────────────────────┘

Client                          API Server                   Database
  │                               │                            │
  │──── 1. POST /auth/register ──>│                            │
  │      (email, phone, password) │                            │
  │                               │                            │
  │                               ├─ 2. Validate inputs       │
  │                               │    (email, phone, name)    │
  │                               │                            │
  │                               ├─ 3. Check uniqueness       │
  │                               ├───────────────────────────>│
  │                               │<─── exists? ──────────────│
  │                               │                            │
  │                               ├─ 4. Hash password          │
  │                               │    (bcrypt rounds: 12)     │
  │                               │                            │
  │                               ├─ 5. Create citizen record  │
  │                               ├───────────────────────────>│
  │                               │<─── citizen_id ───────────│
  │                               │                            │
  │                               ├─ 6. Generate tokens        │
  │                               │    (JWT access + refresh)  │
  │                               │                            │
  │<── 7. 201 Created ────────────│                            │
  │      {access_token,           │                            │
  │       refresh_token}          │                            │
  │                               │                            │

Response Format:
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "citizen_id": "uuid",
    "email": "citizen@example.com",
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

## 2. Login Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      LOGIN FLOW                                 │
└─────────────────────────────────────────────────────────────────┘

Client                          API Server                   Database
  │                               │                            │
  │──── 1. POST /auth/login ─────>│                            │
  │      (email, password)        │                            │
  │                               │                            │
  │                               ├─ 2. Validate email format  │
  │                               │                            │
  │                               ├─ 3. Fetch citizen          │
  │                               ├───────────────────────────>│
  │                               │<─── citizen record ───────│
  │                               │                            │
  │                               ├─ 4. Check account status   │
  │                               │    (active, not locked)    │
  │                               │                            │
  │                               ├─ 5. Verify password        │
  │                               │    (bcrypt compare)        │
  │                               │                            │
  │          If INCORRECT:                                      │
  │                               ├─ Increment failed attempts │
  │                               ├───────────────────────────>│
  │<── 401 Unauthorized ──────────│                            │
  │      "Invalid credentials"    │                            │
  │                               │                            │
  │          If CORRECT:                                        │
  │                               ├─ Reset failed attempts     │
  │                               ├─ Update last_login         │
  │                               ├───────────────────────────>│
  │                               │<─── ✓ Updated ───────────│
  │                               │                            │
  │                               ├─ Generate tokens           │
  │                               │    (JWT access + refresh)  │
  │                               │                            │
  │<── 200 OK ────────────────────│                            │
  │      {access_token,           │                            │
  │       refresh_token}          │                            │
  │                               │                            │

Response Format (Success):
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

## 3. Protected API Request Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              PROTECTED API REQUEST FLOW                         │
└─────────────────────────────────────────────────────────────────┘

Client                          API Server                   Database
  │                               │                            │
  │──── 1. GET /auth/me ──────────>│                            │
  │      Authorization: Bearer     │                            │
  │      <access_token>            │                            │
  │                               │                            │
  │                               ├─ 2. Extract token          │
  │                               │    from Authorization header│
  │                               │                            │
  │                               ├─ 3. Decode JWT             │
  │                               │    (verify signature)      │
  │                               │                            │
  │          If INVALID:                                        │
  │<── 401 Unauthorized ──────────│                            │
  │      "Invalid or expired"     │                            │
  │                               │                            │
  │          If VALID:                                          │
  │                               ├─ 4. Extract citizen_id     │
  │                               │    from token payload      │
  │                               │                            │
  │                               ├─ 5. Fetch citizen profile  │
  │                               ├───────────────────────────>│
  │                               │<─── citizen data ─────────│
  │                               │                            │
  │<── 200 OK ────────────────────│                            │
  │      {citizen profile}        │                            │
  │                               │                            │

Token Payload:
{
  "sub": "citizen_id",          // Subject (citizen ID)
  "email": "citizen@example.com",
  "role": "citizen",
  "exp": 1234567890,            // Expiry time (Unix timestamp)
  "type": "access"              // Token type
}
```

## 4. Token Refresh Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              TOKEN REFRESH FLOW                                 │
└─────────────────────────────────────────────────────────────────┘

Client                          API Server
  │                               │
  │──── 1. POST /auth/refresh ────>│
  │      {refresh_token}          │
  │                               │
  │                               ├─ 2. Verify refresh token   │
  │                               │    (check expiry, type)    │
  │                               │                            │
  │          If INVALID:                                        │
  │<── 401 Unauthorized ──────────│                            │
  │                               │                            │
  │          If VALID:                                          │
  │                               ├─ 3. Extract citizen_id     │
  │                               │                            │
  │                               ├─ 4. Generate new tokens    │
  │                               │    (access + refresh)      │
  │                               │                            │
  │<── 200 OK ────────────────────│                            │
  │      {access_token,           │                            │
  │       refresh_token}          │                            │
  │                               │                            │

Token Lifetimes:
- Access Token:  30 minutes (short-lived)
- Refresh Token: 7 days (long-lived)
```

## 5. Account Locking Flow

```
┌─────────────────────────────────────────────────────────────────┐
│            ACCOUNT LOCKING FLOW                                 │
└─────────────────────────────────────────────────────────────────┘

Failed Login Attempts (per user):

Attempt 1 ──> failed_attempts = 1 ──> ✓ Continue
  │
Attempt 2 ──> failed_attempts = 2 ──> ✓ Continue
  │
Attempt 3 ──> failed_attempts = 3 ──> ✓ Continue
  │
Attempt 4 ──> failed_attempts = 4 ──> ✓ Continue
  │
Attempt 5 ──> failed_attempts = 5 ──> account_locked = TRUE
  │
Attempt 6+ ──> ✗ ACCOUNT LOCKED
            └─> 401 "Account is locked due to multiple failed attempts"
              └─> Requires admin intervention to unlock

Successful Login ──> failed_attempts = 0 (reset)
                  └─> account_locked = FALSE (unlocked)
```

## 6. Password Change Flow

```
┌─────────────────────────────────────────────────────────────────┐
│            PASSWORD CHANGE FLOW                                 │
└─────────────────────────────────────────────────────────────────┘

Client                          API Server                   Database
  │                               │                            │
  │──── 1. PUT /auth/change-pass ->│                            │
  │      {old_pwd, new_pwd}       │                            │
  │      Authorization: Bearer    │                            │
  │                               │                            │
  │                               ├─ 2. Get authenticated user │
  │                               ├───────────────────────────>│
  │                               │<─── citizen record ───────│
  │                               │                            │
  │                               ├─ 3. Verify old password    │
  │                               │                            │
  │          If INCORRECT:                                      │
  │<── 401 Unauthorized ──────────│                            │
  │                               │                            │
  │          If CORRECT:                                        │
  │                               ├─ 4. Validate new password  │
  │                               │    (strength rules)        │
  │                               │                            │
  │                               ├─ 5. Hash new password      │
  │                               │    (bcrypt)               │
  │                               │                            │
  │                               ├─ 6. Update in database     │
  │                               ├───────────────────────────>│
  │                               │<─── ✓ Updated ───────────│
  │                               │                            │
  │<── 200 OK ────────────────────│                            │
  │      "Password changed"       │                            │
  │                               │                            │
```

## Security Notes

### Token Security
1. **Tokens in Transit**: Use HTTPS to prevent interception
2. **Token Storage**: Store in secure HTTP-only cookies or localStorage
3. **Token Expiry**: Access tokens expire in 30 minutes, requiring refresh
4. **Refresh Tokens**: Longer-lived but should also be rotated

### Password Security
1. **Hashing**: Bcrypt with 12 rounds provides strong protection
2. **No Plaintext**: Passwords never stored or logged as plaintext
3. **Strong Policy**: Enforce uppercase, lowercase, digits, special chars
4. **Minimum Length**: 8 characters minimum (configurable)

### Attack Prevention
1. **Brute Force**: Account locking after 5 failed attempts
2. **SQL Injection**: SQLAlchemy ORM parameterized queries
3. **CORS**: Restricted to whitelisted origins
4. **XSS**: JSON responses validate structure

### Audit Trail
All authentication events are logged:
- Successful logins (timestamp, IP)
- Failed attempts (reason, IP)
- Password changes
- Token generation
- Account status changes
