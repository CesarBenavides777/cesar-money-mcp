"""
Integration tests for MCP endpoint functionality
"""

import pytest
import json
import asyncio
from unittest.mock import patch, AsyncMock
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestMCPIntegration:
    """Test MCP JSON-RPC endpoint integration"""

    @pytest.mark.asyncio
    async def test_mcp_tools_list(self):
        """Test MCP tools/list endpoint"""
        # This would typically be tested with a test server
        # For now, test the underlying functionality
        from fastmcp_server import mcp

        tools = await mcp.get_tools()
        tools_list = []

        for tool_name, tool in tools.items():
            # Simulate MCP tools/list response format
            tool_def = {
                "name": tool_name,
                "description": tool.__doc__ or f"{tool_name} tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            tools_list.append(tool_def)

        # Should have 5 tools
        assert len(tools_list) == 5

        # Check tool names
        tool_names = [t["name"] for t in tools_list]
        expected_tools = [
            'get_accounts',
            'get_transactions',
            'get_budgets',
            'get_spending_plan',
            'get_account_history'
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_mcp_tool_call_format(self, mock_monarch_client):
        """Test MCP tools/call response format"""
        from fastmcp_server import mcp

        with patch('fastmcp_server.get_monarch_client', return_value=mock_monarch_client):
            tools = await mcp.get_tools()

            # Simulate calling get_accounts
            result = await tools['get_accounts'].run({})

            # Check that result can be converted to MCP format
            mcp_response = {
                "content": [
                    {
                        "type": "text",
                        "text": result.content[0].text
                    }
                ]
            }

            assert "content" in mcp_response
            assert len(mcp_response["content"]) > 0
            assert mcp_response["content"][0]["type"] == "text"
            assert len(mcp_response["content"][0]["text"]) > 0

    @pytest.mark.asyncio
    async def test_mcp_error_handling(self):
        """Test MCP error response format"""
        from fastmcp_server import mcp

        with patch('fastmcp_server.get_monarch_client', side_effect=Exception("Test error")):
            tools = await mcp.get_tools()
            result = await tools['get_accounts'].run({})

            # Error should be contained in the text response
            text_content = result.content[0].text
            assert "Error fetching accounts" in text_content
            assert "Test error" in text_content

    @pytest.mark.asyncio
    async def test_date_parameter_handling(self, mock_monarch_client):
        """Test that date parameters are properly handled"""
        from fastmcp_server import mcp

        with patch('fastmcp_server.get_monarch_client', return_value=mock_monarch_client):
            tools = await mcp.get_tools()

            # Test with valid dates
            result = await tools['get_transactions'].run({
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "limit": 50
            })

            # Should not contain serialization errors
            text_content = result.content[0].text
            assert "JSON serializable" not in text_content
            assert "Test Store" in text_content or "No transactions found" in text_content

    @pytest.mark.asyncio
    async def test_parameter_validation(self, mock_monarch_client):
        """Test parameter validation and error messages"""
        from fastmcp_server import mcp

        with patch('fastmcp_server.get_monarch_client', return_value=mock_monarch_client):
            tools = await mcp.get_tools()

            # Test invalid date format
            result = await tools['get_transactions'].run({
                "start_date": "not-a-date",
                "end_date": "2025-12-31"
            })

            text_content = result.content[0].text
            assert "Invalid" in text_content or "format" in text_content

    @pytest.mark.skipif(
        not os.getenv("MONARCH_EMAIL") or not os.getenv("MONARCH_PASSWORD"),
        reason="Real credentials not available"
    )
    @pytest.mark.asyncio
    async def test_real_authentication(self):
        """Test with real Monarch Money credentials (when available)"""
        from fastmcp_server import mcp

        tools = await mcp.get_tools()

        # Test get_accounts with real credentials
        result = await tools['get_accounts'].run({})
        text_content = result.content[0].text

        # Should either succeed or give a specific error (not generic)
        assert "Error fetching accounts" in text_content or "Found" in text_content

        # Should not have generic "not configured" error if credentials are set
        if os.getenv("MONARCH_EMAIL") and os.getenv("MONARCH_PASSWORD"):
            assert "not configured" not in text_content