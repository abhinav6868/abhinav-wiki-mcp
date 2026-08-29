#!/usr/bin/env python3
"""
mcp_server.py — Formula 1 Tiered Knowledge Vault MCP Server
Parameterized by DATA_ROOT environment variable.

Exposes standard MCP Tools:
- list_pages(directory: str = "")
- read_page(path: str)
- search(query: str, limit: int = 10)

Supports both MCP JSON-RPC over SSE/HTTP (Claude Desktop, Cursor, MCP Clients)
and REST inspection endpoints.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse
import asyncio

# Resolve DATA_ROOT
DATA_ROOT_ENV = os.getenv("DATA_ROOT", "")
if DATA_ROOT_ENV:
    DATA_ROOT = Path(DATA_ROOT_ENV).resolve()
else:
    # Default to local vault directory
    DATA_ROOT = (Path(__file__).resolve().parent / "vault").resolve()

TIER_NAME = os.getenv("TIER_NAME", "Formula 1 Knowledge Vault Server")

print(f"🏎️  Starting MCP Server: {TIER_NAME}")
print(f"📁 DATA_ROOT configured to: {DATA_ROOT}")
if not DATA_ROOT.exists():
    print(f"⚠️ Warning: DATA_ROOT {DATA_ROOT} does not exist yet. Creating...")
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=f"F1 Knowledge Vault MCP — {TIER_NAME}",
    description="Karpathy-style tiered LLM knowledge wiki MCP server for Formula 1 history & telemetry.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═════════════════════════════════════════════════════════════════════
# 🛠️ CORE TOOL IMPLEMENTATIONS
# ═════════════════════════════════════════════════════════════════════

def list_pages_impl(directory: str = "") -> Dict[str, Any]:
    """List available markdown pages under DATA_ROOT."""
    target_dir = (DATA_ROOT / directory.strip("/\\")).resolve()
    
    # Path traversal check
    if not str(target_dir).startswith(str(DATA_ROOT)):
        return {"error": "Access denied: Path outside DATA_ROOT.", "pages": []}
    
    if not target_dir.exists():
        return {"error": f"Directory '{directory}' not found under DATA_ROOT.", "pages": []}

    pages = []
    for p in target_dir.rglob("*.md"):
        rel_path = p.relative_to(DATA_ROOT).as_posix()
        size_bytes = p.stat().st_size
        
        # Determine tier classification from path
        tier_label = "Unclassified"
        if "tier1" in rel_path:
            tier_label = "Tier 1 (Public Results, Bios & Standings)"
        elif "tier2" in rel_path:
            tier_label = "Tier 2 (Telemetry, Pit Strategy & Qualifying Gaps)"
        elif "tier3" in rel_path:
            tier_label = "Tier 3 (Derived Analysis & ML Models)"

        pages.append({
            "path": rel_path,
            "filename": p.name,
            "tier": tier_label,
            "size_bytes": size_bytes
        })

    # Sort deterministically
    pages.sort(key=lambda x: x["path"])

    return {
        "tier_scope": TIER_NAME,
        "data_root": str(DATA_ROOT.name),
        "total_pages": len(pages),
        "pages": pages
    }

def read_page_impl(path: str) -> Dict[str, Any]:
    """Return content of a specific page under DATA_ROOT."""
    clean_path = path.strip("/\\")
    if not clean_path.endswith(".md"):
        clean_path += ".md"
        
    target_file = (DATA_ROOT / clean_path).resolve()

    # Search fallback if exact relative path wasn't given
    if not target_file.exists():
        # Try finding by filename across subdirectories
        matches = list(DATA_ROOT.rglob(Path(clean_path).name))
        if matches:
            target_file = matches[0]

    # Path traversal security check
    if not str(target_file).startswith(str(DATA_ROOT)):
        return {"error": "Access denied: Path outside DATA_ROOT.", "path": path}

    if not target_file.exists() or not target_file.is_file():
        return {
            "error": f"Page '{path}' not found in this access tier.",
            "data_root_tier": TIER_NAME,
            "hint": "The requested entity may belong to a higher or different security tier physically absent from this bundle."
        }

    try:
        content = target_file.read_text(encoding="utf-8")
        rel_path = target_file.relative_to(DATA_ROOT).as_posix()
        return {
            "path": rel_path,
            "filename": target_file.name,
            "size_bytes": len(content),
            "content": content
        }
    except Exception as e:
        return {"error": f"Error reading page: {str(e)}"}

def search_impl(query: str, limit: int = 10) -> Dict[str, Any]:
    """Full-text keyword / BM25 search over all markdown documents in DATA_ROOT."""
    clean_q = query.strip().lower()
    tokens = [t for t in re.split(r'\W+', clean_q) if t]
    
    if not tokens:
        return {"query": query, "results_count": 0, "results": []}

    scored_results = []

    for p in DATA_ROOT.rglob("*.md"):
        try:
            content = p.read_text(encoding="utf-8")
            content_lower = content.lower()
            filename_lower = p.stem.lower()
            rel_path = p.relative_to(DATA_ROOT).as_posix()

            score = 0.0

            # 1. Exact match in filename / slug (highest priority)
            if clean_q in filename_lower:
                score += 50.0
            for t in tokens:
                if t in filename_lower:
                    score += 15.0

            # 2. Header match (# Title)
            first_line = content.splitlines()[0].lower() if content.splitlines() else ""
            if clean_q in first_line:
                score += 35.0
            for t in tokens:
                if t in first_line:
                    score += 10.0

            # 3. Content occurrences
            token_count = 0
            for t in tokens:
                cnt = content_lower.count(t)
                if cnt > 0:
                    token_count += 1
                    score += min(cnt * 2.0, 20.0)

            # Require at least one token match
            if score > 0:
                # Generate snippet
                snippet = ""
                pos = content_lower.find(tokens[0])
                if pos != -1:
                    start = max(0, pos - 80)
                    end = min(len(content), pos + 180)
                    snippet = content[start:end].replace("\n", " ").strip()
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(content):
                        snippet = snippet + "..."
                else:
                    snippet = content[:200].replace("\n", " ") + "..."

                scored_results.append({
                    "path": rel_path,
                    "filename": p.name,
                    "score": round(score, 2),
                    "snippet": snippet
                })
        except Exception:
            continue

    # Rank by score
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    top_results = scored_results[:limit]

    return {
        "query": query,
        "tier_scope": TIER_NAME,
        "results_count": len(top_results),
        "results": top_results
    }

# ═════════════════════════════════════════════════════════════════════
# 📋 MCP TOOLS MANIFEST
# ═════════════════════════════════════════════════════════════════════

TOOLS_MANIFEST = [
    {
        "name": "list_pages",
        "description": "List available Formula 1 knowledge pages under the active tier DATA_ROOT. Returns relative filepaths and security tiers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Optional subdirectory to filter (e.g. 'tier1/drivers', 'tier2/races', 'tier3/analysis', or '' for root)"
                }
            }
        }
    },
    {
        "name": "read_page",
        "description": "Read the complete Markdown contents of an entity dossier, race telemetry breakdown, or analysis report from the vault.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the markdown document (e.g. 'tier1/drivers/hamilton.md', 'tier1/races/2021-22.md', 'tier3/analysis/win_probability_model.md')"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "search",
        "description": "Perform full-text keyword search and BM25 index matching across all available documents in the active knowledge tier.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords, driver name, circuit, Grand Prix year/round, or analytical concept (e.g. 'Hamilton win rate', 'Monza 2020', 'undercut strategy')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of ranked results to return (default: 10)"
                }
            },
            "required": ["query"]
        }
    }
]

# ═════════════════════════════════════════════════════════════════════
# 🌐 FASTAPI HTTP & SSE ROUTES
# ═════════════════════════════════════════════════════════════════════

@app.get("/")
@app.get("/health")
def health():
    pages_count = len(list(DATA_ROOT.rglob("*.md")))
    return {
        "status": "healthy",
        "service": "Formula 1 Tiered Knowledge Vault MCP Server",
        "tier_name": TIER_NAME,
        "data_root": str(DATA_ROOT),
        "total_markdown_pages": pages_count,
        "tools_available": [t["name"] for t in TOOLS_MANIFEST]
    }

@app.get("/tools")
def get_tools():
    return {"tools": TOOLS_MANIFEST}

@app.post("/call")
async def call_tool_rest(request: Request):
    body = await request.json()
    name = body.get("name")
    args = body.get("arguments", {})

    if name == "list_pages":
        return list_pages_impl(args.get("directory", ""))
    elif name == "read_page":
        return read_page_impl(args.get("path", ""))
    elif name == "search":
        return search_impl(args.get("query", ""), args.get("limit", 10))
    else:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found.")

@app.post("/rpc")
async def handle_json_rpc(request: Request):
    """Handle standard JSON-RPC 2.0 MCP protocol requests."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None})

    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {},
                    "prompts": {}
                },
                "serverInfo": {
                    "name": f"f1-vault-{TIER_NAME.lower().replace(' ', '-')}",
                    "version": "1.0.0"
                }
            }
        })

    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS_MANIFEST}
        })

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if tool_name == "list_pages":
            res = list_pages_impl(tool_args.get("directory", ""))
        elif tool_name == "read_page":
            res = read_page_impl(tool_args.get("path", ""))
        elif tool_name == "search":
            res = search_impl(tool_args.get("query", ""), tool_args.get("limit", 10))
        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool '{tool_name}'"}
            })

        # Format output text block
        text_content = json.dumps(res, indent=2) if isinstance(res, dict) else str(res)
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": text_content
                    }
                ]
            }
        })

    return JSONResponse({
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method '{method}' not implemented."}
    })

# ── MCP SSE Transport Endpoints ──
@app.get("/sse")
async def handle_sse(request: Request):
    """Server-Sent Events endpoint for MCP protocol connection."""
    async def event_generator():
        # Initial endpoint event pointing to messages URI
        endpoint_data = "/messages"
        yield {"event": "endpoint", "data": endpoint_data}
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(15)
            yield {"event": "ping", "data": "keep-alive"}

    return EventSourceResponse(event_generator())

@app.post("/messages")
async def handle_messages(request: Request):
    """Handle message transport over SSE."""
    return await handle_json_rpc(request)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=port, reload=False)
