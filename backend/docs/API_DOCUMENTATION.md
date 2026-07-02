# API Documentation

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.example.com` (update with actual domain)

## Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Getting Started

1. **Register** - Create a new account
2. **Login** - Get access and refresh tokens
3. **Use Access Token** - Include in `Authorization` header
4. **Refresh Token** - Get new access token when expired

### Authorization Header Format

```
Authorization: Bearer <access_token>
```

Example:
```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  http://localhost:8000/auth/me
```

## Response Format

### Success Response

```json
{
  "success": true,
  "data": {
    "field1": "value1",
    "field2": "value2"
  },
  "error": null
}
```

### Error Response

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": {
      "field": "email"
    }
  }
}
```

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| VALIDATION_ERROR | 422 | Input validation failed |
| AUTHENTICATION_ERROR | 401 | Invalid credentials or token |
| AUTHORIZATION_ERROR | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT_ERROR | 409 | Resource already exists (duplicate email/phone) |
| DATABASE_ERROR | 500 | Database operation failed |
| INTERNAL_SERVER_ERROR | 500 | Unexpected server error |

## Endpoints

### Authentication

#### 1. Register

Create a new citizen account.

**Endpoint:**
```
POST /auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "phone": "9876543210",
  "full_name": "John Doe",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!",
  "date_of_birth": "1990-01-15",
  "gender": "MALE",
  "district": "Chennai",
  "state": "Tamil Nadu"
}
```

**Field Validation:**
- `email` (required): Valid email address, max 254 characters
- `phone` (required): 10-digit Indian phone number (6-9 as first digit)
- `full_name` (required): 2-100 characters, letters and spaces only
- `password` (required): Min 8 chars, uppercase, lowercase, digit, special char
- `confirm_password` (required): Must match password
- `date_of_birth` (required): Format YYYY-MM-DD, age 18-120
- `gender` (required): MALE, FEMALE, or OTHER
- `district` (required): String, max 100 characters
- `state` (required): String, max 100 characters

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "citizen_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "phone": "9876543210",
    "full_name": "John Doe",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "error": null
}
```

**Error Cases:**
- **422**: Invalid email/phone/password format
- **409**: Email or phone already registered
- **500**: Database error

**Example:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "phone": "9876543210",
    "full_name": "John Doe",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "date_of_birth": "1990-01-15",
    "gender": "MALE",
    "district": "Chennai",
    "state": "Tamil Nadu"
  }'
```

---

#### 2. Login

Authenticate with email and password.

**Endpoint:**
```
POST /auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "citizen_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "error": null
}
```

**Error Cases:**
- **422**: Invalid email format
- **401**: Invalid email or password
- **403**: Account locked (too many failed attempts)
- **500**: Database error

**Example:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

---

#### 3. Refresh Token

Get a new access token using refresh token.

**Endpoint:**
```
POST /auth/refresh
```

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "error": null
}
```

**Error Cases:**
- **401**: Invalid or expired refresh token
- **500**: Database error

**Example:**
```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

---

#### 4. Get Current User Profile

Get the authenticated user's profile.

**Endpoint:**
```
GET /auth/me
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "citizen_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "phone": "9876543210",
    "full_name": "John Doe",
    "date_of_birth": "1990-01-15",
    "gender": "MALE",
    "district": "Chennai",
    "state": "Tamil Nadu",
    "account_status": "ACTIVE",
    "created_at": "2024-01-15T10:30:00Z",
    "last_login_at": "2024-01-16T14:45:30Z"
  },
  "error": null
}
```

**Error Cases:**
- **401**: Missing or invalid token
- **404**: User not found
- **500**: Database error

**Example:**
```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  http://localhost:8000/auth/me
```

---

#### 5. Update Profile

Update user profile information.

**Endpoint:**
```
PUT /auth/profile
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "full_name": "Jane Doe",
  "phone": "9876543210",
  "date_of_birth": "1990-01-15",
  "gender": "FEMALE",
  "district": "Mumbai",
  "state": "Maharashtra"
}
```

**Field Validation:**
- All fields optional
- Same validation rules as registration

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "citizen_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "phone": "9876543210",
    "full_name": "Jane Doe",
    "date_of_birth": "1990-01-15",
    "gender": "FEMALE",
    "district": "Mumbai",
    "state": "Maharashtra",
    "updated_at": "2024-01-16T15:00:00Z"
  },
  "error": null
}
```

**Error Cases:**
- **401**: Invalid token
- **422**: Invalid field values
- **409**: Phone already in use by another user
- **404**: User not found
- **500**: Database error

**Example:**
```bash
curl -X PUT http://localhost:8000/auth/profile \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Jane Doe",
    "district": "Mumbai",
    "state": "Maharashtra"
  }'
```

---

#### 6. Change Password

Change the user's password.

**Endpoint:**
```
PUT /auth/change-password
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "old_password": "SecurePass123!",
  "new_password": "NewSecurePass456!",
  "confirm_password": "NewSecurePass456!"
}
```

**Field Validation:**
- `old_password`: Must match current password
- `new_password`: Same rules as registration password
- `confirm_password`: Must match new_password
- `new_password` cannot be same as `old_password`

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Password changed successfully"
  },
  "error": null
}
```

**Error Cases:**
- **401**: Invalid token or wrong old password
- **422**: Invalid new password format
- **404**: User not found
- **500**: Database error

**Example:**
```bash
curl -X PUT http://localhost:8000/auth/change-password \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "SecurePass123!",
    "new_password": "NewSecurePass456!",
    "confirm_password": "NewSecurePass456!"
  }'
```

---

#### 7. Logout

Logout the user (audit logging).

**Endpoint:**
```
POST /auth/logout
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:** (Empty)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Logged out successfully"
  },
  "error": null
}
```

**Error Cases:**
- **401**: Invalid token
- **404**: User not found
- **500**: Database error

**Example:**
```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

---

#### 8. Verify Token

Verify if a token is valid.

**Endpoint:**
```
POST /auth/verify-token
```

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK - Valid):**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "citizen_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "expires_at": "2024-01-16T11:30:00Z"
  },
  "error": null
}
```

**Response (200 OK - Invalid):**
```json
{
  "success": true,
  "data": {
    "valid": false,
    "reason": "Token expired"
  },
  "error": null
}
```

**Error Cases:**
- **422**: Token missing or malformed
- **500**: Verification error

**Example:**
```bash
curl -X POST http://localhost:8000/auth/verify-token \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

---

### Health Check

#### 1. Health Status

Check if the API is running.

**Endpoint:**
```
GET /health
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "database": "connected",
    "timestamp": "2024-01-16T15:30:00Z"
  },
  "error": null
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

#### 2. Version Information

Get API version and build information.

**Endpoint:**
```
GET /version
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "version": "1.0.0",
    "build_date": "2024-01-15",
    "python_version": "3.11.0"
  },
  "error": null
}
```

**Example:**
```bash
curl http://localhost:8000/version
```

---

#### 3. API Information

Get detailed API information.

**Endpoint:**
```
GET /info
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "name": "Citizen Registration & Authentication API",
    "version": "1.0.0",
    "description": "Module 1 of AI-Powered Government Scheme Fulfillment Engine",
    "endpoints": 11,
    "database": "MySQL 8.0"
  },
  "error": null
}
```

**Example:**
```bash
curl http://localhost:8000/info
```

---

## Status Codes Reference

| Code | Status | When Used |
|------|--------|-----------|
| 200 | OK | Successful GET, POST (non-resource creation) |
| 201 | Created | Successful resource creation (registration) |
| 400 | Bad Request | Malformed request |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authentication valid but permission denied |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists (duplicate) |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Database offline |

## Data Types

### DateTime

ISO 8601 format:
```
2024-01-15T10:30:00Z
```

### UUID

36-character string:
```
550e8400-e29b-41d4-a716-446655440000
```

### Gender

Enum values:
- `MALE`
- `FEMALE`
- `OTHER`

### Account Status

Enum values:
- `ACTIVE` - Normal account
- `LOCKED` - Too many failed login attempts
- `INACTIVE` - Account deactivated by user or admin
- `SUSPENDED` - Administrative action

## Rate Limiting

Currently not implemented. Will be added in future versions.

Recommended limits:
- 100 requests per minute per IP
- 5 login attempts per minute per user
- 10 registration attempts per hour per IP

## Token Information

### Access Token

- **Expires in**: 30 minutes (configurable)
- **Contains**: citizen_id, email
- **Used for**: Authenticating API requests
- **Refresh**: Use refresh token to get new access token

### Refresh Token

- **Expires in**: 7 days (configurable)
- **Contains**: citizen_id
- **Used for**: Getting new access token
- **Revocation**: On password change, logout

## Examples

### Complete Registration & Login Flow

```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "phone": "9876543210",
    "full_name": "New User",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "date_of_birth": "1990-01-15",
    "gender": "MALE",
    "district": "Chennai",
    "state": "Tamil Nadu"
  }' > /tmp/register_response.json

# Extract access token
ACCESS_TOKEN=$(jq -r '.data.access_token' /tmp/register_response.json)

# 2. Get current user
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://localhost:8000/auth/me

# 3. Update profile
curl -X PUT http://localhost:8000/auth/profile \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Updated User"
  }'

# 4. Change password
curl -X PUT http://localhost:8000/auth/change-password \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "SecurePass123!",
    "new_password": "NewPass456!",
    "confirm_password": "NewPass456!"
  }'

# 5. Logout
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Interactive API Documentation

Visit these URLs in your browser:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Support

For issues or questions:
1. Check the [INSTALLATION.md](INSTALLATION.md)
2. Review the [AUTHENTICATION_FLOW.md](AUTHENTICATION_FLOW.md)
3. Check [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
4. Review logs in `logs/app.log`
