#!/usr/bin/env python3
"""
mcp_server.py — Formula 1 Knowledge Vault Multi-Tier MCP Server & Live Web Wiki
Features:
1. Live Interactive Web Wiki UI on browser requests (matching team screenshot).
2. Autonomous Chat & Note Logging with Real-Time Re-Indexing (save_chat_query, update_wiki_page, add_concept).
3. Multi-Tier Streamable HTTP MCP Server (/sse, /mcp1/sse, /mcp2/sse, /mcp3/sse).
4. Physical Tier Isolation & Boundary Enforcement (MCP 1 > MCP 2 > MCP 3).
5. Native RFC 8414 & RFC 7591 OAuth Auto-Registration for Claude Connectors.
"""

import os
import sys
import json
import re
import uuid
from datetime import datetime, timezone
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
    title="Formula 1 Knowledge Vault & Multi-Tier MCP Server",
    description="Interactive Live Wiki & Streamable HTTP MCP Server with physical tier isolation and real-time auto-indexing.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═════════════════════════════════════════════════════════════════════
# 🔄 REAL-TIME AUTO-INDEXING & LOGGING ENGINE
# ═════════════════════════════════════════════════════════════════════

def trigger_auto_reindex():
    """Dynamically refresh sub-indexes and master index in real time."""
    try:
        # Re-index Claude Chat Queries
        queries_dir = VAULT_FULL / "raw" / "claude-chat-queries"
        if queries_dir.exists():
            q_files = sorted(list(queries_dir.glob("*.md")), reverse=True)
            q_lines = [
                "# 💬 Claude Chat Queries & Research Threads Index",
                "",
                "Chronological archive of live Q&A threads and research conversations.",
                "",
                "| Thread Dossier | User | Date | Topic |",
                "| :--- | :--- | :--- | :--- |"
            ]
            for p in q_files:
                parts = p.stem.split("_")
                u = parts[0].title() if len(parts) > 0 else "User"
                d = parts[1] if len(parts) > 1 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
                t = parts[2].replace("-", " ").title() if len(parts) > 2 else p.stem.replace("_", " ").title()
                q_lines.append(f"| [[{p.stem}]] | **{u}** | `{d}` | {t} |")
            (VAULT_FULL / "queries-index.md").write_text("\n".join(q_lines) + "\n", encoding="utf-8")

        # Re-index Concepts
        concepts_dir = VAULT_FULL / "wiki" / "concepts"
        if concepts_dir.exists():
            c_files = sorted(list(concepts_dir.glob("*.md")))
            c_lines = [
                "# 🧠 Formula 1 Engineering, Aerodynamics & Strategy Concepts Index",
                "",
                "Master catalog of technical definitions, aerodynamic principles, and tactical frameworks.",
                "",
                "| Concept Page | Category | Summary |",
                "| :--- | :--- | :--- |"
            ]
            for p in c_files:
                c_lines.append(f"| [[{p.stem}]] | Technical Concept | {p.stem.replace('-', ' ').title()} |")
            (VAULT_FULL / "concepts-index.md").write_text("\n".join(c_lines) + "\n", encoding="utf-8")

        # Append to log.md
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        log_file = VAULT_FULL / "log.md"
        if log_file.exists():
            cur = log_file.read_text(encoding="utf-8")
            log_file.write_text(cur + f"\n- [{now_str}] Vault auto-indexed & synchronized.\n", encoding="utf-8")

        # Copy updated indexes to mcp1
        if (PROJECT_ROOT / "mcp1" / "vault").exists():
            for idx_name in ["queries-index.md", "concepts-index.md", "index.md", "log.md"]:
                src = VAULT_FULL / idx_name
                if src.exists():
                    (PROJECT_ROOT / "mcp1" / "vault" / idx_name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception as e:
        print(f"⚠️ Reindexing warning: {e}")

# ═════════════════════════════════════════════════════════════════════
# 🛠️ CORE MCP TOOL IMPLEMENTATIONS (READ & WRITE)
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

def execute_save_chat_query(user: str, topic: str, conversation_markdown: str) -> Dict[str, Any]:
    """Save a live Claude Q&A conversation thread directly to the vault and auto-index."""
    clean_user = re.sub(r'[^a-zA-Z0-9]', '', user.lower()) or "user"
    clean_topic = re.sub(r'[^a-zA-Z0-9\-_]', '-', topic.lower().strip()).strip("-") or "research-thread"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    thread_slug = f"{clean_user}_{date_str}_{clean_topic}"
    
    target_dir = VAULT_FULL / "raw" / "claude-chat-queries"
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / f"{thread_slug}.md"

    doc_content = f"""| thread_name | {thread_slug} |
| :--- | :--- |
| **user** | {clean_user} |
| **type** | claude-chat |
| **created** | {date_str} |
| **updated** | {date_str} |

# Thread: {topic.title()}

{conversation_markdown}

---
*Logged automatically via MCP Save Chat Integration on {date_str}.*
"""
    file_path.write_text(doc_content, encoding="utf-8")
    
    # Mirror to mcp1
    mcp1_target = PROJECT_ROOT / "mcp1" / "vault" / "raw" / "claude-chat-queries"
    if mcp1_target.parent.parent.exists():
        mcp1_target.mkdir(parents=True, exist_ok=True)
        (mcp1_target / f"{thread_slug}.md").write_text(doc_content, encoding="utf-8")

    trigger_auto_reindex()

    return {
        "status": "success",
        "saved_path": f"raw/claude-chat-queries/{thread_slug}.md",
        "thread_name": thread_slug,
        "message": f"Successfully logged conversation '{topic}' to vault and auto-updated all indexes."
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
        "name": "save_chat_query",
        "description": "Log and save a research conversation or Q&A thread into the vault's chat query archive with automatic real-time indexing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user": {"type": "string", "description": "Name of the user (e.g. 'Abhi', 'Ayan', 'Danish')"},
                "topic": {"type": "string", "description": "Short summary title of the conversation topic"},
                "conversation_markdown": {"type": "string", "description": "Complete formatted Markdown conversation thread"}
            },
            "required": ["user", "topic", "conversation_markdown"]
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
# 🌐 WEB WIKI VIEWER API & HTML UI
# ═════════════════════════════════════════════════════════════════════

@app.get("/api/tree")
def get_tree():
    """Return file tree JSON for the web explorer."""
    def build_tree(current_path: Path):
        items = []
        if not current_path.exists():
            return items
        for p in sorted(current_path.iterdir()):
            if p.name.startswith("."):
                continue
            if p.is_dir():
                items.append({
                    "name": p.name,
                    "path": p.relative_to(VAULT_FULL).as_posix(),
                    "type": "dir",
                    "children": build_tree(p)
                })
            elif p.suffix == ".md":
                items.append({
                    "name": p.name,
                    "path": p.relative_to(VAULT_FULL).as_posix(),
                    "type": "file",
                    "size": p.stat().st_size
                })
        return items

    return {"root": "vault", "tree": build_tree(VAULT_FULL)}

@app.get("/api/file")
def get_file(path: str):
    return execute_read_page(VAULT_FULL, "Master Tier", path)

@app.post("/api/save_chat")
async def api_save_chat(request: Request):
    body = await request.json()
    return execute_save_chat_query(
        user=body.get("user", "User"),
        topic=body.get("topic", "Research Thread"),
        conversation_markdown=body.get("conversation", "")
    )

WIKI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Formula 1 Knowledge Wiki</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-main: #0d1117;
            --bg-sidebar: #010409;
            --bg-header: #161b22;
            --border-color: #30363d;
            --text-main: #e6edf3;
            --text-muted: #8b949e;
            --link-color: #58a6ff;
            --accent-blue: #1f6feb;
            --highlight-bg: #161b22;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        #sidebar {
            width: 330px;
            background-color: var(--bg-sidebar);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }
        .sidebar-header {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 14px;
            font-weight: 600;
        }
        .search-box {
            padding: 10px 16px;
            border-bottom: 1px solid var(--border-color);
        }
        .search-box input {
            width: 100%;
            background: #0d1117;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 6px 10px;
            color: var(--text-main);
            font-size: 13px;
        }
        .search-box input:focus { outline: none; border-color: var(--link-color); }
        .file-tree {
            flex: 1;
            overflow-y: auto;
            padding: 10px 8px;
            font-size: 13px;
        }
        .tree-node {
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--text-main);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .tree-node:hover { background-color: #161b22; }
        .tree-node.active { background-color: #1f6feb33; color: var(--link-color); font-weight: 500; }
        .tree-children { padding-left: 14px; }
        .tree-children.collapsed { display: none; }
        #main {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background-color: var(--bg-main);
        }
        .content-header {
            background-color: var(--bg-header);
            border-bottom: 1px solid var(--border-color);
            padding: 8px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 13px;
        }
        .breadcrumbs {
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--text-muted);
            font-family: monospace;
        }
        .breadcrumbs span.current-file { color: var(--text-main); font-weight: 600; }
        .header-actions { display: flex; align-items: center; gap: 8px; }
        .tab-btn {
            background: none;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
        }
        .tab-btn.active { background-color: #21262d; border-color: #8b949e; }
        .btn-primary {
            background: #238636;
            border: 1px solid rgba(240,246,252,0.1);
            color: #fff;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            font-weight: 500;
        }
        .btn-primary:hover { background: #2ea043; }
        .content-body {
            flex: 1;
            overflow-y: auto;
            padding: 32px 48px;
        }
        .markdown-body {
            max-width: 960px;
            margin: 0 auto;
            line-height: 1.6;
        }
        .markdown-body h1 { font-size: 24px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color); }
        .markdown-body h2 { font-size: 18px; margin-top: 24px; margin-bottom: 12px; }
        .markdown-body table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }
        .markdown-body th, .markdown-body td { border: 1px solid var(--border-color); padding: 8px 12px; text-align: left; }
        .markdown-body th { background-color: #161b22; }
        .markdown-body a { color: var(--link-color); text-decoration: none; }
        .markdown-body a:hover { text-decoration: underline; }
        .markdown-body blockquote { border-left: 4px solid #1f6feb; padding: 6px 16px; background-color: #161b22; color: #8b949e; margin: 16px 0; border-radius: 4px; }
        .code-view {
            max-width: 960px;
            margin: 0 auto;
            background: #010409;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 16px;
            font-family: monospace;
            font-size: 13px;
            white-space: pre-wrap;
            display: none;
        }
        /* Modal for New Chat Thread */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0,0,0,0.7);
            align-items: center; justify-content: center;
            z-index: 1000;
        }
        .modal.open { display: flex; }
        .modal-card {
            background: #161b22;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            width: 540px;
            padding: 20px;
        }
        .modal-card h3 { font-size: 16px; margin-bottom: 12px; }
        .modal-card input, .modal-card textarea {
            width: 100%;
            background: #0d1117;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px;
            color: #e6edf3;
            font-size: 13px;
            margin-bottom: 10px;
            font-family: inherit;
        }
        .modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
    </style>
</head>
<body>
    <div id="sidebar">
        <div class="sidebar-header">
            <span><i class="fa-solid fa-flag-checkered" style="color:#e10600; margin-right:6px;"></i> Formula 1 Wiki</span>
            <button class="btn-primary" onclick="openModal()"><i class="fa-solid fa-plus"></i> Log Chat</button>
        </div>
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Search pages, drivers, concepts..." oninput="filterTree()">
        </div>
        <div class="file-tree" id="treeContainer">
            <div style="color:var(--text-muted); padding:10px;">Loading vault...</div>
        </div>
    </div>

    <div id="main">
        <div class="content-header">
            <div class="breadcrumbs" id="breadcrumbBar">
                <i class="fa-solid fa-folder-open"></i> <span>vault</span> / <span class="current-file" id="currentFileName">index.md</span>
            </div>
            <div class="header-actions">
                <span class="file-meta-badge" id="fileMetaBadge">Markdown Document</span>
                <button class="tab-btn active" id="tabPreview" onclick="setTab('preview')"><i class="fa-regular fa-eye"></i> Preview</button>
                <button class="tab-btn" id="tabCode" onclick="setTab('code')"><i class="fa-solid fa-code"></i> Code</button>
            </div>
        </div>
        <div class="content-body">
            <div class="markdown-body" id="previewArea">Select a document from the left to view.</div>
            <pre class="code-view" id="codeArea"></pre>
        </div>
    </div>

    <div class="modal" id="chatModal">
        <div class="modal-card">
            <h3>💬 Log Live Research / Chat Thread</h3>
            <input type="text" id="chatUser" placeholder="Your Name (e.g. Abhi, Ayan)">
            <input type="text" id="chatTopic" placeholder="Topic (e.g. 2021 Title Battle Deep Dive)">
            <textarea id="chatConversation" rows="8" placeholder="Paste conversation markdown or notes here..."></textarea>
            <div class="modal-actions">
                <button class="tab-btn" onclick="closeModal()">Cancel</button>
                <button class="btn-primary" onclick="saveChat()">Save & Auto-Index</button>
            </div>
        </div>
    </div>

    <script>
        let currentFilePath = "index.md";
        let fullTreeData = [];

        async function loadTree() {
            try {
                const res = await fetch('/api/tree');
                const data = await res.json();
                fullTreeData = data.tree;
                renderTree(fullTreeData, document.getElementById('treeContainer'));
                loadFile(currentFilePath);
            } catch (e) {
                console.error("Tree load error:", e);
            }
        }

        function renderTree(items, container) {
            container.innerHTML = "";
            items.forEach(item => {
                const div = document.createElement('div');
                if (item.type === 'dir') {
                    const node = document.createElement('div');
                    node.className = 'tree-node';
                    node.innerHTML = `<i class="fa-solid fa-chevron-down" style="font-size:10px; width:12px;"></i> <i class="fa-solid fa-folder" style="color:#8b949e;"></i> <span>${item.name}</span>`;
                    const childrenDiv = document.createElement('div');
                    childrenDiv.className = 'tree-children';
                    renderTree(item.children, childrenDiv);
                    node.onclick = () => {
                        const icon = node.querySelector('.fa-chevron-down, .fa-chevron-right');
                        childrenDiv.classList.toggle('collapsed');
                        if (childrenDiv.classList.contains('collapsed')) {
                            icon.className = 'fa-solid fa-chevron-right';
                        } else {
                            icon.className = 'fa-solid fa-chevron-down';
                        }
                    };
                    div.appendChild(node);
                    div.appendChild(childrenDiv);
                } else {
                    const node = document.createElement('div');
                    node.className = 'tree-node';
                    node.innerHTML = `<i class="fa-regular fa-file-lines" style="color:#58a6ff;"></i> <span>${item.name}</span>`;
                    node.onclick = () => {
                        document.querySelectorAll('.tree-node').forEach(n => n.classList.remove('active'));
                        node.classList.add('active');
                        loadFile(item.path);
                    };
                    div.appendChild(node);
                }
                container.appendChild(div);
            });
        }

        async function loadFile(path) {
            currentFilePath = path;
            document.getElementById('currentFileName').innerText = path.split('/').pop();
            try {
                const res = await fetch(`/api/file?path=${encodeURIComponent(path)}`);
                const data = await res.json();
                if (data.found || data.content) {
                    const raw = data.content;
                    document.getElementById('codeArea').innerText = raw;
                    
                    // Parse Wikilinks [[PageName]] -> <a href="#" onclick="loadFile('PageName')">
                    let parsedHtml = marked.parse(raw);
                    parsedHtml = parsedHtml.replace(/\\[\\[([a-zA-Z0-9_\\-\\s]+)\\]\\]/g, (match, p1) => {
                        return `<a href="javascript:void(0)" onclick="loadFile('${p1.trim()}')" style="color:#58a6ff; font-weight:500;">[[${p1.trim()}]]</a>`;
                    });
                    document.getElementById('previewArea').innerHTML = parsedHtml;
                    document.getElementById('fileMetaBadge').innerText = `${data.size_bytes} bytes · ${path}`;
                } else {
                    document.getElementById('previewArea').innerHTML = `<div style="color:#f85149;">Error: ${data.error}</div>`;
                }
            } catch (e) {
                console.error("File load error:", e);
            }
        }

        function setTab(tab) {
            if (tab === 'preview') {
                document.getElementById('tabPreview').classList.add('active');
                document.getElementById('tabCode').classList.remove('active');
                document.getElementById('previewArea').style.display = 'block';
                document.getElementById('codeArea').style.display = 'none';
            } else {
                document.getElementById('tabCode').classList.add('active');
                document.getElementById('tabPreview').classList.remove('active');
                document.getElementById('previewArea').style.display = 'none';
                document.getElementById('codeArea').style.display = 'block';
            }
        }

        function openModal() { document.getElementById('chatModal').classList.add('open'); }
        function closeModal() { document.getElementById('chatModal').classList.remove('open'); }

        async function saveChat() {
            const user = document.getElementById('chatUser').value;
            const topic = document.getElementById('chatTopic').value;
            const conversation = document.getElementById('chatConversation').value;
            if (!topic || !conversation) { alert("Please enter a topic and conversation."); return; }

            const res = await fetch('/api/save_chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user, topic, conversation })
            });
            const result = await res.json();
            closeModal();
            loadTree();
            loadFile(result.saved_path);
        }

        function filterTree() {
            const query = document.getElementById('searchInput').value.toLowerCase();
            document.querySelectorAll('.tree-node').forEach(node => {
                const text = node.innerText.toLowerCase();
                node.style.display = (!query || text.includes(query)) ? 'flex' : 'none';
            });
        }

        loadTree();
    </script>
</body>
</html>
"""

# ═════════════════════════════════════════════════════════════════════
# 🌐 ROUTER BUILDER FOR TIERED MCP
# ═════════════════════════════════════════════════════════════════════

def create_tier_router(data_root: Path, tier_name: str, prefix: str = ""):
    router = APIRouter(prefix=prefix)

    @router.get("/")
    @router.get("/health")
    def health(request: Request):
        # If requested by browser HTML, show the Web Wiki UI
        accept = request.headers.get("accept", "")
        if "text/html" in accept and prefix == "":
            return HTMLResponse(WIKI_HTML)
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
        elif name == "save_chat_query":
            return execute_save_chat_query(args.get("user", "User"), args.get("topic", "Research Thread"), args.get("conversation_markdown", ""))
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
                    "serverInfo": {"name": f"f1-vault-{tier_name.lower().replace(' ', '-')}", "version": "3.0.0"}
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
            elif tool_name == "save_chat_query":
                res = execute_save_chat_query(tool_args.get("user", "User"), tool_args.get("topic", "Research Thread"), tool_args.get("conversation_markdown", ""))
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

@app.get("/wiki", response_class=HTMLResponse)
def wiki_page():
    return HTMLResponse(WIKI_HTML)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Launching Formula 1 Knowledge Vault & MCP Server on port {port}")
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=port, reload=False)
