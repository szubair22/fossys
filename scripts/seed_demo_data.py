#!/usr/bin/env python3
"""
Demo Data Seeding Script for OrgSuite Revenue Recognition.

Creates a nonprofit organization with:
- Multi-line sponsorship contract (12-month, 3 performance obligations)
- Annual membership contract (single line, straight-line recognition)
- Pre-generated revenue schedules
- Revenue recognition runs with posted journal entries

Usage:
    python scripts/seed_demo_data.py

Requires:
    - Backend running at http://localhost:8000
    - Valid admin user credentials
"""
import asyncio
import httpx
from datetime import date, timedelta
from decimal import Decimal
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
DEMO_USER_EMAIL = "demo@fossys.com"
DEMO_USER_PASSWORD = "Demo123!"


async def get_auth_token(client: httpx.AsyncClient) -> str:
    """Authenticate and return JWT token."""
    print("Authenticating...")
    response = await client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PASSWORD}
    )
    if response.status_code != 200:
        print(f"Auth failed: {response.text}")
        sys.exit(1)

    data = response.json()
    print(f"Authenticated as {data['user']['email']}")
    return data["token"]


async def get_or_create_nonprofit_org(client: httpx.AsyncClient, headers: dict) -> str:
    """Get or create a nonprofit organization with rev rec enabled."""
    print("\nLooking for nonprofit organization...")

    # List organizations
    response = await client.get(f"{BASE_URL}/api/v1/organizations", headers=headers)
    orgs = response.json().get("items", [])

    # Find one with nonprofit edition
    for org in orgs:
        org_id = org["id"]
        # Check edition
        settings_response = await client.get(
            f"{BASE_URL}/api/v1/admin/org-settings/effective",
            params={"organization_id": org_id, "scope": "finance"},
            headers=headers
        )
        if settings_response.status_code == 200:
            settings = settings_response.json().get("settings", {}).get("finance", {})
            if settings.get("edition") == "nonprofit":
                print(f"Found nonprofit org: {org['name']} ({org_id})")
                return org_id

    # Create new nonprofit org if none found
    print("Creating nonprofit organization...")
    response = await client.post(
        f"{BASE_URL}/api/v1/organizations",
        headers=headers,
        json={
            "name": "Demo Nonprofit Foundation",
            "description": "Demo organization for revenue recognition features",
            "type": "nonprofit"
        }
    )

    if response.status_code not in (200, 201):
        print(f"Failed to create org: {response.text}")
        sys.exit(1)

    org_id = response.json()["id"]
    print(f"Created org: {org_id}")

    # Set to nonprofit edition
    await client.put(
        f"{BASE_URL}/api/v1/admin/org-settings",
        headers=headers,
        params={"organization_id": org_id},
        json={
            "scope": "finance",
            "settings": {
                "edition": "nonprofit",
                "accounting_basis": "accrual",
                "enable_rev_rec": True,
                "enable_contracts": True,
                "enable_donations": True,
                "enable_restrictions": True
            }
        }
    )
    print("Set organization to Nonprofit edition with rev rec enabled")

    return org_id


async def ensure_chart_of_accounts(client: httpx.AsyncClient, headers: dict, org_id: str) -> dict:
    """Ensure basic chart of accounts exists and return account IDs."""
    print("\nSetting up chart of accounts...")

    # Check existing accounts
    response = await client.get(
        f"{BASE_URL}/api/v1/finance/accounts",
        params={"organization_id": org_id},
        headers=headers
    )
    accounts = response.json().get("items", [])

    account_map = {}
    for acc in accounts:
        account_map[acc["code"]] = acc["id"]

    # Required accounts
    required = [
        {"code": "4100", "name": "Sponsorship Revenue", "account_type": "revenue"},
        {"code": "4200", "name": "Membership Revenue", "account_type": "revenue"},
        {"code": "4300", "name": "Program Revenue", "account_type": "revenue"},
        {"code": "2500", "name": "Deferred Revenue", "account_type": "liability"},
    ]

    for acc_data in required:
        if acc_data["code"] not in account_map:
            response = await client.post(
                f"{BASE_URL}/api/v1/finance/accounts",
                headers=headers,
                json={
                    "organization_id": org_id,
                    **acc_data
                }
            )
            if response.status_code in (200, 201):
                account_map[acc_data["code"]] = response.json()["id"]
                print(f"  Created account: {acc_data['code']} - {acc_data['name']}")
            else:
                print(f"  Failed to create {acc_data['code']}: {response.text}")

    return account_map


async def create_sponsorship_contract(
    client: httpx.AsyncClient,
    headers: dict,
    org_id: str,
    accounts: dict
) -> str:
    """Create a multi-line sponsorship contract."""
    print("\nCreating multi-line sponsorship contract...")

    today = date.today()
    start_date = today.replace(day=1)  # First of current month
    end_date = (start_date + timedelta(days=365)).replace(day=1) - timedelta(days=1)  # ~12 months

    contract_data = {
        "organization_id": org_id,
        "name": "2025 Annual Sponsorship - TechCorp Inc.",
        "description": "Multi-year sponsorship agreement including naming rights, promotional materials, and event access",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_transaction_price": 50000.00,
        "currency": "USD",
        "notes": "Demo contract for ASC 606 revenue recognition showcase",
        "lines": [
            {
                "description": "Event Naming Rights - Annual Conference",
                "recognition_pattern": "straight_line",
                "product_type": "service",
                "quantity": 1,
                "unit_price": 25000.00,
                "ssp_amount": 28000.00,  # SSP differs from unit price
                "revenue_account_id": accounts.get("4100"),
                "deferred_revenue_account_id": accounts.get("2500")
            },
            {
                "description": "Promotional Materials Package",
                "recognition_pattern": "point_in_time",
                "product_type": "service",
                "quantity": 1,
                "unit_price": 15000.00,
                "ssp_amount": 15000.00,
                "revenue_account_id": accounts.get("4100"),
                "deferred_revenue_account_id": accounts.get("2500")
            },
            {
                "description": "VIP Event Access (12 passes)",
                "recognition_pattern": "straight_line",
                "product_type": "service",
                "quantity": 12,
                "unit_price": 833.33,
                "ssp_amount": 12000.00,
                "revenue_account_id": accounts.get("4100"),
                "deferred_revenue_account_id": accounts.get("2500")
            }
        ]
    }

    response = await client.post(
        f"{BASE_URL}/api/v1/finance/contracts",
        headers=headers,
        json=contract_data
    )

    if response.status_code not in (200, 201):
        print(f"Failed to create sponsorship contract: {response.text}")
        return None

    contract = response.json()
    print(f"  Created contract: {contract['name']} ({contract['id']})")
    print(f"  Total value: ${contract['total_transaction_price']:,.2f}")
    print(f"  Lines: {len(contract.get('lines', []))}")

    return contract["id"]


async def create_membership_contract(
    client: httpx.AsyncClient,
    headers: dict,
    org_id: str,
    accounts: dict
) -> str:
    """Create a single-line membership contract."""
    print("\nCreating membership contract...")

    today = date.today()
    start_date = today.replace(day=1)
    end_date = (start_date + timedelta(days=365)).replace(day=1) - timedelta(days=1)

    contract_data = {
        "organization_id": org_id,
        "name": "Corporate Membership - Acme Industries",
        "description": "Annual corporate membership with full benefits",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_transaction_price": 12000.00,
        "currency": "USD",
        "lines": [
            {
                "description": "Annual Corporate Membership",
                "recognition_pattern": "straight_line",
                "product_type": "subscription",
                "quantity": 1,
                "unit_price": 12000.00,
                "ssp_amount": 12000.00,
                "revenue_account_id": accounts.get("4200"),
                "deferred_revenue_account_id": accounts.get("2500")
            }
        ]
    }

    response = await client.post(
        f"{BASE_URL}/api/v1/finance/contracts",
        headers=headers,
        json=contract_data
    )

    if response.status_code not in (200, 201):
        print(f"Failed to create membership contract: {response.text}")
        return None

    contract = response.json()
    print(f"  Created contract: {contract['name']} ({contract['id']})")

    return contract["id"]


async def activate_contract(
    client: httpx.AsyncClient,
    headers: dict,
    org_id: str,
    contract_id: str
) -> bool:
    """Activate a contract and generate revenue schedules."""
    print(f"\nActivating contract {contract_id}...")

    response = await client.post(
        f"{BASE_URL}/api/v1/finance/contracts/{contract_id}/activate",
        params={"organization_id": org_id},
        headers=headers,
        json={"generate_schedules": True}
    )

    if response.status_code != 200:
        print(f"  Failed to activate: {response.text}")
        return False

    result = response.json()
    print(f"  {result.get('message', 'Activated')}")
    print(f"  Schedules created: {result.get('schedules_created', 0)}")
    print(f"  Total allocated: ${float(result.get('total_allocated', 0)):,.2f}")

    return True


async def run_revenue_recognition(
    client: httpx.AsyncClient,
    headers: dict,
    org_id: str
) -> dict:
    """Run revenue recognition for due schedule lines."""
    print("\nRunning revenue recognition...")

    # First preview
    today = date.today()
    as_of_date = today.isoformat()

    response = await client.post(
        f"{BASE_URL}/api/v1/finance/revenue-recognition/run",
        headers=headers,
        json={
            "organization_id": org_id,
            "as_of_date": as_of_date,
            "dry_run": True
        }
    )

    if response.status_code != 200:
        print(f"  Preview failed: {response.text}")
        return None

    preview = response.json()
    print(f"  Preview: {preview.get('lines_processed', 0)} lines, ${float(preview.get('total_amount', 0)):,.2f}")

    if preview.get("lines_processed", 0) == 0:
        print("  No lines due for recognition")
        return preview

    # Now post
    response = await client.post(
        f"{BASE_URL}/api/v1/finance/revenue-recognition/run",
        headers=headers,
        json={
            "organization_id": org_id,
            "as_of_date": as_of_date,
            "dry_run": False
        }
    )

    if response.status_code != 200:
        print(f"  Post failed: {response.text}")
        return None

    result = response.json()
    print(f"  Posted: {result.get('lines_posted', 0)} lines")
    print(f"  Journal entries: {result.get('journal_entries_created', 0)}")
    print(f"  Total recognized: ${float(result.get('total_amount', 0)):,.2f}")

    return result


async def print_summary(
    client: httpx.AsyncClient,
    headers: dict,
    org_id: str
):
    """Print summary of created data."""
    print("\n" + "="*60)
    print("DEMO DATA SUMMARY")
    print("="*60)

    # Contracts
    response = await client.get(
        f"{BASE_URL}/api/v1/finance/contracts",
        params={"organization_id": org_id},
        headers=headers
    )
    contracts = response.json().get("items", [])

    print(f"\nContracts: {len(contracts)}")
    for c in contracts:
        status_badge = f"[{c['status'].upper()}]"
        print(f"  {status_badge:12} {c['name']}")
        print(f"             ${float(c['total_transaction_price']):,.2f} | Lines: {c.get('lines_count', 0)}")

    # Schedules
    response = await client.get(
        f"{BASE_URL}/api/v1/finance/revenue-recognition/schedules",
        params={"organization_id": org_id},
        headers=headers
    )
    schedules = response.json().get("items", [])

    print(f"\nRevenue Schedules: {len(schedules)}")
    total_deferred = sum(float(s.get("deferred_amount", 0)) for s in schedules)
    total_recognized = sum(float(s.get("recognized_amount", 0)) for s in schedules)

    print(f"  Total Deferred:   ${total_deferred:,.2f}")
    print(f"  Total Recognized: ${total_recognized:,.2f}")

    # Waterfall
    today = date.today()
    from_date = today.replace(day=1).isoformat()
    to_date = (today.replace(day=1) + timedelta(days=365)).isoformat()

    response = await client.get(
        f"{BASE_URL}/api/v1/finance/revenue-recognition/waterfall",
        params={
            "organization_id": org_id,
            "from_date": from_date,
            "to_date": to_date
        },
        headers=headers
    )

    if response.status_code == 200:
        waterfall = response.json()
        print(f"\nWaterfall ({from_date} to {to_date}):")
        print(f"  Total Planned:  ${float(waterfall.get('total_planned', 0)):,.2f}")
        print(f"  Total Posted:   ${float(waterfall.get('total_posted', 0)):,.2f}")
        print(f"  Total Deferred: ${float(waterfall.get('total_deferred', 0)):,.2f}")

    print("\n" + "="*60)
    print("Demo data seeding complete!")
    print("="*60)


async def main():
    """Main seeding function."""
    print("="*60)
    print("OrgSuite Revenue Recognition Demo Data Seeder")
    print("="*60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Authenticate
        token = await get_auth_token(client)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Get/create nonprofit org
        org_id = await get_or_create_nonprofit_org(client, headers)

        # Setup accounts
        accounts = await ensure_chart_of_accounts(client, headers, org_id)

        # Create sponsorship contract
        sponsorship_id = await create_sponsorship_contract(client, headers, org_id, accounts)
        if sponsorship_id:
            await activate_contract(client, headers, org_id, sponsorship_id)

        # Create membership contract
        membership_id = await create_membership_contract(client, headers, org_id, accounts)
        if membership_id:
            await activate_contract(client, headers, org_id, membership_id)

        # Run revenue recognition
        await run_revenue_recognition(client, headers, org_id)

        # Print summary
        await print_summary(client, headers, org_id)


if __name__ == "__main__":
    asyncio.run(main())
