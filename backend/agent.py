import json
import os
import re
import sys

from dotenv import load_dotenv
from groq import Groq
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

load_dotenv()

MODEL = 'llama-3.3-70b-versatile'
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

ALIASES = {
    'MCP_get_availability_tool': 'check_doctor_availability_tool',
    'MCP_book_appointment_tool': 'book_appointment_tool',
    'MCP_doctor_summary_tool': 'doctor_summary_report_tool',
    'get_available_time_slots_tool': 'check_doctor_availability_tool',
}


def _clean(text: str) -> str:
    # remove leaked tool tags
    text = text or ''
    text = re.sub(r'<function\s*=\s*[^>]+>\{.*?\}</function>', '', text, flags=re.DOTALL)
    text = re.sub(r'<function\s*=\s*[^>]+\(\{.*?\}\)\s*></function>', '', text, flags=re.DOTALL)
    return text.strip()


def _norm(name: str, args: dict) -> tuple[str, dict]:
    # normalize tool names args
    name = ALIASES.get(name, name)
    if name == 'check_doctor_availability_tool':
        if 'doctor_name' not in args and 'doctor' in args:
            args['doctor_name'] = args.pop('doctor')
        if 'date' not in args and 'appointment_date' in args:
            args['date'] = args.pop('appointment_date')
        args.setdefault('time_range', 'all')
    if name == 'book_appointment_tool' and 'doctor_name' not in args and 'doctor' in args:
        args['doctor_name'] = args.pop('doctor')
    return name, args


def _fallback_calls(text: str) -> list[tuple[str, dict]]:
    # parse raw function markup
    calls = []
    for pat in [
        r'<function\s*=\s*([^>]+)>(\{.*?\})</function>',
        r'<function\s*=\s*([^(>\s]+)\((\{.*?\})\)\s*></function>',
    ]:
        for m in re.finditer(pat, text or '', re.DOTALL):
            try:
                args = json.loads(m.group(2).strip())
                calls.append(_norm(m.group(1).strip(), args))
            except Exception:
                pass
    return calls


async def get_mcp_response(messages: list) -> str:
    # run tools then reply
    server = StdioServerParameters(command=sys.executable, args=[os.path.join(os.path.dirname(__file__), 'mcp_server.py')])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            tools = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}} for t in listed.tools]

            first = client.chat.completions.create(model=MODEL, messages=messages, tools=tools, tool_choice='auto').choices[0].message

            if not first.tool_calls:
                calls = _fallback_calls(first.content or '')
                if not calls:
                    return _clean(first.content) or "I'm not sure how to help with that."
                outputs = []
                for name, args in calls:
                    r = await session.call_tool(name, args)
                    outputs.append('\n'.join(c.text for c in r.content if c.type == 'text'))
                final = client.chat.completions.create(
                    model=MODEL,
                    messages=messages + [{"role": "assistant", "content": 'Use these tool outputs:\n\n' + '\n\n'.join(outputs)}],
                ).choices[0].message.content
                return _clean(final) or '\n\n'.join(outputs)

            convo = messages + [{
                "role": "assistant",
                "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in first.tool_calls],
            }]

            outputs = []
            for tc in first.tool_calls:
                try:
                    name, args = _norm(tc.function.name, json.loads(tc.function.arguments))
                    r = await session.call_tool(name, args)
                    out = '\n'.join(c.text for c in r.content if c.type == 'text')
                except Exception as e:
                    out = f'Tool error: {e}'
                outputs.append(out)
                convo.append({"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": out})

            final = _clean(client.chat.completions.create(model=MODEL, messages=convo).choices[0].message.content)
            return final if final and final.lower() not in {'done', 'done.'} else ('\n\n'.join(outputs) or 'Done.')


async def call_mcp_tool(tool_name: str, args: dict | None = None) -> str:
    # call one mcp tool directly
    args = args or {}
    server = StdioServerParameters(command=sys.executable, args=[os.path.join(os.path.dirname(__file__), 'mcp_server.py')])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            if tool_name not in names:
                raise ValueError(f'Tool not found: {tool_name}')
            r = await session.call_tool(tool_name, args)
            return '\n'.join(c.text for c in r.content if c.type == 'text').strip()
