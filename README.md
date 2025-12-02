# OrgMeet (Part of OrgSuite)

**OrgMeet** is the governance and meeting management module of the **OrgSuite** platform - an open-source suite of tools for nonprofits, fraternities/sororities, and service-based companies. OrgMeet combines structured meeting management (inspired by OpenSlides) with real-time video conferencing (via Jitsi Meet).

## OrgSuite Platform

OrgSuite is a modular platform with the following modules:

| Module | Description | Status |
|--------|-------------|--------|
| **Governance (OrgMeet)** | Meeting management, motions, voting, minutes | ✅ Complete |
| **Membership** | Member tracking, contacts (donors, vendors, sponsors) | ✅ Complete |
| **Finance** | Chart of Accounts, double-entry bookkeeping, donations | ✅ Complete |
| **Events** | Event management, projects | 🔜 Planned |
| **Documents** | File management, organization documents | ✅ Complete |

## Features

### Core Features (Governance/OrgMeet)
- **Organization Hierarchy**: Organizations → Committees → Meetings
- **Agenda Management**: Create and manage meeting agendas with topics, motions, and elections
- **Motion & Voting**: Submit motions, conduct electronic voting with multiple methods
- **Video Conferencing**: Integrated HD video via Jitsi Meet with screen sharing and chat
- **Real-time Updates**: Live synchronization across all participants
- **Speaker Queue**: Manage speaking order with points of order support

### Governance Features
- **Meeting Lifecycle**: Track meetings through scheduled → in_progress → completed states
- **Quorum Tracking**: Configure required quorum and track attendance in real-time
- **Motion Workflow**: Full motion state machine (draft → submitted → screening → discussion → voting → accepted/rejected)
- **Poll Management**: Open/close polls with automatic result calculation

### Membership Features (New)
- **Member Management**: Track organization members with status (active, inactive, pending, alumni, guest, honorary, suspended)
- **Member Types**: Regular, associate, lifetime, student, board, volunteer, staff
- **Contact Management**: Track third-party entities - donors, vendors, sponsors, partners, grant makers
- **Member Profiles**: Address, phone, email, join date, expiry date, member number

### Finance Features (New)
- **Chart of Accounts**: Full double-entry bookkeeping with account types (asset, liability, equity, income, expense)
- **Journal Entries**: Create, post, and void journal entries with balanced debit/credit lines
- **Donation Tracking**: Track donations from members or contacts with payment methods and receipts
- **Dimension Placeholders**: Future support for departments, projects, classes, locations (Intacct-style)

### Productivity Features
- **Meeting Templates**: Pre-built templates for common organization types (HOA, nonprofit, fraternity, church, corporate)
- **Auto-Generated Minutes**: Generate structured meeting minutes with decisions and attendance
- **Decision Log**: Track all decisions across meetings in one place
- **ICS Calendar Export**: Add meetings to any calendar application
- **Email Notifications**: Send meeting invitations to participants

### New in v2.0
- **Role-Based Permissions**: Organization memberships with Owner/Admin/Member/Viewer roles
- **Document Management**: Upload and organize files for organizations and meetings
- **AI Integration**: Connect your OpenAI or Anthropic API key for:
  - AI-generated meeting summaries
  - Agenda suggestions
  - Motion drafting assistance
- **Recording Support**: Store and manage meeting recordings (URLs or uploaded files)
- **Enhanced Email Notifications**: Rich HTML emails with ICS calendar attachments

## Feature Matrix

| Feature | Free (Self-Hosted) | Pro (Cloud) | Enterprise |
|---------|-------------------|-------------|------------|
| **Core Meeting Management** | ✅ Unlimited | ✅ Unlimited | ✅ Unlimited |
| Organizations & Committees | ✅ | ✅ | ✅ |
| Agenda & Motions | ✅ | ✅ | ✅ |
| Voting & Polls | ✅ | ✅ | ✅ |
| Video Conferencing (Jitsi) | ✅ | ✅ | ✅ Custom |
| Quorum Tracking | ✅ | ✅ | ✅ |
| Meeting Minutes | ✅ | ✅ | ✅ |
| ICS Calendar Export | ✅ | ✅ | ✅ |
| **Document Management** | | | |
| File Uploads | ✅ 100MB | ✅ 5GB | ✅ Unlimited |
| Organization Documents | ✅ | ✅ | ✅ |
| Meeting Attachments | ✅ | ✅ | ✅ |
| **AI Features** | | | |
| AI Meeting Summaries | ✅ BYOK* | ✅ Included | ✅ Included |
| AI Agenda Suggestions | ✅ BYOK* | ✅ Included | ✅ Included |
| AI Motion Drafting | ✅ BYOK* | ✅ Included | ✅ Included |
| **Recording & Media** | | | |
| Recording URLs | ✅ | ✅ | ✅ |
| Recording Uploads | ❌ | ✅ 5GB | ✅ Unlimited |
| **Permissions & Security** | | | |
| Role-Based Access | ✅ | ✅ | ✅ |
| Organization Memberships | ✅ 10 members | ✅ 100 members | ✅ Unlimited |
| **Notifications** | | | |
| Email Notifications | ✅ Self-host SMTP | ✅ Included | ✅ Included |
| Calendar Invites (ICS) | ✅ | ✅ | ✅ |
| **Support** | | | |
| Community Support | ✅ | ✅ | ✅ |
| Priority Support | ❌ | ✅ | ✅ |
| Dedicated Support | ❌ | ❌ | ✅ |
| SLA | ❌ | ❌ | ✅ |

*BYOK = Bring Your Own Key (provide your own OpenAI or Anthropic API key)

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git (to clone the repository)

### Backend Options

OrgMeet supports two backend configurations:

| Backend | Database | Status | Use Case |
|---------|----------|--------|----------|
| **FastAPI + PostgreSQL** | PostgreSQL | ✅ Recommended | Production, OrgSuite integration |
| PocketBase | SQLite | ⚠️ Legacy | Simple deployments |

---

## FastAPI Backend (Recommended)

The FastAPI backend uses PostgreSQL for robust production deployments and integrates with the larger OrgSuite platform.

### Development Environment (FastAPI)

```bash
# Clone the repository
git clone <repository-url>
cd orgmeet

# Copy environment file and configure
cp .env.fastapi.example .env

# Start development environment
docker compose -f docker-compose.fastapi.yml up -d

# Run database migrations
docker compose -f docker-compose.fastapi.yml exec backend alembic upgrade head
```

**Access points (FastAPI development):**
- Frontend: http://localhost:3000
- API: http://localhost:3000/api/
- API Docs (Swagger): http://localhost:8000/docs
- API Docs (ReDoc): http://localhost:8000/redoc
- PostgreSQL: localhost:5432

### Production Environment (FastAPI)

```bash
# Copy and configure production environment
cp .env.fastapi.example .env
# Edit .env with production values (strong SECRET_KEY, proper CORS origins, etc.)

# Start production environment
docker compose -f docker-compose.fastapi.prod.yml up -d

# Run database migrations
docker compose -f docker-compose.fastapi.prod.yml exec backend alembic upgrade head
```

**Access points (FastAPI production):**
- Frontend: http://localhost:3000
- API: Proxied through `/api/`
- Database: Internal network only

### Running Alembic Migrations

```bash
# Development
docker compose -f docker-compose.fastapi.yml exec backend alembic upgrade head

# Production
docker compose -f docker-compose.fastapi.prod.yml exec backend alembic upgrade head

# Create a new migration (after modifying models)
docker compose -f docker-compose.fastapi.yml exec backend alembic revision --autogenerate -m "description"

# Downgrade one version
docker compose -f docker-compose.fastapi.yml exec backend alembic downgrade -1

# View migration history
docker compose -f docker-compose.fastapi.yml exec backend alembic history
```

### Migrating from PocketBase to PostgreSQL

If you have existing data in PocketBase, use the migration script:

```bash
# Ensure the FastAPI stack is running
docker compose -f docker-compose.fastapi.yml up -d

# Run the migration script
python scripts/migrate_pocketbase_to_postgres.py \
  --pocketbase-db ./pocketbase/pb_data/data.db \
  --postgres-url "postgresql://orgmeet:orgmeet_dev@localhost:5432/orgmeet"

# Or with Docker
docker compose -f docker-compose.fastapi.yml exec backend python /app/scripts/migrate_pocketbase_to_postgres.py
```

The migration script:
- Reads all data from PocketBase SQLite database
- Maps PocketBase collections to PostgreSQL tables
- Preserves IDs and relationships
- Handles password hashes correctly
- Reports migration statistics

---

## PocketBase Backend (Legacy)

> ⚠️ **Deprecated**: The PocketBase backend is maintained for backwards compatibility but is not recommended for new deployments.

### Development Environment (PocketBase)

```bash
# Start development environment
./scripts/start-dev.sh

# Or manually:
docker compose -f docker-compose.dev.yml up -d
```

**Access points (PocketBase development):**
- Frontend: http://localhost:3000
- PocketBase API: http://localhost:8090/api/
- PocketBase Admin: http://localhost:8090/_/

### Production Environment (PocketBase)

```bash
# Start production environment
./scripts/start-prod.sh

# Or manually:
docker compose up -d
```

**Access points (PocketBase production):**
- Frontend: http://localhost:3000
- PocketBase API: Proxied through `/api/`
- PocketBase Admin: **Not publicly accessible** (see below)

---

## Runtime Configuration

The static frontend reads runtime settings from `frontend/config.json`, allowing you to change API and site URLs without rebuilding.

- File: `frontend/config.json`
- Keys: `APP_ENV`, `PB_URL`, `JITSI_DOMAIN`, `SITE_URL`, `DEBUG`

Example:

```json
{
  "APP_ENV": "production",
  "PB_URL": "/api",
  "JITSI_DOMAIN": "meet.jit.si",
  "SITE_URL": "https://orgmeet.example.com",
  "DEBUG": false
}
```

Notes:
- `config.json` is served directly by Nginx and can be edited at runtime.
- For FastAPI backend, the frontend works identically (API endpoints are compatible).

## Nginx Configuration Files

| Backend | Dev Config | Prod Config |
|---------|------------|-------------|
| FastAPI | `nginx.fastapi.conf` | `nginx.fastapi.prod.conf` |
| PocketBase | `nginx.dev.conf` | `nginx.prod.conf` |

### Image versioning

To ensure stability, images are pinned:
- Nginx: `nginx:1.27-alpine`
- Python: `python:3.12-slim`
- PostgreSQL: `postgres:16-alpine`
- PocketBase (legacy): `ghcr.io/muchobien/pocketbase:0.22.15`

Update versions intentionally and test before deployment.

## Architecture

### FastAPI Backend (Recommended)

```
┌─────────────────────────────────────────────────────┐
│  Browser (localhost:3000)                           │
│  ┌─────────────────────────────────────────────┐   │
│  │  HTML + Tailwind CSS + HTMX                  │   │
│  │  + PocketBase JS SDK (API-compatible)        │   │
│  └──────────────────┬──────────────────────────┘   │
└─────────────────────┼───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  Nginx (Docker: orgmeet-frontend)                   │
│  - Serves static files                              │
│  - Proxies /api/* to FastAPI                        │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  FastAPI (Docker: orgmeet-backend)                  │
│  - REST API (PocketBase-compatible endpoints)       │
│  - SQLAlchemy ORM with async support                │
│  - JWT authentication                               │
│  - Alembic migrations                               │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  PostgreSQL (Docker: orgmeet-postgres)              │
│  - Relational database with full ACID compliance   │
│  - Production-grade performance                     │
└─────────────────────────────────────────────────────┘
```

### PocketBase Backend (Legacy)

```
┌─────────────────────────────────────────────────────┐
│  Browser (localhost:3000)                           │
│  ┌─────────────────────────────────────────────┐   │
│  │  HTML + Tailwind CSS + HTMX                  │   │
│  │  + PocketBase JS SDK                         │   │
│  └──────────────────┬──────────────────────────┘   │
└─────────────────────┼───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  Nginx (Docker: orgmeet-frontend)                   │
│  - Serves static files                              │
│  - Proxies /api/* to PocketBase                     │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  PocketBase (Docker: orgmeet-pocketbase)            │
│  - REST API + Real-time subscriptions               │
│  - SQLite database (WAL mode)                       │
│  - User authentication                              │
└─────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env.dev` or `.env.prod` and configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | development |
| `PB_URL` | PocketBase API URL | /api |
| `JITSI_DOMAIN` | Jitsi Meet server | meet.jit.si |
| `SITE_URL` | Public site URL | http://localhost:3000 |
| `DEBUG` | Enable debug logging | true |

### Self-Hosting Jitsi

By default, OrgMeet uses the public `meet.jit.si` server. For private video conferencing:

1. Deploy your own Jitsi Meet server
2. Update `JITSI_DOMAIN` in your `.env` file
3. Restart the application

## Accessing PocketBase Admin UI

### Development

In development mode, the admin UI is accessible at:
```
http://localhost:8090/_/
```

### Production

For security, the admin UI is **not publicly exposed** in production. Access it via:

**Option 1: SSH Tunnel (Recommended)**
```bash
ssh -L 8090:localhost:8090 user@your-server
# Then access: http://localhost:8090/_/
```

**Option 2: Docker exec**
```bash
# Access container directly
docker exec -it orgmeet-pocketbase /bin/sh
```

## Project Structure

```
orgmeet/
├── docker-compose.yml              # PocketBase production config
├── docker-compose.dev.yml          # PocketBase development config
├── docker-compose.fastapi.yml      # FastAPI development config
├── docker-compose.fastapi.prod.yml # FastAPI production config
├── nginx.prod.conf                 # PocketBase prod Nginx
├── nginx.dev.conf                  # PocketBase dev Nginx
├── nginx.fastapi.conf              # FastAPI dev Nginx
├── nginx.fastapi.prod.conf         # FastAPI prod Nginx
├── .env.fastapi.example            # FastAPI environment template
├── .env.dev                        # PocketBase dev environment
├── .env.prod                       # PocketBase prod environment
│
├── backend/                        # FastAPI Backend (OrgSuite)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   └── app/
│       ├── main.py                 # FastAPI application
│       ├── core/
│       │   ├── config.py           # Settings
│       │   ├── security.py         # JWT & password hashing
│       │   └── deps.py             # Dependencies
│       ├── db/
│       │   ├── base.py             # Database session
│       │   └── migrations/         # Alembic migrations
│       │       └── versions/
│       │           ├── 001_initial.py           # Core tables
│       │           └── 002_membership_finance.py # Membership & Finance
│       ├── models/                 # SQLAlchemy models
│       │   ├── base.py             # Base model with timestamps
│       │   ├── user.py
│       │   ├── organization.py
│       │   ├── meeting.py
│       │   ├── member.py           # NEW: Membership module
│       │   ├── contact.py          # NEW: Membership module
│       │   ├── account.py          # NEW: Finance module (Chart of Accounts)
│       │   ├── journal_entry.py    # NEW: Finance module
│       │   ├── journal_line.py     # NEW: Finance module
│       │   ├── donation.py         # NEW: Finance module
│       │   └── ...
│       ├── schemas/                # Pydantic schemas
│       │   ├── auth.py
│       │   ├── organization.py
│       │   ├── member.py           # NEW
│       │   ├── contact.py          # NEW
│       │   ├── account.py          # NEW
│       │   ├── journal.py          # NEW
│       │   └── ...
│       └── api/
│           └── v1/                 # API endpoints (modular)
│               ├── auth.py
│               ├── governance/     # OrgMeet module
│               │   ├── organizations.py
│               │   ├── meetings.py
│               │   ├── motions.py
│               │   └── ...
│               ├── membership/     # Membership module (NEW)
│               │   ├── members.py
│               │   └── contacts.py
│               ├── finance/        # Finance module (NEW)
│               │   ├── accounts.py
│               │   └── journal.py
│               ├── events/         # Events module (planned)
│               └── documents/      # Documents module
│                   └── files.py
│
├── frontend/
│   ├── index.html                  # Landing page
│   ├── config.json                 # Runtime configuration
│   ├── pages/                      # Application pages
│   │   ├── dashboard.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── meetings.html
│   │   ├── meeting.html
│   │   ├── account.html
│   │   ├── organizations.html
│   │   └── organization.html
│   ├── fragments/                  # HTMX HTML fragments
│   ├── js/
│   │   ├── app.js                  # Main application logic
│   │   ├── config.js               # Frontend configuration
│   │   └── pocketbase.umd.js       # PocketBase SDK
│   └── css/
│       └── custom.css              # Custom styles
│
├── pocketbase/                     # Legacy PocketBase
│   ├── pb_data/                    # Database and storage
│   ├── pb_migrations/              # Database migrations
│   └── pb_hooks/                   # Server-side hooks
│
├── scripts/
│   ├── start-dev.sh                # PocketBase dev startup
│   ├── start-prod.sh               # PocketBase prod startup
│   └── migrate_pocketbase_to_postgres.py  # Data migration
│
└── tests/                          # Playwright E2E tests
    ├── playwright.config.js
    ├── auth-stability.spec.js
    ├── core-flows.spec.js
    ├── meetings.spec.js
    ├── account.spec.js
    └── organization-details.spec.js
```

## Common Commands

### FastAPI Backend (Recommended)

```bash
# Start development environment
docker compose -f docker-compose.fastapi.yml up -d

# Run database migrations
docker compose -f docker-compose.fastapi.yml exec backend alembic upgrade head

# View logs
docker compose -f docker-compose.fastapi.yml logs -f

# View backend logs only
docker compose -f docker-compose.fastapi.yml logs -f backend

# Stop services
docker compose -f docker-compose.fastapi.yml down

# Rebuild containers
docker compose -f docker-compose.fastapi.yml up -d --build

# Access PostgreSQL CLI
docker compose -f docker-compose.fastapi.yml exec postgres psql -U orgmeet -d orgmeet

# Run Playwright tests
cd tests && npm test
```

### PocketBase Backend (Legacy)

```bash
# Start development environment
./scripts/start-dev.sh

# Start production environment
./scripts/start-prod.sh

# View logs
docker compose -f docker-compose.dev.yml logs -f

# Stop services
docker compose -f docker-compose.dev.yml down

# Rebuild containers
docker compose -f docker-compose.dev.yml up -d --build
```

## Technology Stack

### FastAPI Backend (Recommended)

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Auth | JWT (PyJWT + bcrypt) |
| Frontend | HTML + Tailwind CSS + HTMX |
| API Client | PocketBase JavaScript SDK (API-compatible) |
| Video | Jitsi Meet External API |
| Web Server | Nginx |
| Containers | Docker Compose |

### PocketBase Backend (Legacy)

| Layer | Technology |
|-------|------------|
| Backend | PocketBase (Go + SQLite WAL) |
| Frontend | HTML + Tailwind CSS + HTMX |
| API Client | PocketBase JavaScript SDK |
| Video | Jitsi Meet External API |
| Web Server | Nginx |
| Containers | Docker Compose |

## Meeting Templates

OrgMeet includes pre-built templates for common organization types:

| Template | Organization Type | Description |
|----------|------------------|-------------|
| Fraternity/Sorority Chapter | fraternity | Standard chapter meeting with roll call, officer reports, ritualistic closing |
| HOA Board Meeting | hoa | Homeowners Association board meeting following Robert's Rules |
| Nonprofit Board Meeting | nonprofit | Standard nonprofit board meeting with governance focus |
| Church Council Meeting | church | Church leadership council or vestry meeting format |
| Corporate Board Meeting | corporate | Formal corporate board meeting with governance practices |
| General Meeting | generic | Simple meeting format suitable for any organization |

Each template includes:
- Pre-configured agenda items with suggested durations
- Default quorum settings
- Meeting type classification

## Motion Workflow

Motions follow a structured workflow:

```
draft → submitted → screening → discussion → voting → accepted
                                                    ↘ rejected
                        ↓ (any state)
                      withdrawn
                      tabled
```

Moderators can transition motions through each state, and vote results are automatically recorded.

## Testing

OrgMeet uses Playwright for end-to-end testing. Tests are located in the `tests/` directory.

### Running Playwright Tests

```bash
# Navigate to tests directory
cd tests

# Install dependencies (first time only)
npm install
npx playwright install chromium

# Run all tests
npm test

# Run specific test file
npx playwright test auth-stability.spec.js

# Run tests with UI mode
npx playwright test --ui

# Run tests in headed mode (visible browser)
npx playwright test --headed

# View test report
npx playwright show-report
```

### Test Configuration

Tests are configured to run against `http://localhost:3000`. Ensure the application is running before executing tests:

```bash
# For FastAPI backend
docker compose -f docker-compose.fastapi.yml up -d
docker compose -f docker-compose.fastapi.yml exec backend alembic upgrade head

# Then run tests
cd tests && npm test
```

### Test Suites

| File | Description |
|------|-------------|
| `auth-stability.spec.js` | Login/logout flows, session persistence |
| `core-flows.spec.js` | Dashboard, organization creation, meeting flows |
| `meetings.spec.js` | Meeting scheduling, agenda management, voting |
| `account.spec.js` | Profile viewing/editing, password change |
| `organization-details.spec.js` | Organization settings, committee management |

## API Documentation

When running the FastAPI backend, interactive API documentation is available:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

The API is designed to be compatible with the PocketBase SDK, so the existing frontend works without modification.

### API Endpoints by Module

#### Legacy/PocketBase-Compatible Endpoints
These endpoints maintain backward compatibility with the PocketBase SDK:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/collections/users/records` | GET/POST | User management |
| `/api/collections/users/auth-with-password` | POST | User login |
| `/api/collections/organizations/records` | GET/POST | Organization management |
| `/api/collections/meetings/records` | GET/POST | Meeting management |
| `/api/collections/motions/records` | GET/POST | Motion management |
| `/api/collections/polls/records` | GET/POST | Poll management |

#### Membership Module (v1 API)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/membership/members` | GET | List organization members |
| `/api/v1/membership/members` | POST | Create a new member |
| `/api/v1/membership/members/{id}` | GET | Get member details |
| `/api/v1/membership/members/{id}` | PATCH | Update member |
| `/api/v1/membership/members/{id}` | DELETE | Delete member |
| `/api/v1/membership/contacts` | GET | List organization contacts |
| `/api/v1/membership/contacts` | POST | Create a new contact |
| `/api/v1/membership/contacts/{id}` | GET | Get contact details |
| `/api/v1/membership/contacts/{id}` | PATCH | Update contact |
| `/api/v1/membership/contacts/{id}` | DELETE | Delete contact |

#### Finance Module (v1 API)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/finance/accounts` | GET | List chart of accounts |
| `/api/v1/finance/accounts` | POST | Create a new account |
| `/api/v1/finance/accounts/{id}` | GET | Get account details |
| `/api/v1/finance/accounts/{id}` | PATCH | Update account |
| `/api/v1/finance/accounts/{id}` | DELETE | Delete account (if no journal lines) |
| `/api/v1/finance/journal-entries` | GET | List journal entries |
| `/api/v1/finance/journal-entries` | POST | Create journal entry with lines |
| `/api/v1/finance/journal-entries/{id}` | GET | Get journal entry with lines |
| `/api/v1/finance/journal-entries/{id}` | PATCH | Update draft journal entry |
| `/api/v1/finance/journal-entries/{id}` | DELETE | Delete draft journal entry |
| `/api/v1/finance/journal-entries/{id}/post` | POST | Post journal entry |
| `/api/v1/finance/journal-entries/{id}/void` | POST | Void posted journal entry |

### Finance Module Data Model

The finance module implements double-entry bookkeeping:

```
Account Types:
├── Asset (Cash, Bank, Accounts Receivable, Inventory, Fixed Assets)
├── Liability (Accounts Payable, Credit Card, Current/Long-term Liabilities)
├── Equity (Retained Earnings, Opening Balance)
├── Income (Operating Income, Donations, Dues, Grants)
└── Expense (Operating Expense, Cost of Goods, Payroll)

Journal Entry Workflow:
Draft → Posted → Voided
  │
  └── Must have balanced debits/credits to post
```

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting pull requests.

## License

MIT License - See [LICENSE](LICENSE) file for details.
