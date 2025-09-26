from fastmcp import FastMCP
import asyncio

mcp = FastMCP('test')

@mcp.tool
async def test_func():
    return 'test'

async def main():
    # Get the tools
    tools = await mcp.get_tools()
    print('Tools:', tools)
    print('Tools type:', type(tools))

    if tools:
        tool_name = list(tools.keys())[0]
        tool = tools[tool_name]
        print(f'Tool "{tool_name}" type:', type(tool))
        print('Tool callable?', callable(tool))

        # Try calling it directly
        try:
            result = await tool()
            print('Direct call result:', result)
        except Exception as e:
            print('Direct call error:', e)

# Run the async function
asyncio.run(main())
