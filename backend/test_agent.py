import asyncio
from agent import get_mcp_response

async def test():
    # quick agent smoke test
    print("Testing MCP Agent...")
    messages = [{"role": "user", "content": "Book an appointment with Dr. Ahuja tomorrow morning."}]
    response = await get_mcp_response(messages)
    print("Agent Response:", response)

if __name__ == "__main__":
    asyncio.run(test())
