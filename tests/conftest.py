"""
Pytest configuration and shared fixtures for Monarch Money MCP tests
"""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, Mock
from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_monarch_client():
    """Mock MonarchMoney client for testing without real API calls"""
    client = AsyncMock()

    # Mock successful login
    client.login = AsyncMock()

    # Mock accounts response
    client.get_accounts = AsyncMock(return_value={
        "accounts": [
            {
                "id": "test_account_1",
                "displayName": "Test Checking",
                "currentBalance": 1500.00,
                "type": {"display": "Checking"},
                "institution": {"name": "Test Bank"}
            },
            {
                "id": "test_account_2",
                "displayName": "Test Savings",
                "currentBalance": 5000.00,
                "type": {"display": "Savings"},
                "institution": {"name": "Test Bank"}
            }
        ]
    })

    # Mock transactions response
    client.get_transactions = AsyncMock(return_value={
        "allTransactions": {
            "results": [
                {
                    "id": "tx1",
                    "date": "2025-09-26",
                    "amount": -50.00,
                    "merchant": {"name": "Test Store"},
                    "category": {"name": "Groceries"},
                    "account": {"displayName": "Test Checking"}
                },
                {
                    "id": "tx2",
                    "date": "2025-09-25",
                    "amount": 2000.00,
                    "merchant": {"name": "Test Employer"},
                    "category": {"name": "Income"},
                    "account": {"displayName": "Test Checking"}
                }
            ]
        }
    })

    # Mock budgets response
    client.get_budgets = AsyncMock(return_value=[
        {"name": "Monthly Budget", "id": "budget1"}
    ])

    # Mock spending plan response
    client.get_spending_plan = AsyncMock(return_value={
        "categories": [
            {"name": "Groceries", "budgeted": 400, "spent": 350}
        ]
    })

    # Mock account history response
    client.get_account_history = AsyncMock(return_value={
        "history": [
            {"date": "2025-09-26", "balance": 1500.00},
            {"date": "2025-09-25", "balance": 1450.00}
        ]
    })

    return client


@pytest.fixture
def test_credentials():
    """Test credentials for authentication tests"""
    return {
        "email": "test@example.com",
        "password": "test_password",
        "mfa_secret": "TEST_MFA_SECRET_KEY"
    }


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing"""
    return {
        "start_date": "2025-06-01",
        "end_date": "2025-09-26",
        "limit": 100,
        "expected_transactions": [
            {
                "date": "2025-09-26",
                "amount": -50.00,
                "merchant": "Test Store",
                "category": "Groceries"
            },
            {
                "date": "2025-09-25",
                "amount": 2000.00,
                "merchant": "Test Employer",
                "category": "Income"
            }
        ]
    }


@pytest.fixture
def environment_credentials():
    """Get credentials from environment variables if available"""
    return {
        "email": os.getenv("MONARCH_EMAIL"),
        "password": os.getenv("MONARCH_PASSWORD"),
        "mfa_secret": os.getenv("MONARCH_MFA_SECRET")
    }


@pytest.fixture
def has_real_credentials(environment_credentials):
    """Check if real credentials are available for integration tests"""
    return all([
        environment_credentials["email"],
        environment_credentials["password"]
    ])