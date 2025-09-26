import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from fastmcp_server import mcp

async def test():
    tools = await mcp.get_tools()
    
    # Test get_transactions
    tool = tools['get_transactions']
    
    # Test with proper arguments
    try:
        result = await tool.run({
            "start_date": "2025-06-01",
            "end_date": "2025-08-31",
            "limit": 1000
        })
        print("Success! Result type:", type(result))
        if hasattr(result, 'content'):
            for content in result.content:
                if hasattr(content, 'text'):
                    print("Text:", content.text[:100], "...")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
