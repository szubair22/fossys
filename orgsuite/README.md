# OrgSuite - Stage 1: OrgMeet Governance for Nonprofits

**OrgSuite** is an open-source platform for small organizations, nonprofits, fraternities/sororities, and service-based companies. It provides governance, membership, and finance tools with a modular architecture.

## Stage 1: OrgMeet Governance (Current)

Stage 1 focuses on **governance and meeting management**, combining structured meeting management with real-time video conferencing (via Jitsi Meet).

### Current Features (Stage 1)

| Module | Features | Status |
|--------|----------|--------|
| **Dashboard** | Overview, quick actions, organization switcher | Active |
| **Governance (OrgMeet)** | Meetings, agendas, motions, voting, minutes | Active |
| **Membership** | Basic member tracking, contacts | Active |
| **Documents** | File storage, organization documents | Active |
| **Administration** | Organization settings, role management | Active |

### Governance Features

- **Meeting Management**: Schedule, run, and track meetings with full lifecycle support
- **Agenda Builder**: Create agendas with topics, motions, and elections
- **Motion Workflow**: Draft > Submitted > Screening > Discussion > Voting > Accepted/Rejected
- **Voting & Polls**: Electronic voting with multiple methods and quorum tracking
- **Video Conferencing**: Integrated HD video via Jitsi Meet
- **Meeting Minutes**: Auto-generate structured minutes with decisions and attendance
- **Speaker Queue**: Manage speaking order with points of order support

### Disabled in Stage 1

The following modules exist but are disabled by default for Stage 1:

- **Collaboration** (chat, real-time collaboration) - Stage 2
- **Dashboard Metrics** (analytics, reporting) - Stage 4
- **Finance** (contracts, revenue recognition, donations) - Stage 5
- **CRM** (leads, opportunities) - Stage 4

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for tests)

### Running Locally

1. **Clone the repository**
   ```bash
   git clone https://github.com/szubair22/fossys.git
   cd fossys/orgsuite
   ```

2. **Copy environment files**
   ```bash
   cp .env.fastapi.example .env.fastapi.dev
   # Edit .env.fastapi.dev with your settings
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose -f docker-compose.fastapi.yml up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:3000/api/docs

### Environment Configuration

Copy `.env.fastapi.example` and configure:

```env
# Required
SECRET_KEY=your-super-secret-key-change-in-production
POSTGRES_USER=orgmeet
POSTGRES_PASSWORD=orgmeet
POSTGRES_DB=orgmeet

# Optional - Video conferencing
JITSI_DOMAIN=meet.jit.si

# Optional - Email notifications
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_TLS=true
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
SMTP_SENDER=noreply@yourdomain.com
```

## Architecture

### Backend (FastAPI + PostgreSQL)

```
backend/
├── app/
│   ├── api/v1/          # API routes (governance, membership, finance, etc.)
│   ├── core/            # Config, security, permissions
│   ├── db/              # Database, migrations (Alembic)
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   └── services/        # Business logic
└── tests/               # pytest tests
```

### Frontend (Vanilla JS)

```
frontend/
├── js/
│   ├── config.js        # Environment config
│   ├── config.modules.js # Module flags (Stage 1/2/3/4/5)
│   ├── layout.js        # Header, navigation, apps menu
│   ├── api.js           # API client
│   ├── app.js           # Main application logic
│   └── ui.js            # UI utilities
├── css/                 # Styles (Tailwind + custom)
└── pages/               # HTML pages
```

### Module Configuration

Module visibility is controlled by `frontend/js/config.modules.js`:

```javascript
const DEPLOYMENT_STAGE = 1;

window.OrgSuiteModules = {
    dashboard: true,
    governance: true,
    documents: true,
    membership: true,
    collaboration: false,  // Stage 2
    dashboardMetrics: false, // Stage 4
    finance: false,         // Stage 5
    admin: true,
    crm: false              // Stage 4
};
```

## Running Tests

### Backend (pytest)
```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

### Frontend (Playwright E2E)
```bash
npm install
npx playwright test
```

## Deployment Configurations

| File | Use Case |
|------|----------|
| `docker-compose.fastapi.yml` | FastAPI + PostgreSQL (recommended) |
| `docker-compose.fastapi.prod.yml` | Production with SSL |

## Roadmap

See [../ROADMAP.md](../ROADMAP.md) for planned stages and features.

## License

MIT License - see [../LICENSE](../LICENSE)

---

**Stage 1 Status**: Governance module complete and production-ready.
