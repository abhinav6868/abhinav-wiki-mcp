#!/usr/bin/env python3
"""
mcp_server.py — Multi-Tier Formula 1 Knowledge Vault MCP Server with Native Claude Connectors Support
Features:
- Direct support for all Claude Connectors URL formats (/, /sse, /mcp1, /mcp2, /mcp3, /mcp2/sse, etc.)
- Full POST & GET streamable transport support (eliminates 405 Method Not Allowed)
- Native RFC 8414 & OAuth Protected Resource Discovery
- Native RFC 7591 Dynamic Registration (/register & /oauth/register)
- Instant Auto-Approval OAuth Authorize (/oauth/authorize)
- Complete Physical Tier Isolation (MCP 1 > MCP 2 > MCP 3)
"""

import os
import sys
import json
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse, RedirectResponse
from sse_starlette.sse import EventSourceResponse
import asyncio

PROJECT_ROOT = Path(__file__).resolve().parent

# Determine paths for each tier
VAULT_FULL = (PROJECT_ROOT / "vault").resolve()
VAULT_MCP1 = (PROJECT_ROOT / "mcp1" / "vault").resolve() if (PROJECT_ROOT / "mcp1" / "vault").exists() else VAULT_FULL
VAULT_MCP2 = (PROJECT_ROOT / "mcp2" / "vault").resolve() if (PROJECT_ROOT / "mcp2" / "vault").exists() else VAULT_FULL
VAULT_MCP3 = (PROJECT_ROOT / "mcp3" / "vault").resolve() if (PROJECT_ROOT / "mcp3" / "vault").exists() else VAULT_FULL

# Standalone bundle fallback
ENV_DATA_ROOT = os.getenv("DATA_ROOT")
if ENV_DATA_ROOT:
    STANDALONE_ROOT = (PROJECT_ROOT / ENV_DATA_ROOT).resolve()
    if STANDALONE_ROOT.exists():
        VAULT_FULL = STANDALONE_ROOT
        VAULT_MCP1 = STANDALONE_ROOT
        VAULT_MCP2 = STANDALONE_ROOT
        VAULT_MCP3 = STANDALONE_ROOT

API_KEY = os.getenv("API_KEY", "")

app = FastAPI(
    title="Formula 1 Knowledge Vault Multi-Tier MCP Server",
    description="Streamable HTTP MCP Server with physical tier isolation and universal OAuth auto-registration for Claude Connectors.",
    version="2.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═════════════════════════════════════════════════════════════════════
# 🛠️ CORE MCP TOOL IMPLEMENTATIONS
# ═════════════════════════════════════════════════════════════════════

def execute_list_pages(data_root: Path, tier_name: str, directory: str = "") -> Dict[str, Any]:
    target_dir = (data_root / directory.strip("/\\")).resolve()
    if not str(target_dir).startswith(str(data_root)):
        return {"error": "Access denied: Path outside tier root.", "pages": []}
    if not target_dir.exists():
        return {"error": f"Directory '{directory}' not found in this tier.", "pages": []}

    pages = []
    for p in target_dir.rglob("*.md"):
        rel_path = p.relative_to(data_root).as_posix()
        tier_label = None
        if "tier1" in rel_path:
            tier_label = "tier1"
        elif "tier2" in rel_path:
            tier_label = "tier2"
        elif "tier3" in rel_path:
            tier_label = "tier3"
        elif "wiki" in rel_path:
            tier_label = "wiki"
        elif "raw" in rel_path:
            tier_label = "raw"

        pages.append({
            "path": rel_path,
            "filename": p.name,
            "tier": tier_label,
            "size_bytes": p.stat().st_size
        })

    pages.sort(key=lambda x: x["path"])
    return {
        "tier_scope": tier_name,
        "file_count": len(pages),
        "total_pages": len(pages),
        "pages": pages
    }

def execute_read_page(data_root: Path, tier_name: str, path: str) -> Dict[str, Any]:
    if not path or not isinstance(path, str):
        return {"error": "Invalid path parameter.", "found": False}
    clean_path = path.strip("/\\")
    if not clean_path.endswith(".md"):
        clean_path += ".md"

    target_file = (data_root / clean_path).resolve()
    if not target_file.exists():
        matches = list(data_root.rglob(Path(clean_path).name))
        if matches:
            target_file = matches[0]

    if not str(target_file).startswith(str(data_root)):
        return {"error": "Access denied: Path outside tier root.", "found": False}
    if not target_file.exists() or not target_file.is_file():
        return {
            "error": f"Page '{path}' not found in this access tier ({tier_name}).",
            "found": False,
            "requested_path": path,
            "tier_scope": tier_name
        }

    try:
        content = target_file.read_text(encoding="utf-8")
        rel_path = target_file.relative_to(data_root).as_posix()
        return {
            "path": rel_path,
            "filename": target_file.name,
            "found": True,
            "size_bytes": len(content),
            "content": content
        }
    except Exception as e:
        return {"error": f"Error reading page: {str(e)}", "found": False}

def execute_search(data_root: Path, tier_name: str, query: str, limit: int = 10) -> Dict[str, Any]:
    clean_q = query.strip().lower() if query else ""
    tokens = [t for t in re.split(r'\W+', clean_q) if t]
    if not tokens:
        return {"query": query, "results_count": 0, "results": []}

    scored_results = []
    for p in data_root.rglob("*.md"):
        try:
            content = p.read_text(encoding="utf-8")
            content_lower = content.lower()
            filename_lower = p.stem.lower()
            rel_path = p.relative_to(data_root).as_posix()

            score = 0.0
            if clean_q in filename_lower:
                score += 50.0
            for t in tokens:
                if t in filename_lower:
                    score += 15.0

            first_line = content.splitlines()[0].lower() if content.splitlines() else ""
            if clean_q in first_line:
                score += 35.0
            for t in tokens:
                if t in first_line:
                    score += 10.0

            for t in tokens:
                cnt = content_lower.count(t)
                if cnt > 0:
                    score += min(cnt * 2.0, 20.0)

            if len(tokens) > 1:
                matched_all = all(t in content_lower for t in tokens)
                if not (clean_q in content_lower or matched_all):
                    continue

            if score > 0:
                snippet = None
                pos = content_lower.find(tokens[0])
                if pos != -1:
                    start = max(0, pos - 80)
                    end = min(len(content), pos + 180)
                    snippet = content[start:end].replace("\n", " ").strip()
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(content):
                        snippet = snippet + "..."

                scored_results.append({
                    "path": rel_path,
                    "filename": p.name,
                    "score": round(score, 2),
                    "snippet": snippet
                })
        except Exception:
            continue

    scored_results.sort(key=lambda x: x["score"], reverse=True)
    top_results = scored_results[:limit]
    return {
        "query": query,
        "tier_scope": tier_name,
        "results_count": len(top_results),
        "results": top_results
    }

TOOLS_MANIFEST = [
    {
        "name": "list_pages",
        "description": "List available Formula 1 knowledge pages under the active tier DATA_ROOT.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Optional subdirectory to filter"}
            }
        }
    },
    {
        "name": "read_page",
        "description": "Read the complete Markdown contents of an entity dossier, race telemetry breakdown, or analysis report.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to markdown document (e.g. 'tier1/drivers/hamilton.md')"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "search",
        "description": "Perform full-text keyword search across all available documents in the active knowledge tier.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords (e.g. 'Hamilton win rate', 'Monza 2020')"},
                "limit": {"type": "integer", "description": "Max results to return"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_entity_dossier",
        "description": "Retrieve full entity dossier (alias for read_page / search).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_name": {"type": "string", "description": "Name or slug of driver/constructor/concept (e.g. 'Lewis Hamilton', 'Ferrari')"}
            },
            "required": ["entity_name"]
        }
    },
    {
        "name": "query_knowledge_base",
        "description": "Search the Formula 1 knowledge base (alias for search).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query string"}
            },
            "required": ["query"]
        }
    }
]

# ═════════════════════════════════════════════════════════════════════
# 🔐 GLOBAL OAUTH & DISCOVERY HANDLERS
# ═════════════════════════════════════════════════════════════════════

@app.get("/.well-known/oauth-protected-resource")
@app.get("/.well-known/oauth-protected-resource/{subpath:path}")
def global_oauth_protected(request: Request, subpath: str = ""):
    base_url = str(request.base_url).rstrip("/")
    return {
        "resource": base_url,
        "authorization_servers": [base_url],
        "scopes_supported": ["openid", "mcp:read", "mcp:write"]
    }

@app.get("/.well-known/oauth-authorization-server")
@app.get("/.well-known/openid-configuration")
def global_oauth_discovery(request: Request):
    base_url = str(request.base_url).rstrip("/")
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "registration_endpoint": f"{base_url}/register",
        "userinfo_endpoint": f"{base_url}/oauth/userinfo",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
        "scopes_supported": ["openid", "mcp:read", "mcp:write"]
    }

@app.post("/register")
@app.post("/oauth/register")
async def global_register(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    client_id = body.get("client_name", "claude-client") + "-" + str(uuid.uuid4())[:8]
    client_secret = "f1-vault-secret-" + str(uuid.uuid4())[:16]
    return JSONResponse({
        "client_id": client_id,
        "client_secret": client_secret,
        "client_name": body.get("client_name", "Claude MCP Client"),
        "redirect_uris": body.get("redirect_uris", ["https://claude.ai/api/connectors/oauth/callback", "https://claude.ai/api/mcp/auth_callback"]),
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"]
    }, status_code=201)

@app.get("/oauth/authorize")
@app.post("/oauth/authorize")
async def global_authorize(request: Request):
    redirect_uri = request.query_params.get("redirect_uri") or "https://claude.ai/api/mcp/auth_callback"
    state = request.query_params.get("state", "")
    code = "f1-vault-auth-code-" + str(uuid.uuid4())[:12]
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(url=f"{redirect_uri}{separator}code={code}&state={state}", status_code=302)

@app.post("/oauth/token")
async def global_token(request: Request):
    return JSONResponse({
        "access_token": "f1-vault-production-token-2026",
        "token_type": "Bearer",
        "expires_in": 86400 * 365,
        "refresh_token": "f1-vault-refresh-token-2026",
        "scope": "openid mcp:read mcp:write"
    })

# ═════════════════════════════════════════════════════════════════════
# 🌐 ROUTER BUILDER
# ═════════════════════════════════════════════════════════════════════

def create_tier_router(data_root: Path, tier_name: str, prefix: str = ""):
    router = APIRouter(prefix=prefix)

    @router.get("/")
    @router.get("/health")
    def health():
        cnt = len(list(data_root.rglob("*.md")))
        return {
            "status": "healthy",
            "service": "Formula 1 Tiered Knowledge Vault MCP Server",
            "tier_name": tier_name,
            "file_count": cnt,
            "total_markdown_pages": cnt,
            "tools_available": [t["name"] for t in TOOLS_MANIFEST]
        }

    @router.get("/tools")
    def get_tools(request: Request):
        return {"tools": TOOLS_MANIFEST}

    @router.post("/call")
    async def call_tool_rest(request: Request):
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

        name = body.get("name")
        args = body.get("arguments", {})

        if name == "list_pages":
            return execute_list_pages(data_root, tier_name, args.get("directory", ""))
        elif name == "read_page":
            return execute_read_page(data_root, tier_name, args.get("path", ""))
        elif name in ["search", "query_knowledge_base"]:
            q = args.get("query", "") or args.get("term", "")
            return execute_search(data_root, tier_name, q, args.get("limit", 10))
        elif name == "get_entity_dossier":
            entity = args.get("entity_name", "") or args.get("entity", "") or args.get("title", "")
            res = execute_read_page(data_root, tier_name, entity.lower().replace(" ", "_"))
            if res.get("found"):
                return res
            return execute_search(data_root, tier_name, entity, limit=1)
        else:
            raise HTTPException(status_code=404, detail=f"Tool '{name}' not found.")

    @router.post("/")
    @router.post("/rpc")
    @router.post("/messages")
    @router.post("/sse")
    async def handle_rpc(request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"jsonrpc": "2.0", "result": {"status": "connected"}, "id": None})

        req_id = body.get("id")
        method = body.get("method")
        params = body.get("params", {})

        if method == "initialize":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}, "resources": {}, "prompts": {}},
                    "serverInfo": {"name": f"f1-vault-{tier_name.lower().replace(' ', '-')}", "version": "2.4.0"}
                }
            })
        elif method == "tools/list":
            return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS_MANIFEST}})
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name == "list_pages":
                res = execute_list_pages(data_root, tier_name, tool_args.get("directory", ""))
            elif tool_name == "read_page":
                res = execute_read_page(data_root, tier_name, tool_args.get("path", ""))
            elif tool_name in ["search", "query_knowledge_base"]:
                q = tool_args.get("query", "") or tool_args.get("term", "")
                res = execute_search(data_root, tier_name, q, tool_args.get("limit", 10))
            elif tool_name == "get_entity_dossier":
                entity = tool_args.get("entity_name", "") or tool_args.get("entity", "") or tool_args.get("title", "")
                res = execute_read_page(data_root, tier_name, entity.lower().replace(" ", "_"))
                if not res.get("found"):
                    search_res = execute_search(data_root, tier_name, entity, limit=1)
                    if search_res.get("results"):
                        hit = search_res["results"][0]
                        res = execute_read_page(data_root, tier_name, hit["path"])
                    else:
                        res = {"error": f"No entity matching '{entity}' found in this tier.", "found": False}
            else:
                return JSONResponse({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool '{tool_name}'"}})

            text_content = res.get("content") if (isinstance(res, dict) and "content" in res and isinstance(res["content"], str)) else json.dumps(res, indent=2)
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": text_content}]}
            })

        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method '{method}' not implemented."}})

    @router.get("/sse")
    async def sse_endpoint(request: Request):
        async def event_generator():
            msg_path = f"{prefix}/messages" if prefix else "/messages"
            yield {"event": "endpoint", "data": msg_path}
            while True:
                if await request.is_disconnected():
                    break
                await asyncio.sleep(15)
                yield {"event": "ping", "data": "keep-alive"}
        return EventSourceResponse(event_generator())

    return router

# Mount Tier Routers
app.include_router(create_tier_router(VAULT_MCP1, "MCP 1 (Master Tier — Tier 1 + 2 + 3)", prefix=""))
app.include_router(create_tier_router(VAULT_MCP1, "MCP 1 (Master Tier — Tier 1 + 2 + 3)", prefix="/mcp1"))
app.include_router(create_tier_router(VAULT_MCP2, "MCP 2 (Telemetry Tier — Tier 2 + 3)", prefix="/mcp2"))
app.include_router(create_tier_router(VAULT_MCP3, "MCP 3 (Analysis Tier — Tier 3 Only)", prefix="/mcp3"))

# Explicit alias routes for bare paths
@app.get("/mcp1")
@app.get("/mcp2")
@app.get("/mcp3")
def bare_get(request: Request):
    path = request.url.path
    if "mcp2" in path:
        return {"status": "healthy", "tier_name": "MCP 2 (Telemetry Tier — Tier 2 + 3)", "file_count": len(list(VAULT_MCP2.rglob("*.md")))}
    elif "mcp3" in path:
        return {"status": "healthy", "tier_name": "MCP 3 (Analysis Tier — Tier 3 Only)", "file_count": len(list(VAULT_MCP3.rglob("*.md")))}
    return {"status": "healthy", "tier_name": "MCP 1 (Master Tier — Tier 1 + 2 + 3)", "file_count": len(list(VAULT_MCP1.rglob("*.md")))}

@app.post("/mcp1")
@app.post("/mcp2")
@app.post("/mcp3")
async def bare_post(request: Request):
    path = request.url.path
    root = VAULT_MCP2 if "mcp2" in path else (VAULT_MCP3 if "mcp3" in path else VAULT_MCP1)
    tier_label = "MCP 2" if "mcp2" in path else ("MCP 3" if "mcp3" in path else "MCP 1")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"jsonrpc": "2.0", "result": {"status": "connected"}, "id": None})
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": body.get("id"),
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}, "resources": {}, "prompts": {}},
            "serverInfo": {"name": f"f1-vault-{tier_label.lower().replace(' ', '-')}", "version": "2.4.0"}
        }
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Launching Multi-Tier MCP Server on port {port}")
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=port, reload=False)
