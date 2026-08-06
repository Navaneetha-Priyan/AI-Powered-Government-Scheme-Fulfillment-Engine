# Citizen Registration & Authentication API (Module 1)

Secure registration and login system for citizens in the AI-Powered Government Scheme Fulfillment Engine.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Database Schema](#database-schema)
- [Security](#security)
- [Future Modules](#future-modules)

## Overview

Module 1 provides a production-ready authentication system with:
- Secure citizen registration
- JWT-based login with access and refresh tokens
- User profile management
- Password change functionality
- Aadhaar and Ration Card validation
- Comprehensive audit logging
- Enterprise-grade security

## Features

### Authentication
- **Citizen Registration** - Register with email, phone, and government ID
- **Citizen Login** - Secure login with email and password
- **JWT Tokens** - Access tokens (30 minutes) and refresh tokens (7 days)
- **Token Refresh** - Get new access token without re-entering password
- **Secure Logout** - Graceful logout with audit logging

### Profile Management
- **View Profile** - Get authenticated user's profile information
- **Update Profile** - Update personal and address information
- **Change Password** - Secure password change with validation
- **Profile Verification** - Email and phone verification flags

### Validation
- **Aadhaar Validation** - 12-digit validation with Verhoeff checksum
- **Ration Card Validation** - Format and uniqueness validation
- **Email Validation** - RFC-compliant email validation
- **Phone Validation** - Indian phone number validation
- **Password Strength** - Enforce strong password policy

### Security
- **Password Hashing** - bcrypt with 12 rounds
- **JWT Authentication** - HS256 algorithm
- **CORS Protection** - Configurable CORS origins
- **SQL Injection Protection** - SQLAlchemy ORM
- **XSS Protection** - JSON response validation
- **Account Locking** - Lock after 5 failed login attempts
- **Audit Logging** - Track all authentication events

## Technology Stack

- **Framework**: FastAPI 0.104.1
- **Web Server**: Uvicorn 0.24.0
- **Database**: MySQL 8.0
- **ORM**: SQLAlchemy 2.0.23
- **Validation**: Pydantic V2 2.5.0
- **Password Hashing**: bcrypt 4.1.1 + passlib 1.7.4
- **JWT**: python-jose 3.3.0
- **Migrations**: Alembic 1.13.1
- **Testing**: Pytest 7.4.3
- **Containerization**: Docker + Docker Compose

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── core/                   # Core configuration and utilities
│   │   ├── __init__.py
│   │   ├── config.py          # Settings management
│   │   ├── logging.py         # Logging configuration
│   │   ├── security.py        # Password hashing functions
│   │   └── jwt.py             # JWT token management
│   ├── database/              # Database configuration
│   │   ├── __init__.py
│   │   └── connection.py      # Database connection and session
│   ├── models/                # SQLAlchemy models
│   │   ├── __init__.py
│   │   └── citizen.py         # Citizen model
│   ├── schemas/               # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   └── citizen.py         # Citizen schemas
│   ├── repositories/          # Data access layer
│   │   ├── __init__.py
│   │   └── citizen_repository.py
│   ├── services/              # Business logic layer
│   │   ├── __init__.py
│   │   └── auth_service.py    # Authentication logic
│   ├── api/                   # API routes
│   │   ├── __init__.py
│   │   ├── dependencies.py    # Dependency injection
│   │   ├── auth_routes.py     # Authentication endpoints
│   │   └── health_routes.py   # Health check endpoints
│   ├── exceptions/            # Custom exceptions
│   │   ├── __init__.py
│   │   └── exceptions.py      # Exception classes
│   ├── validators/            # Validation functions
│   │   ├── __init__.py
│   │   └── validators.py      # Custom validators
│   ├── utils/                 # Utility functions
│   │   └── __init__.py
│   └── middleware/            # Custom middleware
│       ├── __init__.py
│       └── handlers.py        # Exception handlers
├── tests/                     # Test suite
│   ├── conftest.py           # Test configuration
│   ├── unit/                 # Unit tests
│   │   ├── test_validators.py
│   │   └── test_security.py
│   └── integration/          # Integration tests
│       └── test_auth_api.py
├── alembic/                  # Database migrations
│   ├── env.py               # Migration configuration
│   ├── alembic.ini          # Migration settings
│   └── versions/            # Migration files
├── docs/                    # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── DATABASE_SCHEMA.md
│   ├── ARCHITECTURE.md
│   ├── AUTHENTICATION_FLOW.md
│   └── ENVIRONMENT_VARIABLES.md
├── .env.example            # Environment variables template
├── .env                    # Environment variables (development)
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker image specification
├── docker-compose.yml     # Docker Compose configuration
├── pytest.ini            # Pytest configuration
└── README.md             # This file
```

## Installation

### Prerequisites
- Python 3.11+
- MySQL 8.0+
- Docker & Docker Compose (optional)

### Setup (Local Development)

1. **Clone the repository**
```bash
cd backend
```

2. **Create virtual environment**
```bash
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Initialize database**
```bash
# Using Alembic
alembic upgrade head
```

6. **Run the application**
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Setup (Docker)

1. **Build and run with Docker Compose**
```bash
docker-compose up -d
```

2. **Initialize database**
```bash
docker-compose exec backend alembic upgrade head
```

3. **Access the API**
```
http://localhost:8000
```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options.

Key variables:
```env
# Database
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/citizen_auth_db

# JWT
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Security
REQUIRE_UPPERCASE=True
REQUIRE_LOWERCASE=True
REQUIRE_DIGITS=True
REQUIRE_SPECIAL_CHARS=True
MIN_PASSWORD_LENGTH=8

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
```

## Running the Application

### Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

### Docker
```bash
docker-compose up
```

## API Documentation

### Base URL
- Development: `http://localhost:8000`
- Production: `https://api.example.com`

### Authentication Endpoints

#### 1. Register
- **POST** `/auth/register`
- Register a new citizen account
- Request body:
```json
{
  "email": "citizen@example.com",
  "phone": "9876543210",
  "full_name": "John Doe",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!",
  "aadhaar_number": "123456789012",
  "smart_ration_card": "TN1234567890",
  "district": "Chennai",
  "state": "Tamil Nadu"
}
```
- Response: Access token, Refresh token, Citizen ID

#### 2. Login
- **POST** `/auth/login`
- Login with email and password
- Request body:
```json
{
  "email": "citizen@example.com",
  "password": "SecurePass123!"
}
```
- Response: Access token, Refresh token

#### 3. Refresh Token
- **POST** `/auth/refresh`
- Get new access token using refresh token
- Request body:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```
- Response: New access token, Refresh token

#### 4. Get Profile
- **GET** `/auth/me`
- Get authenticated user's profile
- Headers: `Authorization: Bearer <access_token>`
- Response: Citizen profile with all details

#### 5. Update Profile
- **PUT** `/auth/profile`
- Update authenticated user's profile
- Headers: `Authorization: Bearer <access_token>`
- Request body: (all fields optional)
```json
{
  "full_name": "Updated Name",
  "gender": "male",
  "village": "Sample Village",
  "district": "New District",
  "state": "New State"
}
```

#### 6. Change Password
- **PUT** `/auth/change-password`
- Change password for authenticated user
- Headers: `Authorization: Bearer <access_token>`
- Request body:
```json
{
  "old_password": "CurrentPass123!",
  "new_password": "NewPass123!",
  "confirm_password": "NewPass123!"
}
```

#### 7. Logout
- **POST** `/auth/logout`
- Logout authenticated user (audit logging)
- Headers: `Authorization: Bearer <access_token>`

#### 8. Verify Token
- **POST** `/auth/verify-token`
- Verify token validity
- Request body:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Health & Info Endpoints

#### 1. Health Check
- **GET** `/health`
- Check API and database health
- Response: Status, version, database connection status

#### 2. API Version
- **GET** `/version`
- Get API version
- Response: Version information

#### 3. API Info
- **GET** `/info`
- Get API information
- Response: App name, version, description, etc.

### Response Format

All responses follow a consistent format:

**Success Response:**
```json
{
  "success": true,
  "message": "Operation successful",
  "data": { }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Error description",
  "details": { }
}
```

### Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| VALIDATION_ERROR | 422 | Invalid input data |
| AUTHENTICATION_ERROR | 401 | Invalid credentials |
| AUTHORIZATION_ERROR | 403 | Access denied |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Resource already exists |
| INTERNAL_SERVER_ERROR | 500 | Server error |

### Interactive API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## Testing

### Run All Tests
```bash
pytest
```

### Run Unit Tests Only
```bash
pytest tests/unit -v
```

### Run Integration Tests Only
```bash
pytest tests/integration -v
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Test Coverage Report
```bash
# Open htmlcov/index.html in browser
```

## Database Schema

### Citizens Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | CHAR(36) | PK | UUID primary key |
| email | VARCHAR(254) | UNIQUE, NOT NULL | Email address |
| phone | VARCHAR(20) | UNIQUE, NOT NULL | Phone number |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt hash |
| full_name | VARCHAR(100) | NOT NULL | Full name |
| aadhaar_number | VARCHAR(12) | UNIQUE | Aadhaar ID |
| smart_ration_card | VARCHAR(20) | UNIQUE | Ration card ID |
| email_verified | BOOLEAN | DEFAULT FALSE | Email verification flag |
| phone_verified | BOOLEAN | DEFAULT FALSE | Phone verification flag |
| account_active | BOOLEAN | DEFAULT TRUE | Account status |
| account_locked | BOOLEAN | DEFAULT FALSE | Locked due to failed attempts |
| status | ENUM | DEFAULT 'active' | Account status (active, inactive, suspended, pending) |
| created_at | DATETIME | NOT NULL | Creation timestamp |
| updated_at | DATETIME | NOT NULL | Update timestamp |
| is_deleted | BOOLEAN | DEFAULT FALSE | Soft delete flag |

### LoginAudits Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | CHAR(36) | PK | UUID primary key |
| citizen_id | CHAR(36) | NOT NULL | Foreign key to citizens |
| login_type | VARCHAR(20) | NOT NULL | Type of login attempt |
| success | BOOLEAN | NOT NULL | Success/failure flag |
| failure_reason | VARCHAR(255) | | Reason for failure if applicable |
| ip_address | VARCHAR(45) | | IP address of login |
| user_agent | VARCHAR(500) | | User agent string |
| created_at | DATETIME | NOT NULL | Timestamp |

## Security

### Password Policy

Requirements:
- Minimum 8 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one digit (0-9)
- At least one special character (!@#$%^&*)

### Password Hashing

- Algorithm: bcrypt
- Rounds: 12
- No plaintext passwords stored

### JWT Tokens

- **Access Token**: 30 minutes (configurable)
- **Refresh Token**: 7 days (configurable)
- **Algorithm**: HS256
- **Signature**: SECRET_KEY

### Authentication Flow

1. User provides email and password
2. Password verified against bcrypt hash
3. JWT tokens generated (access + refresh)
4. Tokens returned to client
5. Client includes access token in Authorization header
6. Server verifies token signature and expiry
7. Request processed if valid

### Account Locking

- Account locked after 5 failed login attempts
- Tracks failed attempts per user
- Resets on successful login
- Prevents brute force attacks

### Audit Logging

All authentication events logged:
- Successful logins (IP, timestamp)
- Failed login attempts (reason)
- Password changes
- Profile updates
- Registration events

## Completed Modules

### Module 2: Mock DigiLocker Integration
- Automatic profile retrieval using Aadhaar/Ration Card
- Mock document scanning
- Pre-population of citizen data

### Module 3: Government Scheme Database
- Searchable scheme repository
- PDF document parsing
- Vector embedding storage

### Module 4: Eligibility Engine
- Rule-based eligibility checking
- Personalized scheme recommendations
- Benefit calculation

### Module 4 Docs
- API endpoints: `docs/MODULE_4_ARCHITECTURE.md`
- Database tables: `docs/MODULE_4_DATABASE_SCHEMA.md`
- Installation and tests: `docs/MODULE_4_INSTALLATION_AND_TESTING.md`

### Module 5: Flutter Mobile App
- Mobile app integration
- Voice authentication support
- Offline capabilities

### Module 6: Voice Processing
- Speech-to-text transcription
- Regional dialect support
- Audio denoising

### Module 7: PDF Generation
- Auto-filled application forms
- Document signature support
- Multi-language support

### Module 8: Notifications
- WhatsApp integration
- Email notifications
- SMS alerts

### Module 9: Officer Dashboard
- Administrative portal
- Application review workflow
- Analytics and reporting

### Module 10: Deployment
- Cloud infrastructure setup
- CI/CD pipeline
- Monitoring and logging

## Development Guidelines

### Code Style
- Follow PEP 8
- Use type hints
- Document with docstrings
- Maximum line length: 88 characters

### Adding New Features
1. Create feature branch
2. Write tests first (TDD)
3. Implement feature
4. Ensure all tests pass
5. Update documentation
6. Submit pull request

### Database Migrations
1. Modify models in `app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review migration file
4. Run migration: `alembic upgrade head`

## Troubleshooting

### Database Connection Issues
- Verify DATABASE_URL in .env
- Check MySQL is running
- Verify credentials and permissions
- Check firewall rules

### JWT Token Issues
- Verify SECRET_KEY is set
- Check token expiry
- Verify ALGORITHM matches

### CORS Issues
- Check CORS_ORIGINS in .env
- Verify request origin is whitelisted
- Check request headers

## Support & Contact

For issues and questions:
- Create an issue in the repository
- Contact the development team
- Check documentation at `/docs`

## License

This project is part of the AI-Powered Government Scheme Fulfillment Engine.

## Authors

Backend Team - Citizen Registration & Authentication Module
