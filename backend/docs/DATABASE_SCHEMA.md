# Database Schema Documentation

## Overview

The Citizen Registration & Authentication Module uses a MySQL database with a production-ready schema designed for scalability and future module integration.

## Tables

### 1. Citizens Table

The central table storing citizen identity and authentication information.

#### Schema

```sql
CREATE TABLE citizens (
  id CHAR(36) PRIMARY KEY,
  email VARCHAR(254) UNIQUE NOT NULL,
  phone VARCHAR(20) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(100) NOT NULL,
  gender ENUM('male', 'female', 'other', 'prefer_not_to_say'),
  date_of_birth DATETIME,
  
  -- Government Identities
  aadhaar_number VARCHAR(12) UNIQUE,
  smart_ration_card VARCHAR(20) UNIQUE,
  
  -- Address
  address_line1 VARCHAR(255),
  address_line2 VARCHAR(255),
  village VARCHAR(100),
  taluk VARCHAR(100),
  district VARCHAR(100) NOT NULL,
  state VARCHAR(50) NOT NULL,
  pincode VARCHAR(6),
  
  -- Profile
  preferred_language VARCHAR(20) DEFAULT 'en',
  profile_photo_url VARCHAR(500),
  
  -- Verification
  email_verified BOOLEAN DEFAULT FALSE,
  email_verified_at DATETIME,
  phone_verified BOOLEAN DEFAULT FALSE,
  phone_verified_at DATETIME,
  
  -- Account Status
  account_active BOOLEAN DEFAULT TRUE,
  account_locked BOOLEAN DEFAULT FALSE,
  failed_login_attempts INT DEFAULT 0,
  last_login DATETIME,
  last_login_ip VARCHAR(45),
  
  -- Status
  status ENUM('active', 'inactive', 'suspended', 'pending_verification') NOT NULL,
  status_reason VARCHAR(255),
  
  -- Future Modules
  digilocker_token VARCHAR(500),
  digilocker_sync_at DATETIME,
  preferred_voice_language VARCHAR(20),
  voice_authentication_enabled BOOLEAN DEFAULT FALSE,
  
  -- Soft Delete
  is_deleted BOOLEAN DEFAULT FALSE,
  deleted_at DATETIME,
  
  -- Audit
  created_at DATETIME NOT NULL DEFAULT NOW(),
  updated_at DATETIME NOT NULL DEFAULT NOW() ON UPDATE NOW(),
  created_by CHAR(36),
  updated_by CHAR(36)
);
```

#### Column Descriptions

| Column | Type | Constraints | Description | Use Case |
|--------|------|-------------|-------------|----------|
| id | CHAR(36) | PK | UUID primary key | Unique identifier |
| email | VARCHAR(254) | UNIQUE, NOT NULL | Email address | Login, notifications |
| phone | VARCHAR(20) | UNIQUE, NOT NULL | Phone number | Verification, notifications |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt hash | Authentication |
| full_name | VARCHAR(100) | NOT NULL | Full name | Display, documents |
| gender | ENUM | | Gender | Demographics |
| date_of_birth | DATETIME | | Date of birth | Age verification, eligibility |
| aadhaar_number | VARCHAR(12) | UNIQUE | Aadhaar ID | Identity verification |
| smart_ration_card | VARCHAR(20) | UNIQUE | Ration card ID | Identity verification |
| address_line1 | VARCHAR(255) | | Street address | Documents |
| address_line2 | VARCHAR(255) | | Secondary address | Documents |
| village | VARCHAR(100) | | Village name | Location-based services |
| taluk | VARCHAR(100) | | Taluk/block name | Jurisdiction |
| district | VARCHAR(100) | NOT NULL | District name | Location filtering |
| state | VARCHAR(50) | NOT NULL | State name | Location filtering |
| pincode | VARCHAR(6) | | Postal code | Delivery, services |
| preferred_language | VARCHAR(20) | DEFAULT 'en' | Language preference | Module 6 voice processing |
| profile_photo_url | VARCHAR(500) | | Photo URL | Display, documents |
| email_verified | BOOLEAN | DEFAULT FALSE | Verification flag | Access control |
| email_verified_at | DATETIME | | Verification timestamp | Audit trail |
| phone_verified | BOOLEAN | DEFAULT FALSE | Verification flag | Access control |
| phone_verified_at | DATETIME | | Verification timestamp | Audit trail |
| account_active | BOOLEAN | DEFAULT TRUE | Active status | Login control |
| account_locked | BOOLEAN | DEFAULT FALSE | Locked flag | Brute force protection |
| failed_login_attempts | INT | DEFAULT 0 | Failed attempt count | Security tracking |
| last_login | DATETIME | | Last login timestamp | Analytics |
| last_login_ip | VARCHAR(45) | | Last login IP | Security, analytics |
| status | ENUM | NOT NULL | Account status | Access control |
| status_reason | VARCHAR(255) | | Reason for status | Audit trail |
| digilocker_token | VARCHAR(500) | | DigiLocker token | Module 2 integration |
| digilocker_sync_at | DATETIME | | Last sync timestamp | Module 2 integration |
| preferred_voice_language | VARCHAR(20) | | Voice language | Module 6 integration |
| voice_authentication_enabled | BOOLEAN | DEFAULT FALSE | Voice auth flag | Module 6 integration |
| is_deleted | BOOLEAN | DEFAULT FALSE | Soft delete flag | Data retention |
| deleted_at | DATETIME | | Deletion timestamp | Audit trail |
| created_at | DATETIME | NOT NULL | Creation timestamp | Audit trail |
| updated_at | DATETIME | NOT NULL | Update timestamp | Audit trail |
| created_by | CHAR(36) | | Creator citizen ID | Audit trail |
| updated_by | CHAR(36) | | Updater citizen ID | Audit trail |

#### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| PRIMARY | id | Primary key |
| UQ_email | email | Email uniqueness |
| UQ_phone | phone | Phone uniqueness |
| UQ_aadhaar | aadhaar_number | Aadhaar uniqueness |
| UQ_ration_card | smart_ration_card | Ration card uniqueness |
| IX_email | email | Email lookups |
| IX_phone | phone | Phone lookups |
| IX_email_status | email, status | Filter by status |
| IX_phone_status | phone, status | Filter by status |
| IX_aadhaar_status | aadhaar_number, status | Filter by status |
| IX_district_state | district, state | Location-based queries |
| IX_created_at | created_at | Time-based queries |
| IX_updated_at | updated_at | Time-based queries |
| IX_is_deleted | is_deleted | Soft delete filtering |

#### Sample Data

```sql
INSERT INTO citizens (
  id, email, phone, password_hash, full_name, 
  gender, district, state, created_at, updated_at
) VALUES (
  'f47ac10b-58cc-4372-a567-0e02b2c3d479',
  'citizen@example.com',
  '9876543210',
  '$2b$12$...',  -- bcrypt hash
  'John Doe',
  'male',
  'Chennai',
  'Tamil Nadu',
  NOW(),
  NOW()
);
```

### 2. LoginAudits Table

Audit log table tracking all login attempts and activities.

#### Schema

```sql
CREATE TABLE login_audits (
  id CHAR(36) PRIMARY KEY,
  citizen_id CHAR(36) NOT NULL,
  login_type VARCHAR(20) NOT NULL,
  success BOOLEAN NOT NULL,
  failure_reason VARCHAR(255),
  ip_address VARCHAR(45),
  user_agent VARCHAR(500),
  created_at DATETIME NOT NULL DEFAULT NOW()
);
```

#### Column Descriptions

| Column | Type | Description |
|--------|------|-------------|
| id | CHAR(36) | Unique audit record ID |
| citizen_id | CHAR(36) | Citizen being audited |
| login_type | VARCHAR(20) | Type (password, refresh_token, etc) |
| success | BOOLEAN | Success/failure flag |
| failure_reason | VARCHAR(255) | Reason if failed (invalid_password, account_locked, etc) |
| ip_address | VARCHAR(45) | Client IP address (IPv4/IPv6) |
| user_agent | VARCHAR(500) | Browser/client user agent |
| created_at | DATETIME | Timestamp of attempt |

#### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| PRIMARY | id | Primary key |
| IX_citizen_id | citizen_id | Citizen lookups |
| IX_success | success | Filter by success/failure |
| IX_created_at | created_at | Time-based queries |

#### Sample Data

```sql
INSERT INTO login_audits (
  id, citizen_id, login_type, success, ip_address, created_at
) VALUES (
  '123e4567-e89b-12d3-a456-426614174000',
  'f47ac10b-58cc-4372-a567-0e02b2c3d479',
  'password',
  TRUE,
  '192.168.1.100',
  NOW()
);

-- Failed attempt
INSERT INTO login_audits (
  id, citizen_id, login_type, success, failure_reason, ip_address, created_at
) VALUES (
  '223e4567-e89b-12d3-a456-426614174001',
  'f47ac10b-58cc-4372-a567-0e02b2c3d479',
  'password',
  FALSE,
  'invalid_password',
  '192.168.1.101',
  NOW()
);
```

## Relationships

### Citizens to LoginAudits

- **One-to-Many**: One citizen can have multiple login audit records
- **Foreign Key**: `login_audits.citizen_id` -> `citizens.id`
- **Cascading**: Delete cascade (remove audits when citizen deleted)

## Views (Optional)

### Recent Failed Attempts

```sql
CREATE VIEW vw_recent_failed_attempts AS
SELECT
  c.id,
  c.email,
  c.failed_login_attempts,
  c.account_locked,
  la.ip_address,
  la.failure_reason,
  la.created_at
FROM citizens c
JOIN login_audits la ON c.id = la.citizen_id
WHERE la.success = FALSE
  AND la.created_at >= DATE_SUB(NOW(), INTERVAL 30 MINUTE)
ORDER BY la.created_at DESC;
```

### Citizen Statistics

```sql
CREATE VIEW vw_citizen_statistics AS
SELECT
  COUNT(*) as total_citizens,
  SUM(CASE WHEN account_active = TRUE THEN 1 ELSE 0 END) as active_citizens,
  SUM(CASE WHEN account_locked = TRUE THEN 1 ELSE 0 END) as locked_accounts,
  SUM(CASE WHEN email_verified = TRUE THEN 1 ELSE 0 END) as verified_email_count,
  DATE(created_at) as registration_date
FROM citizens
WHERE is_deleted = FALSE
GROUP BY DATE(created_at);
```

## Queries

### Find Citizen by Email

```sql
SELECT * FROM citizens 
WHERE email = 'citizen@example.com' 
  AND is_deleted = FALSE;
```

### Get Login History

```sql
SELECT * FROM login_audits 
WHERE citizen_id = 'f47ac10b-58cc-4372-a567-0e02b2c3d479'
ORDER BY created_at DESC
LIMIT 10;
```

### Find Locked Accounts

```sql
SELECT id, email, phone, failed_login_attempts, last_login
FROM citizens 
WHERE account_locked = TRUE 
  AND is_deleted = FALSE;
```

### Citizens by Location

```sql
SELECT district, state, COUNT(*) as count
FROM citizens 
WHERE is_deleted = FALSE
  AND account_active = TRUE
GROUP BY district, state
ORDER BY count DESC;
```

## Constraints & Validation

### Unique Constraints
- Email must be unique (case-insensitive)
- Phone must be unique
- Aadhaar must be unique (when provided)
- Ration card must be unique (when provided)

### NOT NULL Constraints
- email, phone, password_hash (authentication)
- full_name, district, state (profile)
- created_at, updated_at (audit)

### Default Values
- preferred_language: 'en'
- account_active: TRUE
- account_locked: FALSE
- email_verified, phone_verified: FALSE
- is_deleted: FALSE

### Data Type Considerations
- UUID (CHAR(36)) for IDs
- VARCHAR(254) for email (RFC 5321)
- VARCHAR(20) for phone (allow international formats)
- ENUM for fixed-value fields
- DATETIME for all timestamps (UTC)

## Future Extensibility

The schema is designed to support:

### Module 2: DigiLocker
- `digilocker_token`: OAuth token
- `digilocker_sync_at`: Last sync timestamp
- Fields for document storage references

### Module 4: Eligibility
- Could add citizenship status
- Land ownership flags
- Income category

### Module 6: Voice Processing
- `preferred_voice_language`: Language for voice
- `voice_authentication_enabled`: V2FA flag

### Module 8: Notifications
- Could add notification preferences
- Language preferences for messages

## Backup & Recovery

### Backup Strategy
```bash
# Daily backup
mysqldump citizen_auth_db > citizen_auth_db_backup_$(date +%Y%m%d).sql

# Incremental binary log backups
mysqlbinlog --start-date='2024-01-01' /var/log/mysql/mysql-bin.* > incremental.sql
```

### Recovery
```bash
# Full restore
mysql citizen_auth_db < citizen_auth_db_backup_20240101.sql

# Point-in-time recovery
mysql citizen_auth_db < incremental.sql
```

## Performance Optimization

### Query Optimization
1. Use indexed columns in WHERE clauses
2. Avoid SELECT * - select only needed columns
3. Use LIMIT for large result sets
4. Use INNER JOIN for related data

### Index Usage
- Email/phone lookups use indexes
- Status filtering uses compound indexes
- Location-based queries use district/state index
- Timestamp-based queries use created_at/updated_at indexes

### Soft Deletes
- `is_deleted = FALSE` on all WHERE clauses
- Separate index for soft delete filtering
- Periodic archival of deleted records

## Maintenance

### Regular Tasks
1. Index optimization: `OPTIMIZE TABLE citizens, login_audits;`
2. Check table integrity: `CHECK TABLE citizens, login_audits;`
3. Update statistics: `ANALYZE TABLE citizens, login_audits;`
4. Archive old audit logs (> 1 year)

### Monitoring
- Monitor table sizes
- Track index usage
- Monitor slow queries
- Alert on failed login spikes
