from typing import Any
import httpx
import os
import asyncpg
from dotenv import load_dotenv
import logging
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import gradio as gr

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("NLTOSQL")

# --- Database connection ---
async def connect(db_name: str) -> asyncpg.Connection:
    try:
        conn = await asyncpg.connect(
            database=db_name,
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASS", "your_password"),
            host=os.getenv("PG_HOST", "localhost"),
            port=os.getenv("PG_PORT", "5432")
        )
        logger.info(f"Connected to database: {db_name}")
        return conn
    except Exception as e:
        logger.error(f"Connection error: {e}")
        raise

@mcp.tool(name="list_databases", description="List all PostgreSQL databases")
async def list_databases() -> str:
    try:
        conn = await connect("postgres")
        rows = await conn.fetch("SELECT datname FROM pg_database WHERE datistemplate = false;")
        await conn.close()
        return "\n".join(row["datname"] for row in rows) if rows else "No databases found."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool(name="list_tables", description="List all public tables in a PostgreSQL database")
async def list_tables(db_name: str) -> str:
    try:
        conn = await connect(db_name)
        rows = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        await conn.close()
        return "\n".join(row["table_name"] for row in rows) if rows else f"No tables in '{db_name}'."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool(name="table_schema", description="Get column names and types of a table")
async def table_schema(db_name: str, table: str) -> str:
    try:
        conn = await connect(db_name)
        rows = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=$1;", table)
        await conn.close()
        return "\n".join(f"{r['column_name']}: {r['data_type']}" for r in rows) if rows else f"No schema for '{table}'."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool(name="view_table", description="Show first 10 rows of a table")
async def view_table(db_name: str, table: str) -> str:
    try:
        conn = await connect(db_name)
        rows = await conn.fetch(f'SELECT * FROM "{table}" LIMIT 10;')
        await conn.close()
        if not rows:
            return f"No rows found in '{table}'."
        return "\n".join(str(dict(row)) for row in rows)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool(name="execute_query", description="Execute custom SQL query")
async def execute_query(db_name: str, query: str) -> str:
    try:
        conn = await connect(db_name)
        if query.strip().upper().startswith(("SELECT", "WITH", "SHOW")):
            rows = await conn.fetch(query)
            await conn.close()
            return "\n".join(str(dict(r)) for r in rows) if rows else "No results."
        else:
            status = await conn.execute(query)
            await conn.close()
            return f"Query executed successfully: {status}"
    except Exception as e:
        return f"Error executing query: {str(e)}"

@mcp.tool(name="hello_postgres", description="Test connection to the server")
async def hello_postgres(name: str = "World") -> str:
    return f"Hello from the Postgres Explorer, {name}!"

# --- SSE handler setup ---
def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        try:
            async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
                await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())
        except Exception as e:
            logger.error(f"SSE Error: {e}")
            raise

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

# Create app instance
mcp_server = mcp._mcp_server
starlette_app = create_starlette_app(mcp_server, debug=True)

# --- Gradio UI for Hugging Face ---
def info_ui():
    return "✅ MCP PostgreSQL Server is running.\nSSE Endpoint: `/sse`\nYou can connect from your client or browser."

with gr.Blocks() as app:
    gr.Markdown("# 🧠 PostgreSQL MCP Server (via Gradio)")
    gr.Markdown("### SSE Endpoint: `/sse`")
    btn = gr.Button("Check Server Status")
    output = gr.Textbox(label="Server Info")
    btn.click(fn=info_ui, outputs=output)

app = gr.mount_gradio_app(starlette_app, app, path="/")
