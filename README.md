# TaskFlow API - Knowledge Transfer (KT) & Architecture Guide

Welcome to the **TaskFlow API** repository. This document serves as the comprehensive Knowledge Transfer (KT) manual, architecture guide, and developer onboarding handbook for the project.

---

## 1. Project Overview & Vision

**TaskFlow API** is a high-performance, asynchronous RESTful backend service built on top of **FastAPI**, **SQLAlchemy 2.0 (Asyncpg)**, and **PostgreSQL**.

### Core Mission
TaskFlow is designed as a scalable task orchestration and workflow management platform. The current phase establishes the **enterprise-grade foundational layer**:
- Secure authentication & session lifecycle management.
- Cryptographically sound credential hashing (Argon2id).
- Dual-token authorization flow (short-lived JWT access tokens + rotating refresh tokens with token family compromise detection).
- Role-Based Access Control (RBAC) distinguishing standard users and superusers.
- Production-ready observability and security middleware (request tracing, security headers, CORS, trusted hosts).

---

## 2. System Architecture & Tech Stack

The service strictly adheres to a **layered separation-of-concerns** pattern, decoupling HTTP transport, domain business logic, data persistence, and system utilities.

```
┌────────────────────────────────────────────────────────┐
│                   Incoming HTTP Client                 │
└───────────────────────────┬────────────────────────────┘
                            │
               [Security & Tracing Middleware]
               - RequestIdMiddleware (X-Request-ID)
               - SecurityHeaderMiddleware (HSTS, nosniff, etc.)
               - CORSMiddleware & TrustedHostMiddleware
                            │
                            ▼
               [API Routers / Controllers]
         /auth (auth.py) | /users (users.py) | /admin (admin.py)
                            │
             [Core Security & Dependencies]
         - OAuth2 Bearer token validation
         - Role-Based guards (get_current_user, get_current_superuser)
                            │
                            ▼
               [Service Layer (Business Logic)]
            - auth_service.py   - user_service.py
                            │
                            ▼
            [Data Layer (SQLAlchemy 2.0 Async)]
         - Models: User, RefreshToken
         - Async Engine & Session (PostgreSQL + asyncpg)
                            │
                            ▼
                     [PostgreSQL DB]
```

### Technology Matrix

| Technology | Version / Specification | Purpose |
| :--- | :--- | :--- |
| **Python** | 3.12+ (tested on 3.14) | Base programming runtime |
| **FastAPI** | 0.165.0+ | Async web framework, dependency injection, OpenAPI documentation |
| **Starlette & Uvicorn** | 1.10.0 / 0.54.0 | ASGI web server and HTTP middleware foundation |
| **SQLAlchemy** | 2.0 (Async) | Modern asynchronous Object-Relational Mapper (ORM) |
| **Asyncpg** | Async driver | High-speed PostgreSQL async connectivity |
| **Alembic** | Latest | Database schema migrations and versioning |
| **Pydantic v2** | 2.14.4+ | Data validation, request payload parsing, response serialization |
| **pydantic-settings** | BaseSettings | Centralized environment configuration management |
| **Argon2-cffi** | Argon2id | Memory-hard, state-of-the-art password hashing |
| **PyJWT** | HS256 | Signed JSON Web Tokens for stateless access authorization |

---

## 3. Repository Structure

```
taskflow-api/
├── alembic/                      # Database migration scripts
│   ├── versions/                 # Individual migration revisions
│   │   ├── b191865154be_create_user_table.py
│   │   └── 8acbfd4eedce_create_user_and_refresh_token.py
│   ├── env.py                    # Alembic runtime environment (configured for async)
│   ├── script.py.mako            # Migration template
│   └── alembic.ini               # Alembic configuration
├── app/
│   ├── core/                     # Foundational infrastructure & cross-cutting concerns
│   │   ├── config.py             # App settings loaded from .env via Pydantic
│   │   ├── database.py           # Async engine, sessionmaker, and DB dependency (get_db)
│   │   ├── dependencies.py       # Auth dependencies (get_current_user, get_current_superuser)
│   │   ├── exceptions.py         # Custom application-level domain exceptions
│   │   ├── middleware.py         # Request ID tagging & security HTTP headers
│   │   ├── pagination.py         # Standard query pagination parameters
│   │   └── security.py           # Password hashing (Argon2), JWT encoding/decoding, token generation
│   ├── models/                   # SQLAlchemy declarative database entities
│   │   ├── user.py               # User table model
│   │   └── refresh_token.py      # RefreshToken table model
│   ├── schemas/                  # Pydantic request and response schemas (DTOs)
│   │   ├── auth.py               # TokenPair, RefreshRequest
│   │   └── user.py               # UserCreate, UserRead
│   ├── services/                 # Pure domain business logic layer
│   │   ├── auth_service.py       # Authentication, token generation, rotation, theft mitigation
│   │   └── user_service.py       # User creation, email lookup, database transactions
│   ├── routers/                  # HTTP endpoint route controllers
│   │   ├── admin.py              # Protected administrative routes
│   │   ├── auth.py               # Public authentication routes (/auth/register, /auth/login, etc.)
│   │   └── users.py              # User profile routes (/users/me, /users/{id})
│   └── main.py                   # FastAPI application factory, middleware, and router registration
├── tests/                        # Automated test suites (unit, integration)
├── .env.example                  # Template of required environment variables
├── requirements.txt              # Pinned Python package dependencies
└── README.md                     # Knowledge transfer and project documentation
```

---

## 4. Database Schema & Data Models

All models use UUID primary keys and timezone-aware timestamps.

### 4.1. `users` Table
Stores registered identities and authorization flags.

| Column | Type | Constraints / Defaults | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key, Index, default=`uuid4` | Unique user identifier |
| `email` | `VARCHAR(255)` | Unique, Index, Not Null | User's normalized lowercase email |
| `password` | `VARCHAR(255)` | Not Null | Argon2id hashed password string |
| `is_active` | `BOOLEAN` | Default=`True` | Status flag; inactive users cannot log in |
| `is_superuser` | `BOOLEAN` | Default=`False`, server_default=`false` | Elevated privileges flag for admin actions |
| `created_at` | `TIMESTAMPTZ` | server_default=`func.now()` | Record creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | server_default=`func.now()`, onupdate=`now()` | Last update timestamp |

### 4.2. `refresh_tokens` Table
Tracks long-lived refresh tokens with revocation support and reuse detection.

| Column | Type | Constraints / Defaults | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key, Index, default=`uuid4` | Refresh token record ID |
| `user_id` | `UUID` | ForeignKey(`users.id`, ondelete="CASCADE"), Index | Owner user ID |
| `token_hash` | `VARCHAR(64)` | Unique, Index, Not Null | SHA-256 hash of the plain refresh token |
| `expires_at` | `TIMESTAMPTZ` | Not Null | Token expiration timestamp (default: 7 days) |
| `revokes_at` | `TIMESTAMPTZ` | Nullable | Revocation timestamp; non-null indicates consumed or revoked |
| `created_at` | `TIMESTAMPTZ` | server_default=`func.now()` | Issued timestamp |
| `updated_at` | `TIMESTAMPTZ` | onupdate=`func.now()` | Last modification timestamp |

---

## 5. Security & Authentication Deep-Dive

### 5.1. Password Hashing
- Utilizes **Argon2id** via `argon2-cffi`.
- Resistant to GPU-based attacks, side-channel timing attacks, and memory-tradeoff optimization.
- Passwords are never logged or stored in plaintext.

### 5.2. Dual-Token Strategy
1. **Access Token (JWT)**:
   - Stateless, short-lived (configurable, default: **15 minutes**).
   - Payload: `sub` (user UUID string), `type: "access"`, `iat` (issued at), `exp` (expiration).
   - Validated on each authenticated request via the FastAPI dependency `get_current_user`.
2. **Refresh Token**:
   - Cryptographically random string (`secrets.token_urlsafe(48)`), long-lived (default: **7 days**).
   - Only the **SHA-256 hash** of the token is persisted in the database. The plain token is sent only once to the client.

### 5.3. Refresh Token Rotation & Theft Detection (Token Family Compromise)
To protect against token replay attacks:
1. When `/auth/refresh` is called with a valid refresh token:
   - The token is immediately marked as revoked (`revokes_at = now()`).
   - A brand new access token and a brand new refresh token are issued (rotation).
2. **Compromise Detection**:
   - If a refresh token is presented whose database record is **already revoked** (`revokes_at is not None`), it indicates that a malicious actor or replay has occurred.
   - The system immediately invokes `revoke_all_for_user(user_id)`, invalidating **all active refresh tokens** for that user account to stop the breach.

### 5.4. Security Headers & Request Tracing
The API automatically applies standard production HTTP headers via custom Starlette middleware:
- `X-Request-ID`: Correlation ID either propagated from client request or generated as a UUID4, returned in the response header for log tracing.
- `X-Content-Type-Options: nosniff`: Prevents MIME-type sniffing.
- `X-Frame-Options: DENY`: Prevents clickjacking.
- `Referrer-Policy: no-referrer`: Prevents referrer leakage.
- `Strict-Transport-Security (HSTS)`: Enforced when `debug=False` (`max-age=31536000; includeSubDomains`).

---

## 6. API Reference

All requests and responses use JSON format (`application/json`), except login which accepts `application/x-www-form-urlencoded` standard OAuth2 form data.

### Health Endpoints
| Method | Endpoint | Description | Auth Required | Status Code |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Application status | None | `200 OK` |
| `GET` | `/health/db` | Database connectivity probe (`SELECT 1`) | None | `200 OK` |

### Authentication Endpoints (`/auth`)
| Method | Endpoint | Description | Request Body | Response Body | Status Code |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register new user account | `UserCreate` (email, password, confirm_password) | `UserRead` | `201 Created` |
| `POST` | `/auth/login` | OAuth2 password login | `OAuth2PasswordRequestForm` (username=email, password) | `TokenPair` (access_token, refresh_token) | `200 OK` |
| `POST` | `/auth/refresh` | Rotate refresh token | `RefreshRequest` (refresh_token) | `TokenPair` | `200 OK` |
| `POST` | `/auth/logout` | Revoke active refresh token | `RefreshRequest` (refresh_token) | None | `204 No Content`|

### User Endpoints (`/users`)
| Method | Endpoint | Description | Auth Required | Status Code |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/users/me` | Retrieve profile of the authenticated user | Bearer Token (`User`) | `200 OK` |
| `GET` | `/users/{user_id}` | Retrieve profile by user UUID | Bearer Token (Self or `Superuser`) | `200 OK` |

### Admin Endpoints (`/admin`)
| Method | Endpoint | Query Parameters | Auth Required | Status Code |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/admin/users` | List paginated users | `limit` (default: 20, max: 100), `offset` (default: 0) | Bearer Token (`Superuser`) | `200 OK` |

---

## 7. Environment Configuration

Configuration is managed via `.env` and loaded through `app/core/config.py`.

Create a `.env` file in the root directory based on `.env.example`:

```env
APP_NAME=taskflow-api
DEBUG=True

DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/taskflow_db
SECRET_KEY=your-super-secret-jwt-signing-key-here-minimum-32-chars

# Optional overrides (defaults shown)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
ALLOWED_ORIGINS=["localhost", "127.0.0.1"]
```

---

## 8. Local Setup & Getting Started

### Prerequisites
- Python 3.12 or later
- PostgreSQL 14+ installed and running locally or via Docker

### 1. Clone & Setup Virtual Environment
```bash
# Clone the repository and navigate into it
cd taskflow-api

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Database & Run Migrations
Create your PostgreSQL database (e.g. `taskflow_db`), update your `.env` connection string, and run:
```bash
# Apply migrations to the latest revision
alembic upgrade head
```

To create a new migration when modifying SQLAlchemy models:
```bash
alembic revision --autogenerate -m "describe_migration_here"
alembic upgrade head
```

### 4. Run the Development Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Interactive API Documentation
When `DEBUG=True`, FastAPI exposes interactive Swagger documentation at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **OpenAPI Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 9. Code Quality & Developer Guidelines

- **Input Validation**: Never trust incoming data. Validate types, formats, and constraints in `app/schemas/`.
- **Response Shapes**: Every endpoint must return a structured Pydantic model (`response_model=...`).
- **Domain Service Separation**: Database queries and business rules belong in `app/services/`, not inside the route functions in `app/routers/`.
- **Error Handling**: Use custom domain exceptions (`app/core/exceptions.py`) inside services, catching and translating them into standard `HTTPException` responses at the router boundary.
- **Async Execution**: Never call blocking synchronous I/O functions (e.g. `requests`, `time.sleep`) inside `async def` routes or services. Always use async equivalents (`httpx`, `asyncio.sleep`).

---

## 10. Technical Audit & Upcoming Roadmap

As part of continuous engineering standards, the following items have been identified for upcoming sprints:

1. **Bug Fixes & Refinements in Current Code**:
   - `app/services/auth_service.py`: Fix indentation of helper functions (`_get_stored_token`, `rotate_refresh_token`, `revoke_refresh_token`) currently nested under `issue_token_pair`. In `issue_token_pair`, replace `await db.connect()` with `await db.commit()`.
   - `app/core/security.py`: In `decode_access_token`, change `jwt.encode` to `jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])`.
   - `app/services/user_service.py`: Update `User(email=..., password_hash=...)` parameter to match the model column attribute name `password` (or rename the model attribute to `password_hash`).
   - `app/schemas/user.py`: Add validation comparing `password` with `confirm_password` in `UserCreate`.
2. **Core TaskFlow Domain Features (Phase 2)**:
   - Task model & workflow pipelines (`tasks`, `workflows`, `task_assignments`).
   - Status transitions (Pending, In Progress, Blocked, Completed).
   - Task comments and activity audit logs.
3. **Automated Testing Suite**:
   - Add integration tests using `pytest` and `pytest-asyncio` with an in-memory SQLite / test Postgres container.
   - Test full auth cycles: register -> login -> access protected route -> refresh -> logout -> token replay rejection.
