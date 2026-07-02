# Architecture Documentation

## Overview

The Citizen Registration & Authentication API (Module 1) is built using a Clean Architecture pattern with well-defined layers for separation of concerns and maintainability.

## Architecture Layers

```
┌────────────────────────────────────────┐
│   API / HTTP Layer                     │
│   (FastAPI Routes, Request Handlers)   │
└────────────────────┬───────────────────┘
                     │
┌────────────────────▼───────────────────┐
│   Service / Business Logic Layer       │
│   (AuthenticationService)              │
└────────────────────┬───────────────────┘
                     │
┌────────────────────▼───────────────────┐
│   Repository / Data Access Layer       │
│   (CitizenRepository)                  │
└────────────────────┬───────────────────┘
                     │
┌────────────────────▼───────────────────┐
│   Database Layer                       │
│   (SQLAlchemy ORM, MySQL)              │
└────────────────────────────────────────┘
```

## Detailed Architecture

### 1. API Layer (`app/api/`)

Handles HTTP requests and responses.

**Responsibilities:**
- Route definition (`auth_routes.py`, `health_routes.py`)
- HTTP request parsing and validation
- HTTP response formatting
- Request authentication (`dependencies.py`)

**Key Files:**
- `auth_routes.py` - Authentication endpoints
- `health_routes.py` - Health check endpoints
- `dependencies.py` - JWT authentication dependency

**Flow:**
```
HTTP Request → Route Handler → Service Call → Response
```

**Example:**
```python
@app.post("/auth/login")
async def login(login_data: CitizenLoginRequest, db: Session = Depends(get_db)):
    auth_service = AuthenticationService(db)
    token_response = auth_service.login(login_data)
    return SuccessResponse(data=token_response.model_dump())
```

### 2. Service Layer (`app/services/`)

Contains business logic and orchestration.

**Responsibilities:**
- Business logic implementation
- Validation orchestration
- Repository coordination
- Authentication flow management

**Key Classes:**
- `AuthenticationService` - Auth business logic

**Key Methods:**
- `register()` - Register new citizen
- `login()` - Login with credentials
- `refresh_token()` - Refresh access token
- `update_profile()` - Update user profile
- `change_password()` - Change password

**Benefits:**
- Testable business logic
- Reusable across multiple endpoints
- Clear separation from HTTP layer

**Example:**
```python
class AuthenticationService:
    def __init__(self, db: Session):
        self.db = db
        self.citizen_repo = CitizenRepository(db)
    
    def register(self, register_data):
        # Validate inputs
        # Check uniqueness
        # Hash password
        # Create citizen
        # Generate tokens
        return citizen, token_response
```

### 3. Repository Layer (`app/repositories/`)

Data access abstraction.

**Responsibilities:**
- Database queries
- CRUD operations
- Query optimization

**Key Classes:**
- `CitizenRepository` - Citizen operations
- `LoginAuditRepository` - Audit operations

**Key Methods:**
- `create()` - Insert new record
- `get_by_id()` - Fetch by ID
- `get_by_email()` - Fetch by email
- `email_exists()` - Check existence
- `update()` - Update record
- `delete()` - Soft delete

**Benefits:**
- Abstraction over database
- Easy to test with mocks
- Query optimization in one place

**Example:**
```python
class CitizenRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_email(self, email: str):
        return self.db.query(Citizen).filter(
            Citizen.email == email
        ).first()
```

### 4. Database Layer (`app/database/`)

ORM and database connection management.

**Responsibilities:**
- SQLAlchemy session management
- Connection pooling
- Transaction handling

**Key Components:**
- `connection.py` - Session factory, engine setup

**Features:**
- Connection pooling (20 connections)
- Auto-recycling (3600 seconds)
- Health check functionality

**Example:**
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    pool_recycle=3600,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine)
```

## Core Components

### Models (`app/models/`)

SQLAlchemy ORM models representing database tables.

**Files:**
- `citizen.py` - Citizen model with relationships

**Features:**
- UUID primary keys
- Indexes for performance
- Soft delete support
- Audit trail columns
- Enum for status values

```python
class Citizen(Base):
    __tablename__ = "citizens"
    
    id = Column(CHAR(36), primary_key=True)
    email = Column(String(254), unique=True)
    # ... other fields
```

### Schemas (`app/schemas/`)

Pydantic V2 models for request/response validation.

**Files:**
- `citizen.py` - All schemas

**Key Classes:**
- `CitizenRegisterRequest` - Registration input
- `CitizenLoginRequest` - Login input
- `CitizenProfileResponse` - Profile output
- `TokenResponse` - Token output
- `SuccessResponse` - Generic success
- `ErrorResponse` - Generic error

**Benefits:**
- Automatic validation
- Type safety
- API documentation

### Exceptions (`app/exceptions/`)

Custom exception classes for error handling.

**Files:**
- `exceptions.py` - All exception classes

**Hierarchy:**
```
AppException (base)
├── ValidationError (422)
├── AuthenticationError (401)
├── AuthorizationError (403)
├── NotFoundError (404)
├── ConflictError (409)
├── DatabaseError (500)
└── InternalServerError (500)
```

### Validators (`app/validators/`)

Custom validation functions for business rules.

**Files:**
- `validators.py` - All validators

**Classes:**
- `AadhaarValidator` - Aadhaar validation with checksum
- `RationCardValidator` - Ration card validation
- `EmailValidator` - Email format validation
- `PhoneValidator` - Phone format validation
- `NameValidator` - Name format validation
- `PincodeValidator` - Pincode format validation

### Core Configuration (`app/core/`)

Configuration and cross-cutting concerns.

**Files:**
- `config.py` - Settings management
- `security.py` - Password hashing functions
- `jwt.py` - JWT token operations
- `logging.py` - Logging configuration

**Key Functions:**
- `hash_password()` - Bcrypt hashing
- `verify_password()` - Bcrypt verification
- `create_access_token()` - JWT access token
- `create_refresh_token()` - JWT refresh token
- `verify_token()` - JWT verification

### Middleware (`app/middleware/`)

Cross-cutting concerns (CORS, exception handling, logging).

**Files:**
- `handlers.py` - Exception handlers and middleware

**Handlers:**
- Exception handling for AppException
- Exception handling for generic exceptions
- CORS middleware
- Request logging middleware

## Design Patterns

### 1. Dependency Injection

FastAPI dependency system for injecting database sessions:

```python
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/endpoint")
async def handler(db: Session = Depends(get_db)):
    # db is injected automatically
```

### 2. Repository Pattern

Abstract database operations:

```python
class CitizenRepository:
    def get_by_email(self, email):
        return self.db.query(Citizen).filter(Citizen.email == email).first()

# Usage
repo = CitizenRepository(db)
citizen = repo.get_by_email("test@example.com")
```

### 3. Service Layer Pattern

Encapsulate business logic:

```python
class AuthenticationService:
    def __init__(self, db: Session):
        self.citizen_repo = CitizenRepository(db)
    
    def register(self, data):
        # Business logic here
        return citizen
```

### 4. Exception Hierarchy

Custom exceptions for error handling:

```python
try:
    citizen = authentication_service.register(data)
except DuplicateEmailError as e:
    return error_response(409, e)
except ValidationError as e:
    return error_response(422, e)
except Exception as e:
    return error_response(500, e)
```

## Data Flow

### Registration Flow

```
1. POST /auth/register
   ↓
2. FastAPI validates with CitizenRegisterRequest schema
   ↓
3. Route handler calls AuthenticationService.register()
   ↓
4. Service validates email, phone, Aadhaar, etc.
   ↓
5. Service calls CitizenRepository.create()
   ↓
6. Repository executes SQL INSERT via SQLAlchemy
   ↓
7. MySQL inserts record and returns ID
   ↓
8. Service generates JWT tokens
   ↓
9. Route handler returns SuccessResponse with tokens
   ↓
10. FastAPI serializes response and sends HTTP 201
```

### Login Flow

```
1. POST /auth/login
   ↓
2. FastAPI validates with CitizenLoginRequest schema
   ↓
3. Route handler calls AuthenticationService.login()
   ↓
4. Service fetches citizen via CitizenRepository.get_by_email()
   ↓
5. Repository executes SQL SELECT
   ↓
6. MySQL returns citizen record
   ↓
7. Service verifies password with bcrypt
   ↓
8. Service generates JWT tokens
   ↓
9. Service logs login attempt via LoginAuditRepository
   ↓
10. Route handler returns SuccessResponse with tokens
    ↓
11. FastAPI serializes response and sends HTTP 200
```

### Protected Endpoint Flow

```
1. GET /auth/me with Authorization header
   ↓
2. FastAPI extracts token from header
   ↓
3. Dependency (get_current_user) verifies JWT signature
   ↓
4. Dependency extracts citizen_id from token
   ↓
5. Route handler calls AuthenticationService.get_profile()
   ↓
6. Service fetches citizen via CitizenRepository.get_by_id()
   ↓
7. Repository executes SQL SELECT with ID
   ↓
8. MySQL returns citizen record
   ↓
9. Route handler serializes to CitizenProfileResponse
   ↓
10. FastAPI sends HTTP 200 with profile data
```

## Error Handling

### Exception Handling Flow

```
Request → Route Handler
    ↓
    ├─ Validation Error
    │  ├─ Caught by Pydantic
    │  └─ Returns 422 VALIDATION_ERROR
    │
    ├─ AppException (Custom)
    │  ├─ Caught by exception handler
    │  └─ Returns appropriate status code
    │
    └─ Generic Exception
       ├─ Logged
       └─ Returns 500 INTERNAL_SERVER_ERROR
```

## Database Design

### Key Features

1. **UUID Primary Keys** - Distributed system compatible
2. **Soft Delete** - Data retention, reversible deletion
3. **Audit Trail** - Track changes (created_at, updated_at, created_by)
4. **Indexing** - Performance optimization for common queries
5. **Enum Types** - Type safety for fixed values (status, gender)
6. **Unique Constraints** - Data integrity (email, phone, Aadhaar)

### Performance Considerations

1. **Connection Pooling** - 20 connections by default
2. **Query Optimization** - Indexes on frequently searched fields
3. **Lazy Loading** - SQLAlchemy loads relationships on demand
4. **Batch Operations** - Use bulk operations for multiple inserts

## Security Architecture

### Password Security
```
Plain Password → bcrypt (12 rounds) → Hash (stored in DB)
Login Password → bcrypt compare → Matches hash?
```

### JWT Security
```
Payload → JWT Encode with SECRET_KEY → Token
Token → JWT Decode with SECRET_KEY → Payload (if valid)
```

### Account Security
```
Failed Login → Increment counter → Threshold (5) → Lock account
Successful Login → Reset counter → Unlock account
```

## Testing Architecture

### Unit Tests

Test individual components in isolation with mocks:

- `tests/unit/test_validators.py` - Validator functions
- `tests/unit/test_security.py` - Password hashing

### Integration Tests

Test API endpoints with real database:

- `tests/integration/test_auth_api.py` - All endpoints

### Test Database

- SQLite in-memory database for fast tests
- Automatic cleanup after each test

## Scalability Considerations

### Horizontal Scaling

1. **Stateless API** - No session state in API
2. **JWT Tokens** - Can validate on any server
3. **Database Externalization** - Shared MySQL database
4. **Load Balancing** - Multiple API instances

### Database Scaling

1. **Connection Pooling** - Efficient resource use
2. **Read Replicas** - For read-heavy operations
3. **Partitioning** - By district, state for large datasets
4. **Archival** - Move old audit logs to archive

### Performance Optimization

1. **Caching** - Add Redis for tokens/sessions
2. **Async Operations** - Use asyncio for I/O operations
3. **Query Optimization** - Use EXPLAIN to analyze queries
4. **Compression** - Gzip HTTP responses

## Deployment Architecture

### Docker Deployment

```
┌────────────────┐
│ Docker Compose │
└────────┬───────┘
         │
    ┌────┴─────┐
    │           │
┌───▼──┐   ┌───▼───┐
│ API  │   │ MySQL │
│ 8000 │   │ 3306  │
└──────┘   └───────┘
```

### Cloud Deployment

```
┌─────────────────┐
│  Load Balancer  │
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┐
    │          │        │        │
┌───▼──┐  ┌───▼──┐ ┌───▼──┐ ┌───▼──┐
│ API1 │  │ API2 │ │ API3 │ │ API4 │
└──────┘  └──────┘ └──────┘ └──────┘
    │
┌───▼─────────────┐
│  Managed MySQL  │
└─────────────────┘
```

## Future Extensibility

The architecture supports easy addition of new modules:

### Module 2: DigiLocker
- Add fields to Citizen model
- Add DigiLockerRepository
- Add DigiLockerService
- Add new routes in api/

### Module 4: Eligibility
- Add EligibilityRepository
- Add EligibilityService
- Add eligibility rules engine
- Use existing citizen data

### Module 6: Voice Processing
- Add VoiceRepository
- Add VoiceService
- Use existing authentication

All modules follow the same layered architecture.

## Code Organization Best Practices

1. **Separation of Concerns** - Each layer has clear responsibility
2. **DRY Principle** - No code duplication
3. **Type Hints** - All functions have type hints
4. **Docstrings** - All classes and functions documented
5. **Error Handling** - Graceful error handling with proper status codes
6. **Logging** - Detailed logging for debugging
7. **Testing** - Comprehensive test coverage
8. **Security** - Security best practices throughout
