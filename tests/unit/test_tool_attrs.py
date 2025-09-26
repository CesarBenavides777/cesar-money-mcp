from fastmcp import FastMCP
import asyncio

mcp = FastMCP('test')

@mcp.tool
async def test_func():
    return 'test'

async def main():
    tools = await mcp.get_tools()
    tool = tools['test_func']
    
    print('Tool attributes:', [a for a in dir(tool) if not a.startswith('_')])
    
    # Check specific attributes
    if hasattr(tool, 'func'):
        print('Has func:', hasattr(tool, 'func'))
        print('func type:', type(tool.func))
        print('func callable:', callable(tool.func))
        
        # Try calling func
        try:
            result = await tool.func()
            print('tool.func() result:', result)
        except Exception as e:
            print('tool.func() error:', e)

asyncio.run(main())
