import json
import requests
import asyncio
from fastmcp_server import mcp as fastmcp_server

async def test_tools():
    """Test that we can call tools correctly"""
    tools = await fastmcp_server.get_tools()
    
    # Test get_transactions tool
    tool = tools['get_transactions']
    result = await tool.run({
        "start_date": "2025-06-01",
        "end_date": "2025-08-31",
        "limit": 1000
    })
    
    print("Tool result type:", type(result))
    print("Content:", result.content)
    if result.content:
        for content in result.content:
            if hasattr(content, 'text'):
                print("Text:", content.text[:200] if len(content.text) > 200 else content.text)

# Run the test
asyncio.run(test_tools())
