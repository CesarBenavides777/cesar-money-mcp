from fastmcp import FastMCP
import asyncio

mcp = FastMCP('test')

@mcp.tool
async def test_func(message: str = "hello"):
    return f'Response: {message}'

async def main():
    tools = await mcp.get_tools()
    tool = tools['test_func']
    
    # Try the run method
    try:
        result = await tool.run(message="test message")
        print('tool.run() result:', result)
    except Exception as e:
        print('tool.run() error:', e)

asyncio.run(main())
