# Fossys - Open Source Apps for Small Organizations

This monorepo contains open-source applications for nonprofits, fraternities/sororities, and service-based companies.

## Applications

| App | Description | Status |
|-----|-------------|--------|
| [**OrgSuite**](./orgsuite/) | Governance, membership, and finance platform | Active |

## Repository Structure

```
fossys/
├── orgsuite/           # OrgSuite application
│   ├── backend/        # FastAPI + PostgreSQL
│   ├── frontend/       # Vanilla JS frontend
│   ├── tests/          # Playwright E2E tests
│   └── ...
├── README.md           # This file
├── ROADMAP.md          # Overall roadmap
└── LICENSE             # MIT License
```

## Quick Start

Each application has its own README with setup instructions:

- **OrgSuite**: See [orgsuite/README.md](./orgsuite/README.md)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE)
