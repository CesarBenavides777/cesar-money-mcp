import asyncio
import os
from dotenv import load_dotenv
from fastmcp_server import mcp

load_dotenv()

async def test():
    print("Testing enhanced logging...")
    
    tools = await mcp.get_tools()
    
    # Test get_accounts
    print("\n=== Testing get_accounts ===")
    tool = tools['get_accounts']
    try:
        result = await tool.run({})
        print("Result type:", type(result))
        if hasattr(result, 'content'):
            for content in result.content:
                if hasattr(content, 'text'):
                    print("Response:", content.text[:200], "...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test get_transactions with dates
    print("\n=== Testing get_transactions ===")
    tool = tools['get_transactions']
    try:
        result = await tool.run({
            "start_date": "2025-06-26",
            "end_date": "2025-09-26",
            "limit": 5
        })
        print("Result type:", type(result))
        if hasattr(result, 'content'):
            for content in result.content:
                if hasattr(content, 'text'):
                    print("Response:", content.text[:200], "...")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
