"""
Unit tests for FastMCP tools without external dependencies
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastmcp.tools.tool import ToolResult
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestFastMCPTools:
    """Test FastMCP tool functionality"""

    @pytest.mark.asyncio
    async def test_fastmcp_tool_structure(self):
        """Test that FastMCP tools are properly structured"""
        from fastmcp_server import mcp

        tools = await mcp.get_tools()

        # Check that all expected tools exist
        expected_tools = [
            'get_accounts',
            'get_transactions',
            'get_budgets',
            'get_spending_plan',
            'get_account_history'
        ]

        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool {tool_name} not found in tools"

        # Check tool types
        for tool_name, tool in tools.items():
            assert hasattr(tool, 'run'), f"Tool {tool_name} missing run method"
            assert callable(tool.run), f"Tool {tool_name}.run is not callable"

    @pytest.mark.asyncio
    async def test_tool_run_returns_tool_result(self, mock_monarch_client):
        """Test that tools return proper ToolResult objects"""
        from fastmcp_server import mcp

        with patch('fastmcp_server.get_monarch_client', return_value=mock_monarch_client):
            tools = await mcp.get_tools()

            # Test get_accounts
            result = await tools['get_accounts'].run({})
            assert isinstance(result, ToolResult)
            assert hasattr(result, 'content')
            assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_get_accounts_structure(self, mock_monarch_client):
        """Test get_accounts tool output structure"""
        from fastmcp_server import mcp

        with patch('fastmcp_server.get_monarch_client', return_value=mock_monarch_client):
            tools = await mcp.get_tools()
            result = await tools['get_accounts'].run({})

            # Check result structure
            assert hasattr(result, 'content')
            text_content = result.content[0].text

            # Should contain account information
            assert "Test Checking" in text_content
            assert "Test Savings" in text_content
            assert "$1,500.00" in text_content
            assert "$5,000.00" in text_content

    @pytest.mark.asyncio
    async def test_get_transactions_with_dates(self, mock_monarch_client):
        """Test get_transactions with date parameters"""
        from fastmcp_server import mcp

        with patch('fastmcp_server.get_monarch_client', return_value=mock_monarch_client):
            tools = await mcp.get_tools()
            result = await tools['get_transactions'].run({
                "start_date": "2025-06-01",
                "end_date": "2025-09-26",
                "limit": 10
            })

            text_content = result.content[0].text

            # Should contain transaction information
            assert "Test Store" in text_content
            assert "Test Employer" in text_content
            assert "Groceries" in text_content

    @pytest.mark.asyncio
    async def test_invalid_date_format(self, mock_monarch_client):
        """Test get_transactions with invalid date format"""
        from fastmcp_server import mcp

        with patch('fastmcp_server.get_monarch_client', return_value=mock_monarch_client):
            tools = await mcp.get_tools()
            result = await tools['get_transactions'].run({
                "start_date": "invalid-date",
                "end_date": "2025-09-26",
                "limit": 10
            })

            text_content = result.content[0].text
            assert "Invalid start_date format" in text_content

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self):
        """Test how tools handle authentication errors"""
        from fastmcp_server import mcp

        # Mock authentication failure
        with patch('fastmcp_server.get_monarch_client', side_effect=ValueError("Authentication failed")):
            tools = await mcp.get_tools()
            result = await tools['get_accounts'].run({})

            text_content = result.content[0].text
            assert "Error fetching accounts" in text_content
            assert "Authentication failed" in text_content