"""
Finance module - Accounting and donations.

This module handles:
- Chart of Accounts
- Journal Entries (double-entry bookkeeping)
- Donations
- Contracts (ASC 606 - edition-gated)
- Revenue Recognition (ASC 606 - edition-gated)
- Invoices/Payments (future)
- Dimension tracking (future)
"""
from fastapi import APIRouter

from app.api.v1.finance.accounts import router as accounts_router
from app.api.v1.finance.journal import router as journal_router
from app.api.v1.finance.donations import router as donations_router
from app.api.v1.finance.contracts import router as contracts_router
from app.api.v1.finance.revenue_recognition import router as rev_rec_router

# Create the finance router for v1 API endpoints
finance_router = APIRouter(prefix="/finance", tags=["finance"])

# Include sub-routers
# Routes will be: /api/v1/finance/accounts, /api/v1/finance/journal-entries, /api/v1/finance/donations
finance_router.include_router(accounts_router)
finance_router.include_router(journal_router)
finance_router.include_router(donations_router)

# Edition-gated routers (require enable_contracts/enable_rev_rec in finance settings)
finance_router.include_router(contracts_router, prefix="/contracts", tags=["contracts"])
finance_router.include_router(rev_rec_router, prefix="/revenue-recognition", tags=["revenue-recognition"])

__all__ = [
    "finance_router",
]
