# Environment Variables Documentation

## Overview

The application uses environment variables for configuration. Copy `.env.example` to `.env` and update values for your environment.

## Database Configuration

### DATABASE_URL
- **Type**: String
- **Default**: `mysql+pymysql://root:password@localhost:3306/citizen_auth_db`
- **Description**: Database connection string
- **Format**: `mysql+pymysql://[username]:[password]@[host]:[port]/[database]`
- **Example**: 
  ```env
  DATABASE_URL=mysql+pymysql://root:password@mysql:3306/citizen_auth_db
  ```

### SQLALCHEMY_ECHO
- **Type**: Boolean
- **Default**: `False`
- **Description**: Log all SQL statements (development only)
- **Values**: `True` or `False`

### SQLALCHEMY_POOL_SIZE
- **Type**: Integer
- **Default**: `20`
- **Description**: Number of database connections in pool
- **Recommended**: `10-20` for small apps, `30-50` for large apps

### SQLALCHEMY_POOL_RECYCLE
- **Type**: Integer (seconds)
- **Default**: `3600`
- **Description**: Recycle database connections after N seconds
- **Prevents**: Connection timeout issues

## Environment

### ENVIRONMENT
- **Type**: String
- **Default**: `development`
- **Values**: `development`, `staging`, `production`
- **Description**: Current environment
- **Example**: `ENVIRONMENT=production`

### DEBUG
- **Type**: Boolean
- **Default**: `True` (development), `False` (production)
- **Description**: Enable debug mode
- **WARNING**: Always set to `False` in production

## Server Configuration

### SERVER_HOST
- **Type**: String
- **Default**: `0.0.0.0`
- **Description**: Server host to bind to
- **Values**: `0.0.0.0` (all interfaces), `localhost`, or specific IP

### SERVER_PORT
- **Type**: Integer
- **Default**: `8000`
- **Description**: Server port
- **Common Ports**: `8000`, `8080`, `3000`, `5000`

### SERVER_RELOAD
- **Type**: Boolean
- **Default**: `True` (development), `False` (production)
- **Description**: Auto-reload on code changes
- **Note**: Disable in production for performance

## JWT Configuration

### SECRET_KEY
- **Type**: String
- **Default**: `your-super-secret-key-change-this-in-production`
- **Length**: Minimum 32 characters recommended
- **Description**: Secret key for JWT signing
- **IMPORTANT**: Change this in production!
- **Recommendation**: Use `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### ALGORITHM
- **Type**: String
- **Default**: `HS256`
- **Values**: `HS256`, `HS512`, `RS256` (if using RSA)
- **Description**: JWT signing algorithm

### ACCESS_TOKEN_EXPIRE_MINUTES
- **Type**: Integer
- **Default**: `30`
- **Description**: Access token expiry in minutes
- **Recommendation**: `15-60` minutes
- **Formula**: Shorter = More secure, Longer = Better UX

### REFRESH_TOKEN_EXPIRE_DAYS
- **Type**: Integer
- **Default**: `7`
- **Description**: Refresh token expiry in days
- **Recommendation**: `7-30` days

## Security Configuration

### CORS_ORIGINS
- **Type**: JSON List
- **Default**: `["http://localhost:3000", "http://localhost:8080"]`
- **Description**: Allowed CORS origins
- **Format**: `["http://domain1.com", "http://domain2.com"]`
- **Example**:
  ```env
  CORS_ORIGINS=["http://localhost:3000","https://example.com"]
  ```
- **Wildcard**: `["*"]` (NOT recommended for production)

### CORS_ALLOW_CREDENTIALS
- **Type**: Boolean
- **Default**: `True`
- **Description**: Allow credentials (cookies, auth headers)

### CORS_ALLOW_METHODS
- **Type**: JSON List
- **Default**: `["*"]`
- **Description**: Allowed HTTP methods
- **Example**: `["GET", "POST", "PUT", "DELETE"]`

### CORS_ALLOW_HEADERS
- **Type**: JSON List
- **Default**: `["*"]`
- **Description**: Allowed request headers
- **Example**: `["Content-Type", "Authorization"]`

## Password Policy

### MIN_PASSWORD_LENGTH
- **Type**: Integer
- **Default**: `8`
- **Description**: Minimum password length
- **Range**: `8-32` recommended

### REQUIRE_UPPERCASE
- **Type**: Boolean
- **Default**: `True`
- **Description**: Require uppercase letters (A-Z)

### REQUIRE_LOWERCASE
- **Type**: Boolean
- **Default**: `True`
- **Description**: Require lowercase letters (a-z)

### REQUIRE_DIGITS
- **Type**: Boolean
- **Default**: `True`
- **Description**: Require digits (0-9)

### REQUIRE_SPECIAL_CHARS
- **Type**: Boolean
- **Default**: `True`
- **Description**: Require special characters (!@#$%^&*)

## Email Configuration

### ALLOWED_EMAIL_DOMAINS
- **Type**: JSON List
- **Default**: `["*"]`
- **Description**: Allowed email domains
- **Restrictions**: `["@example.com", "@company.gov.in"]`
- **Wildcard**: `["*"]` allows all domains

## Logging Configuration

### LOG_DIR
- **Type**: String
- **Default**: `logs`
- **Description**: Directory for log files
- **Create Automatically**: Yes

### LOG_FILE
- **Type**: String
- **Default**: `app.log`
- **Description**: Main log file name

### LOG_LEVEL
- **Type**: String
- **Default**: `INFO`
- **Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Recommended**: `INFO` (production), `DEBUG` (development)

### LOG_FORMAT
- **Type**: String
- **Default**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Description**: Log message format
- **Variables**: `%(asctime)s`, `%(name)s`, `%(levelname)s`, `%(message)s`

## File Upload Configuration

### MAX_UPLOAD_SIZE_MB
- **Type**: Integer
- **Default**: `10`
- **Description**: Maximum file upload size in MB
- **Future Module**: Module 7 (PDF Generation)

### UPLOAD_DIR
- **Type**: String
- **Default**: `uploads`
- **Description**: Directory for uploaded files
- **Future Module**: Module 7 (PDF Generation)

## API Documentation

### DOCS_URL
- **Type**: String
- **Default**: `/docs`
- **Description**: Swagger UI documentation URL
- **Disable**: Set to `None` to disable

### REDOC_URL
- **Type**: String
- **Default**: `/redoc`
- **Description**: ReDoc documentation URL
- **Disable**: Set to `None` to disable

### OPENAPI_URL
- **Type**: String
- **Default**: `/openapi.json`
- **Description**: OpenAPI schema URL
- **Disable**: Set to `None` to disable

## Feature Flags

### ENABLE_AADHAAR_VALIDATION
- **Type**: Boolean
- **Default**: `True`
- **Description**: Enable Aadhaar validation
- **Future**: Could disable for MVP

### ENABLE_RATION_CARD_VALIDATION
- **Type**: Boolean
- **Default**: `True`
- **Description**: Enable Ration Card validation

### ENABLE_AUDIT_LOGGING
- **Type**: Boolean
- **Default**: `True`
- **Description**: Enable detailed audit logging

## Configuration Examples

### Development Configuration

```env
# Database
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/citizen_auth_db
SQLALCHEMY_ECHO=True

# Environment
ENVIRONMENT=development
DEBUG=True

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_RELOAD=True

# JWT
SECRET_KEY=dev-secret-key-not-for-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Logging
LOG_LEVEL=DEBUG

# Features
ENABLE_AADHAAR_VALIDATION=True
ENABLE_AUDIT_LOGGING=True
```

### Staging Configuration

```env
# Database
DATABASE_URL=mysql+pymysql://user:pass@staging-db.example.com:3306/citizen_auth_db
SQLALCHEMY_ECHO=False

# Environment
ENVIRONMENT=staging
DEBUG=False

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_RELOAD=False

# JWT
SECRET_KEY=staging-secret-key-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=["https://staging.example.com"]

# Logging
LOG_LEVEL=INFO
```

### Production Configuration

```env
# Database
DATABASE_URL=mysql+pymysql://prod_user:secure_password@prod-db.example.com:3306/citizen_auth_prod
SQLALCHEMY_ECHO=False
SQLALCHEMY_POOL_SIZE=30

# Environment
ENVIRONMENT=production
DEBUG=False

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_RELOAD=False

# JWT
SECRET_KEY=generate-this-with-secrets-module-very-long-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=["https://example.com", "https://app.example.com"]

# Logging
LOG_LEVEL=WARNING
LOG_DIR=/var/log/citizen-auth

# Features
ENABLE_AUDIT_LOGGING=True
```

## Generating Secure Keys

### Generate SECRET_KEY

```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32

# Using Linux /dev/urandom
head -c 32 /dev/urandom | base64
```

### Example Output
```
ABC-DEF_1234567890abcdefghijklmn
```

## Common Issues

### Database Connection Failed
- Check `DATABASE_URL` format
- Verify MySQL is running
- Check credentials and permissions
- Check host and port

### Port Already in Use
- Change `SERVER_PORT` to unused port
- Or kill process using the port

### JWT Token Invalid
- Verify `SECRET_KEY` hasn't changed
- Check token hasn't expired
- Check `ALGORITHM` matches

### CORS Errors
- Add origin to `CORS_ORIGINS`
- Check origin format (include protocol)
- Verify browser is sending correct origin

## Validation

Verify configuration before running:

```python
# Check settings
from app.core.config import settings

print(f"Environment: {settings.ENVIRONMENT}")
print(f"Debug: {settings.DEBUG}")
print(f"Database: {settings.get_database_url()}")
print(f"CORS Origins: {settings.CORS_ORIGINS}")
```

## Security Checklist

Before deploying to production:

- [ ] Change `SECRET_KEY` to unique value
- [ ] Set `DEBUG = False`
- [ ] Set `ENVIRONMENT = production`
- [ ] Use HTTPS URLs in `CORS_ORIGINS`
- [ ] Change database password
- [ ] Set strong password policy
- [ ] Enable `ENABLE_AUDIT_LOGGING`
- [ ] Configure proper `LOG_LEVEL` (WARNING or ERROR)
- [ ] Restrict `CORS_ORIGINS` to specific domains
- [ ] Test with production database
