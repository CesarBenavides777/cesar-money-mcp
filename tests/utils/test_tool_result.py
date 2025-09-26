from fastmcp import FastMCP
import asyncio

mcp = FastMCP('test')

@mcp.tool
async def test_func(message: str = "hello"):
    return f'Response: {message}'

async def main():
    tools = await mcp.get_tools()
    tool = tools['test_func']
    
    # Run the tool
    result = await tool.run({"message": "test message"})
    print('Result type:', type(result))
    print('Result attributes:', [a for a in dir(result) if not a.startswith('_')])
    
    # Check common attributes
    if hasattr(result, 'content'):
        print('Result content:', result.content)
    if hasattr(result, 'result'):
        print('Result result:', result.result)
    if hasattr(result, 'value'):
        print('Result value:', result.value)
    if hasattr(result, 'data'):
        print('Result data:', result.data)
    
    # Try converting to string
    print('Result as string:', str(result))

asyncio.run(main())
