from fastmcp import FastMCP
import asyncio

mcp = FastMCP('test')

@mcp.tool
async def test_func():
    return 'test'

# Check the tool structure
tool = mcp.tools['test_func']
print('Tool type:', type(tool))
print('Tool callable?', callable(tool))
print('Tool attributes:', [a for a in dir(tool) if not a.startswith('_')])

# Try calling it
loop = asyncio.new_event_loop()
try:
    result = loop.run_until_complete(tool())
    print('Direct call result:', result)
except Exception as e:
    print('Direct call error:', e)
    # Try with func attribute
    try:
        result = loop.run_until_complete(tool.func())
        print('tool.func() result:', result)
    except Exception as e2:
        print('tool.func() error:', e2)
finally:
    loop.close()
