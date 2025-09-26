from fastmcp import FastMCP
import asyncio
import inspect

mcp = FastMCP('test')

@mcp.tool
async def test_func(message: str = "hello"):
    return f'Response: {message}'

async def main():
    tools = await mcp.get_tools()
    tool = tools['test_func']
    
    # Check run method signature
    print('run method signature:', inspect.signature(tool.run))
    
    # Try the run method with positional dict
    try:
        result = await tool.run({"message": "test message"})
        print('tool.run(dict) result:', result)
    except Exception as e:
        print('tool.run(dict) error:', e)

asyncio.run(main())
