import asyncio
from datetime import datetime
from fastmcp_server import mcp

async def test_date_serialization():
    print("Testing date serialization fix...")
    
    tools = await mcp.get_tools()
    
    # Test get_transactions with dates - this should not give serialization error
    print("\n=== Testing get_transactions with dates ===")
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
                    text = content.text
                    print("Response:", text[:100], "...")
                    # Check if it's still a serialization error
                    if "not JSON serializable" in text:
                        print("❌ Still has serialization error!")
                    elif "credentials not configured" in text:
                        print("✅ Serialization fixed - now getting credential error as expected")
                    elif "404" in text:
                        print("✅ Serialization fixed - now getting auth error as expected")
    except Exception as e:
        print(f"Unexpected error: {e}")

asyncio.run(test_date_serialization())
