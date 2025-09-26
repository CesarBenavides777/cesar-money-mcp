#!/usr/bin/env python3
"""Test MCP functionality directly"""
import json
import sys
import os
import asyncio
import io

# Add parent directory to path
sys.path.append(os.path.dirname(__file__))

# Import FastMCP server
from fastmcp_server import mcp as fastmcp_server

async def test_mcp_logic():
    """Test the core MCP logic"""
    
    print("1. Testing tools list...")
    tools = await fastmcp_server.get_tools()
    print(f"   Found {len(tools)} tools: {list(tools.keys())}")
    
    print("\n2. Testing get_transactions tool...")
    if 'get_transactions' in tools:
        tool = tools['get_transactions']
        result = await tool.run({
            "start_date": "2025-06-01",
            "end_date": "2025-08-31",
            "limit": 10
        })
        
        # Extract text from result
        text = ""
        if result.content:
            for content in result.content:
                if hasattr(content, 'text'):
                    text += content.text
        
        print(f"   Result: {text[:200]}...")
    
    print("\n3. Testing get_accounts tool...")
    if 'get_accounts' in tools:
        tool = tools['get_accounts']
        result = await tool.run({})
        
        # Extract text from result
        text = ""
        if result.content:
            for content in result.content:
                if hasattr(content, 'text'):
                    text += content.text
        
        print(f"   Result: {text[:200]}...")

# Run the test
asyncio.run(test_mcp_logic())
