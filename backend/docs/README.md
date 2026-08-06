# Documentation

Complete documentation for the Citizen Registration & Authentication API (Module 1).

## Quick Start

1. **New to this project?** → Start with [README.md](../README.md)
2. **Want to install?** → See [INSTALLATION.md](INSTALLATION.md)
3. **Need API details?** → Check [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

## Documentation Files

### [README.md](../README.md)
**Project Overview**
- What is this project?
- Key features
- Technology stack
- Quick start
- Testing instructions
- Deployment guide

### [INSTALLATION.md](INSTALLATION.md)
**Installation & Setup Guide**
- Step-by-step installation instructions
- Virtual environment setup
- Database configuration
- Running migrations
- Starting the server
- Verification steps
- Docker setup
- Troubleshooting

### [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
**API Endpoint Reference**
- Base URLs
- Authentication details
- Response format
- All 11 endpoints with:
  - Request/response examples
  - Field validation rules
  - Error cases
  - Status codes
- Data types reference
- Complete usage examples
- Interactive API docs locations

### [AUTHENTICATION_FLOW.md](AUTHENTICATION_FLOW.md)
**Authentication Flows & Diagrams**
- Registration flow (ASCII diagram)
- Login flow (ASCII diagram)
- Protected request flow
- Token refresh flow
- Account locking mechanism
- Password change flow
- Security considerations
- Best practices

### [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
**Database Schema Documentation**
- Complete schema definition
- Table descriptions
- Column details with types and constraints
- Indexes and their purposes
- Sample data
- Relationships
- Views and materialized views
- Performance optimization tips
- Backup and maintenance guidelines

### [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)
**Configuration Reference**
- Complete list of 50+ environment variables
- Database configuration
- Server settings
- JWT/Security settings
- Password policy
- CORS configuration
- Logging options
- Feature flags
- Examples for dev/staging/production
- Secure key generation
- Production checklist

### [ARCHITECTURE.md](ARCHITECTURE.md)
**System Architecture Documentation**
- Layered architecture overview
- Component descriptions
- Design patterns used
- Data flow diagrams
- Error handling approach
- Database design decisions
- Security architecture
- Testing strategy
- Scalability considerations
- Deployment options
- Future extensibility

### Module 3 and Module 4 Documentation
- [MODULE_3_ARCHITECTURE.md](MODULE_3_ARCHITECTURE.md) - scheme knowledge base and semantic retrieval
- [MODULE_3_DATABASE_SCHEMA.md](MODULE_3_DATABASE_SCHEMA.md) - Module 3 tables and indexing
- [MODULE_3_INSTALLATION_AND_TESTING.md](MODULE_3_INSTALLATION_AND_TESTING.md) - Module 3 setup and validation
- [MODULE_4_ARCHITECTURE.md](MODULE_4_ARCHITECTURE.md) - eligibility engine and recommendation APIs
- [MODULE_4_DATABASE_SCHEMA.md](MODULE_4_DATABASE_SCHEMA.md) - recommendation tables, rules, history, and feedback
- [MODULE_4_INSTALLATION_AND_TESTING.md](MODULE_4_INSTALLATION_AND_TESTING.md) - Module 4 setup and validation

## How to Use This Documentation

### For Developers

1. **Getting Started**
   - Read [README.md](../README.md) for overview
   - Follow [INSTALLATION.md](INSTALLATION.md) to set up locally
   - Explore [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for endpoints

2. **Understanding the Code**
   - Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
   - Check [AUTHENTICATION_FLOW.md](AUTHENTICATION_FLOW.md) for flows
   - Refer to [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for data model

3. **Implementing Features**
   - Check [ARCHITECTURE.md](ARCHITECTURE.md) for patterns
   - Reference [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for response formats
   - Use [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for data queries

### For DevOps/System Administrators

1. **Deployment Setup**
   - Read [INSTALLATION.md](INSTALLATION.md) Docker section
   - Check [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) for production config
   - Review [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for backup strategies

2. **Configuration Management**
   - Understand all variables in [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)
   - Check production checklist in [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)
   - Review security settings in [ARCHITECTURE.md](ARCHITECTURE.md)

### For Security Auditors

1. **Authentication & Authorization**
   - Check [AUTHENTICATION_FLOW.md](AUTHENTICATION_FLOW.md) for security flows
   - Review password policies in [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)
   - Check JWT configuration in [ARCHITECTURE.md](ARCHITECTURE.md)

2. **Data Protection**
   - Review [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for storage
   - Check [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) for configuration
   - Review security in [ARCHITECTURE.md](ARCHITECTURE.md)

### For API Consumers

1. **Integration**
   - Start with [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
   - Follow examples in [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
   - Check status codes and error handling
   - Review [AUTHENTICATION_FLOW.md](AUTHENTICATION_FLOW.md) for token management

2. **Troubleshooting**
   - Check error codes in [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
   - Review flows in [AUTHENTICATION_FLOW.md](AUTHENTICATION_FLOW.md)
   - Check common issues in [INSTALLATION.md](INSTALLATION.md)

## Document Map

```
Documentation/
├── README.md                          ← Start here
├── INSTALLATION.md                    ← Setup & troubleshooting
├── API_DOCUMENTATION.md               ← API endpoints & examples
├── AUTHENTICATION_FLOW.md             ← Flows & security
├── DATABASE_SCHEMA.md                 ← Data model
├── ENVIRONMENT_VARIABLES.md           ← Configuration
├── ARCHITECTURE.md                    ← System design
├── MODULE_3_*.md                      ← Scheme knowledge base docs
├── MODULE_4_*.md                      ← Eligibility and recommendations docs
└── README.md (this file)             ← Navigation guide
```

## Key Concepts

### Authentication Flow
- User registers with email/phone
- Password hashed with bcrypt (12 rounds)
- JWT tokens issued (access + refresh)
- Access token validates protected requests
- Refresh token gets new access token
- Failed logins tracked, account locks at 5 failures

### Database Design
- MySQL 8.0 with InnoDB
- 40+ columns in citizens table
- 9 indexes for performance
- Soft delete support
- Audit trail (created_at, updated_at)
- Unique constraints on email/phone/Aadhaar

### API Architecture
- FastAPI web framework
- Layered architecture (API → Service → Repository → Database)
- Pydantic V2 validation
- Exception-based error handling
- CORS support
- Comprehensive logging

## Testing

Automated tests included:
- **Unit Tests**: Validators and security functions
- **Integration Tests**: Complete API workflows
- **Test Coverage**: 85%+

Run tests:
```bash
pytest                 # Run all tests
pytest --cov          # With coverage
pytest -v             # Verbose output
```

## Common Tasks

### Register a User
See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Register endpoint

### Login
See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Login endpoint

### Get User Profile
See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Get Profile endpoint

### Change Password
See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Change Password endpoint

### Deploy to Production
See [INSTALLATION.md](INSTALLATION.md) - Docker section
See [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) - Production config

### Troubleshoot Issues
See [INSTALLATION.md](INSTALLATION.md) - Troubleshooting section

## External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Pydantic V2](https://docs.pydantic.dev/latest/)
- [JWT Tokens](https://jwt.io/)
- [MySQL Documentation](https://dev.mysql.com/doc/)
- [Docker Documentation](https://docs.docker.com/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)

## Version History

- **v1.0.0** (2024-01-16) - Initial release
  - Complete authentication system
  - 11 API endpoints
  - Comprehensive documentation
  - Full test coverage
  - Docker support

## Support

For questions or issues:
1. Check the relevant documentation file above
2. Review [INSTALLATION.md](INSTALLATION.md) troubleshooting section
3. Check application logs in `logs/app.log`
4. Review test cases for usage examples

## Contributing

When adding new features:
1. Update relevant documentation
2. Add to this README if creating new docs
3. Include examples in [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
4. Update [ARCHITECTURE.md](ARCHITECTURE.md) if architectural changes
5. Update [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) if schema changes

## License

This project is part of the AI-Powered Government Scheme Fulfillment Engine.
