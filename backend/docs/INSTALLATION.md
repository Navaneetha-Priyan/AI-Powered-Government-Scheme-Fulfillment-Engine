# Installation Guide

## Prerequisites

Before installing the Citizen Registration & Authentication API, ensure you have:

- Python 3.11 or higher
- MySQL 8.0 or higher
- pip (Python package manager)
- Git
- Optional: Docker and Docker Compose

## Step-by-Step Installation

### 1. Clone the Repository

```bash
cd "C:\Users\navan\Documents\Final Year Project\AI-Powered Government Scheme Fulfillment Engine"
cd backend
```

### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Upgrade pip

```bash
pip install --upgrade pip
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- fastapi (web framework)
- uvicorn (ASGI server)
- sqlalchemy (ORM)
- pydantic (validation)
- python-jose (JWT)
- passlib (password hashing)
- And other dependencies

### 5. Configure Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit .env with your settings
# Edit database URL, secret key, etc.
```

**Important variables to set:**
- `DATABASE_URL`: Your MySQL connection string
- `SECRET_KEY`: Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `CORS_ORIGINS`: Your frontend URLs

### 6. Create MySQL Database

**Option A: Using MySQL Client**

```bash
mysql -u root -p
CREATE DATABASE citizen_auth_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'citizen_user'@'localhost' IDENTIFIED BY 'citizen_password';
GRANT ALL PRIVILEGES ON citizen_auth_db.* TO 'citizen_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**Option B: Using Docker**

Skip this if you'll use Docker Compose for everything.

### 7. Run Database Migrations

```bash
# Using Alembic
alembic upgrade head
```

This creates all required tables:
- `citizens` - User authentication and profile
- `login_audits` - Login attempt tracking

### 8. Verify Installation

```bash
# Test imports
python -c "from app.core.config import settings; print('Settings OK')"
python -c "from app.database.connection import test_db_connection; print(test_db_connection())"
```

### 9. Start the Application

**Development with auto-reload:**
```bash
uvicorn app.main:app --reload
```

**Production:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Server will start at: `http://localhost:8000`

### 10. Access the API

- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Installation with Docker

### Quick Start

```bash
# Start services
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Check status
docker-compose ps
```

Services:
- API: http://localhost:8000
- MySQL: localhost:3306

### Docker Commands

```bash
# View logs
docker-compose logs backend
docker-compose logs mysql

# Stop services
docker-compose down

# Rebuild images
docker-compose build --no-cache

# Open bash in container
docker-compose exec backend bash
```

## Verification

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Get version
curl http://localhost:8000/version

# Register user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "phone": "9876543210",
    "full_name": "Test User",
    "password": "TestPass123!",
    "confirm_password": "TestPass123!",
    "district": "Chennai",
    "state": "Tamil Nadu"
  }'
```

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

## Troubleshooting

### MySQL Connection Error

**Error**: `connect() got an unexpected keyword argument 'charset'`

**Solution**: Update connection string to use charset properly:
```env
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/db?charset=utf8mb4
```

### Port Already in Use

**Error**: `Address already in use`

**Solution**:
```bash
# Change port
uvicorn app.main:app --port 8001

# Or kill existing process
# Windows: taskkill /PID <pid> /F
# Linux/Mac: kill -9 <pid>
```

### JWT Secret Key Error

**Error**: `jwt.JWTError`

**Solution**: Make sure `SECRET_KEY` in `.env` is set:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))" > secret.txt
# Copy the output to SECRET_KEY in .env
```

### Module Not Found

**Error**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# Make sure you're in the backend directory
cd backend

# Reinstall packages
pip install -r requirements.txt

# Or run with python module syntax
python -m uvicorn app.main:app --reload
```

### Database Not Found

**Error**: `(pymysql.err.OperationalError) (1044, "Access denied for user..."`

**Solution**: Create database and grant permissions:
```bash
mysql -u root -p < docs/database/init.sql
```

## Database Initialization Script

Create `docs/database/init.sql` for automated setup:

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS citizen_auth_db 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER IF NOT EXISTS 'citizen_user'@'localhost' 
  IDENTIFIED BY 'citizen_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON citizen_auth_db.* 
  TO 'citizen_user'@'localhost';

FLUSH PRIVILEGES;
```

## Development Setup

### Install Development Tools

```bash
# Code formatting
pip install black flake8 pylint

# Type checking
pip install mypy

# Pre-commit hooks
pip install pre-commit
pre-commit install
```

### Pre-commit Configuration

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black

  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

## Next Steps

1. ✅ Application is installed and running
2. 📚 Read the [README.md](README.md) for overview
3. 📖 Check [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) for endpoints
4. 🔐 Review security in [AUTHENTICATION_FLOW.md](docs/AUTHENTICATION_FLOW.md)
5. 💾 Understand schema in [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)
6. 🧪 Run tests: `pytest`
7. 🚀 Deploy to production

## Support

For issues:
1. Check `.env` configuration
2. Verify MySQL is running
3. Check logs: `tail -f logs/app.log`
4. Run tests: `pytest -v`
5. Check API docs: http://localhost:8000/docs

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.11 | 3.11+ |
| MySQL | 8.0 | 8.0+ |
| RAM | 2GB | 4GB+ |
| Disk | 5GB | 10GB+ |
| CPU | 2 cores | 4+ cores |

## Performance Tuning

### Database Connection Pool

Edit `.env`:
```env
SQLALCHEMY_POOL_SIZE=20      # Increase for high traffic
SQLALCHEMY_POOL_RECYCLE=3600 # Recycle connections
```

### Logging

```env
LOG_LEVEL=INFO    # Development: DEBUG, Production: INFO or WARNING
```

### CORS

```env
CORS_ORIGINS=["https://yourdomain.com"]  # Restrict origins
```

## Security Checklist

Before production deployment:

- [ ] Change `SECRET_KEY` in `.env`
- [ ] Change database password
- [ ] Set `DEBUG=False`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure CORS origins
- [ ] Enable HTTPS
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Review security settings
- [ ] Test all endpoints

Congratulations! Your Citizen Registration & Authentication API is ready to use! 🎉
