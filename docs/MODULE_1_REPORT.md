# AI-Powered Government Scheme Fulfillment Engine
## Module 1 Completion Report — Citizen Registration & Authentication

**Date**: July 2026
**Status**: ✅ Complete
**Prepared by**: Backend Team

---

## 1. Project Overview

The AI-Powered Government Scheme Fulfillment Engine is a Final Year Engineering Project that helps citizens discover and apply for government schemes they are eligible for. The system uses AI/NLP to match citizen profiles with relevant schemes and supports multilingual voice input.

The project is divided into 10 modules across 7th and 8th semester. This report covers the completion of **Module 1: Citizen Registration & Authentication**, which forms the foundation for all future modules.

### Team

| Role | Responsibility |
|------|---------------|
| Backend | FastAPI, MySQL, REST APIs, Authentication |
| Frontend | Flutter mobile application |
| AI/NLP | Scheme matching, Bhashini/Whisper integration |

---

## 2. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend Framework | FastAPI | 0.115.4 |
| Server | Uvicorn | 0.31.0 |
| Database | MySQL | 8.0 |
| ORM | SQLAlchemy | 2.0.36 |
| Migrations | Alembic | 1.13.1 |
| Data Validation | Pydantic V2 | 2.10.3 |
| Authentication | JWT (python-jose) | 3.3.0 |
| Password Hashing | bcrypt (passlib) | 4.2.0 |
| Testing | pytest | 8.3.4 |
| Frontend | Flutter | Latest |
| Language | Python | 3.13.1 |

---

## 3. Module 1 Scope

Module 1 covers the complete citizen identity and authentication system:

- Citizen registration with government ID validation
- Secure login with JWT tokens
- Token refresh mechanism
- Profile management (view & update)
- Password change
- Logout with audit logging
- Token verification

---

## 4. Architecture

The backend follows a clean layered architecture:

```
Request
   │
   ▼
┌─────────────────┐
│   API Routes    │  ← auth_routes.py, health_routes.py
│  (FastAPI)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Service Layer  │  ← auth_service.py
│ (Business Logic)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Repository     │  ← citizen_repository.py
│  (Data Access)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MySQL Database │  ← govt_scheme_db
│  (SQLAlchemy)   │
└─────────────────┘
```

### Design Patterns Used
- **Repository Pattern** — Separates data access from business logic
- **Service Layer Pattern** — Centralizes business rules
- **Dependency Injection** — FastAPI `Depends()` for DB sessions and auth
- **DTO Pattern** — Pydantic schemas for request/response separation

---

## 5. Database Design

### Database: `govt_scheme_db`

#### Table: `citizens`
| Column | Type | Description |
|--------|------|-------------|
| id | CHAR(36) | UUID primary key |
| email | VARCHAR(254) | Unique, indexed |
| phone | VARCHAR(20) | Unique, indexed |
| password_hash | VARCHAR(255) | bcrypt hashed |
| full_name | VARCHAR(100) | Citizen name |
| gender | ENUM | male/female/other/prefer_not_to_say |
| date_of_birth | DATETIME | Optional |
| aadhaar_number | VARCHAR(12) | Unique, optional |
| smart_ration_card | VARCHAR(20) | Unique, optional |
| address_line1/2 | VARCHAR(255) | Address fields |
| village, taluk | VARCHAR(100) | Location fields |
| district | VARCHAR(100) | Required |
| state | VARCHAR(50) | Required |
| pincode | VARCHAR(6) | Optional |
| status | ENUM | active/inactive/suspended/pending_verification |
| account_active | BOOLEAN | Account enabled flag |
| account_locked | BOOLEAN | Locked after 5 failed logins |
| failed_login_attempts | INTEGER | Counter |
| last_login | DATETIME | Last login timestamp |
| email_verified | BOOLEAN | Verification flag |
| phone_verified | BOOLEAN | Verification flag |
| is_deleted | BOOLEAN | Soft delete flag |
| created_at / updated_at | DATETIME | Audit timestamps |

**Indexes**: 9 composite and single-column indexes for query optimization.
**Constraints**: Unique on email, phone, aadhaar_number, smart_ration_card.

#### Table: `login_audits`
Tracks every login attempt (success and failure) with IP address, timestamp, and failure reason.

---

## 6. API Endpoints

Base URL: `http://localhost:8000`
Interactive Docs: `http://localhost:8000/docs`

### Authentication Endpoints (`/auth`)

| Method | Endpoint | Auth Required | Description |
|--------|----------|--------------|-------------|
| POST | `/auth/register` | No | Register new citizen |
| POST | `/auth/login` | No | Login with email & password |
| POST | `/auth/refresh` | No | Refresh access token |
| GET | `/auth/me` | Yes | Get current user profile |
| PUT | `/auth/profile` | Yes | Update profile |
| PUT | `/auth/change-password` | Yes | Change password |
| POST | `/auth/logout` | Yes | Logout |
| POST | `/auth/verify-token` | No | Verify token validity |

### Health Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Server health status |
| GET | `/version` | API version |
| GET | `/info` | App info |

### Authentication Flow

```
1. POST /auth/register  →  Returns access_token + refresh_token
2. POST /auth/login     →  Returns access_token + refresh_token
3. GET  /auth/me        →  Header: Authorization: Bearer <access_token>
4. POST /auth/refresh   →  Body: { "refresh_token": "..." }
```

### Token Details
- **Access Token**: Expires in 30 minutes (JWT)
- **Refresh Token**: Expires in 7 days (JWT)
- **Algorithm**: HS256

---

## 7. Validation & Security

### Input Validators
| Validator | Rules |
|-----------|-------|
| Aadhaar | 12 digits, Verhoeff checksum algorithm |
| Ration Card | Format: `<STATE_CODE><10 digits>`, 26 state codes supported |
| Email | RFC format, no consecutive dots |
| Phone | Indian format: starts with 6-9, 10 digits |
| Name | Letters only, no numbers, no excessive spaces |
| Pincode | Exactly 6 digits |
| Age | 18–120 range |

### Password Policy
- Minimum 8 characters
- Must contain uppercase letter
- Must contain lowercase letter
- Must contain digit
- Must contain special character

### Security Features
- bcrypt password hashing (12 rounds)
- Account locking after 5 failed login attempts
- JWT tokens with expiry
- HTTPBearer scheme (visible in Swagger UI)
- CORS middleware configured
- Soft delete (data never permanently removed)
- Full login audit trail

---

## 8. Project File Structure

```
backend/
├── app/
│   ├── main.py                        ← FastAPI entry point
│   ├── core/
│   │   ├── config.py                  ← Pydantic settings (30+ options)
│   │   ├── security.py                ← bcrypt hashing
│   │   ├── jwt.py                     ← Token creation & verification
│   │   └── logging.py                 ← Rotating file logger
│   ├── database/
│   │   └── connection.py              ← SQLAlchemy engine & session
│   ├── models/
│   │   └── citizen.py                 ← Citizen & LoginAudit ORM models
│   ├── schemas/
│   │   └── citizen.py                 ← Pydantic request/response schemas
│   ├── validators/
│   │   └── validators.py              ← Aadhaar, phone, email validators
│   ├── repositories/
│   │   └── citizen_repository.py      ← DB queries (CRUD)
│   ├── services/
│   │   └── auth_service.py            ← Business logic
│   ├── api/
│   │   ├── auth_routes.py             ← 8 auth endpoints
│   │   ├── health_routes.py           ← 3 health endpoints
│   │   └── dependencies.py            ← JWT auth dependency
│   ├── middleware/
│   │   └── handlers.py                ← CORS, exception handlers
│   └── exceptions/
│       └── exceptions.py              ← Custom exception hierarchy
├── tests/
│   ├── conftest.py                    ← Fixtures, SQLite test DB
│   ├── unit/
│   │   ├── test_validators.py         ← 30+ validator tests
│   │   └── test_security.py           ← 10+ security tests
│   └── integration/
│       └── test_auth_api.py           ← 20+ API endpoint tests
├── alembic/
│   └── versions/
│       └── 001_initial_schema.py      ← DB migration
├── .env                               ← Environment config
├── requirements.txt                   ← Python dependencies
├── docker-compose.yml                 ← MySQL + Backend containers
└── Dockerfile                         ← Container definition
```

---

## 9. Test Results

All 63 tests passing.

```
tests/integration/test_auth_api.py   ← 21 tests   ✅ PASSED
tests/unit/test_security.py          ← 12 tests   ✅ PASSED
tests/unit/test_validators.py        ← 30 tests   ✅ PASSED

Total: 63 passed, 0 failed
```

### Coverage Report
| Module | Coverage |
|--------|----------|
| security.py | 100% |
| schemas/citizen.py | 95% |
| validators/validators.py | 94% |
| core/config.py | 95% |
| middleware/handlers.py | 86% |
| models/citizen.py | 91% |
| **Overall** | **70%** |

---

## 10. Setup Instructions (For Teammates)

### Prerequisites
- Python 3.10+
- MySQL 8.0
- Git

### Steps

**1. Clone and navigate:**
```bash
cd backend
```

**2. Create virtual environment:**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Create MySQL database:**
```sql
CREATE DATABASE govt_scheme_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**5. Configure environment:**
```bash
copy .env.example .env
# Edit .env → update DATABASE_URL with your MySQL password
```

**6. Run migrations:**
```bash
alembic upgrade head
```

**7. Start server:**
```bash
python -m app.main
```

**8. Open Swagger UI:**
```
http://localhost:8000/docs
```

---

## 11. Known Issues & Bugs Fixed

During development, the following bugs were identified and resolved:

| # | Bug | Fix Applied |
|---|-----|-------------|
| 1 | Wrong 403 status in tests (should be 401) | Fixed status codes in test assertions |
| 2 | SQLAlchemy 2.x raw SQL deprecation | Wrapped in `text()` |
| 3 | Double `/auth` prefix in test conftest | Removed duplicate prefix |
| 4 | `PENDING_VERIFICATION` blocking login | Changed registration status to `ACTIVE` |
| 5 | SQLite StaticPool data leak between tests | Added `clean_tables` autouse fixture |
| 6 | `SERVER_RELOAD=True` uvicorn warning | Set to `False` in `.env` |
| 7 | `alembic.ini` in wrong directory | Moved to `backend/` root |
| 8 | Gender enum uppercase/lowercase mismatch | Added `values_callable` to SQLAlchemy Enum |
| 9 | Swagger UI missing Authorize button | Replaced `Header()` with `HTTPBearer` |
| 10 | Database named `citizen_auth_db` (too narrow) | Renamed to `govt_scheme_db` |

---

## 12. Module Completion Status

### Module 1 ✅ Complete

| Feature | Status |
|---------|--------|
| Citizen Registration | ✅ Done |
| Login / Logout | ✅ Done |
| JWT Access + Refresh Tokens | ✅ Done |
| Profile View & Update | ✅ Done |
| Password Change | ✅ Done |
| Token Verification | ✅ Done |
| Aadhaar Validation | ✅ Done |
| Ration Card Validation | ✅ Done |
| Account Locking | ✅ Done |
| Login Audit Logging | ✅ Done |
| Database Migrations | ✅ Done |
| Unit Tests (63 passing) | ✅ Done |
| Docker Support | ✅ Done |
| Swagger UI Docs | ✅ Done |

### Upcoming Modules

| Module | Semester | Description |
|--------|----------|-------------|
| Module 2 | 7th | DigiLocker Document Integration |
| Module 3 | 7th | Scheme Discovery & Eligibility Engine |
| Module 4 | 7th | Application Submission & Tracking |
| Module 5 | 7th | Multilingual Voice Input (Bhashini/Whisper) |
| Module 6 | 8th | AI Scheme Matching (ChromaDB / FAISS) |
| Module 7 | 8th | Document Upload & Verification |
| Module 8 | 8th | Notifications & Alerts |
| Module 9 | 8th | Admin Dashboard |
| Module 10 | 8th | Analytics & Reporting |

---

## 13. API for Frontend Team

The Flutter app needs to integrate with these endpoints for Module 1:

### Register
```
POST http://localhost:8000/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "phone": "9876543210",
  "full_name": "Ravi Kumar",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!",
  "district": "Chennai",
  "state": "Tamil Nadu"
}
```

### Login
```
POST http://localhost:8000/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

### Protected Request (use access_token from login/register)
```
GET http://localhost:8000/auth/me
Authorization: Bearer <access_token>
```

### Success Response Format
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": { ... }
}
```

### Error Response Format
```json
{
  "detail": {
    "error": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

---

*Report generated for internal team use — AI-Powered Government Scheme Fulfillment Engine, Final Year Project*
