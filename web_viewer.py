#!/usr/bin/env python3
"""
web_viewer.py — Interactive Dark-Mode Wiki Explorer
Matches the exact UI layout from the user screenshot:
- Left file tree navigation with search & collapsible folders
- Breadcrumb bar with Preview / Code / Blame tabs
- Metadata tables & rich typography
- Live search & wikilink navigation
"""

import os
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent
VAULT_DIR = PROJECT_ROOT / "vault"

app = FastAPI(title="Formula 1 Knowledge Wiki Explorer")

@app.get("/api/tree")
def get_tree():
    """Return nested file tree of the vault."""
    def build_tree(current_path: Path):
        items = []
        for p in sorted(current_path.iterdir()):
            if p.name.startswith("."):
                continue
            if p.is_dir():
                items.append({
                    "name": p.name,
                    "path": p.relative_to(VAULT_DIR).as_posix(),
                    "type": "dir",
                    "children": build_tree(p)
                })
            elif p.suffix == ".md":
                items.append({
                    "name": p.name,
                    "path": p.relative_to(VAULT_DIR).as_posix(),
                    "type": "file",
                    "size": p.stat().st_size
                })
        return items

    return {"root": "vault", "tree": build_tree(VAULT_DIR)}

@app.get("/api/file")
def get_file(path: str):
    clean_path = path.strip("/\\")
    target = (VAULT_DIR / clean_path).resolve()
    
    if not target.exists() or not target.is_file():
        # Try finding by filename
        matches = list(VAULT_DIR.rglob(Path(clean_path).name))
        if matches:
            target = matches[0]
        else:
            return JSONResponse({"error": f"File '{path}' not found."}, status_code=404)

    content = target.read_text(encoding="utf-8")
    lines = content.splitlines()

    return {
        "path": target.relative_to(VAULT_DIR).as_posix(),
        "filename": target.name,
        "size_bytes": len(content),
        "lines_count": len(lines),
        "content": content
    }

@app.get("/", response_class=HTMLResponse)
def index_page():
    return """<!DOCTYPE html>
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

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Sidebar */
        #sidebar {
            width: 320px;
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

        .search-box input:focus {
            outline: none;
            border-color: var(--link-color);
        }

        .file-tree {
            flex: 1;
            overflow-y: auto;
            padding: 10px 8px;
            font-size: 13px;
        }

        .tree-node {
            user-select: none;
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

        .tree-node:hover {
            background-color: #161b22;
        }

        .tree-node.active {
            background-color: #1f6feb33;
            color: var(--link-color);
            font-weight: 500;
        }

        .tree-children {
            padding-left: 16px;
            display: block;
        }

        .tree-children.collapsed {
            display: none;
        }

        /* Main Content */
        #main {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background-color: var(--bg-main);
        }

        /* Breadcrumb / Action Header */
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

        .breadcrumbs span.current-file {
            color: var(--text-main);
            font-weight: 600;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .tab-btn {
            background: none;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
        }

        .tab-btn.active {
            background-color: #21262d;
            border-color: #8b949e;
        }

        .file-meta-badge {
            color: var(--text-muted);
            font-size: 12px;
        }

        /* Markdown Rendering Area */
        .content-body {
            flex: 1;
            overflow-y: auto;
            padding: 32px 48px;
            max-width: 1000px;
            margin: 0 auto;
            width: 100%;
        }

        /* Markdown Styles matching Screenshot */
        .markdown-body h1 {
            font-size: 26px;
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 8px;
            margin-top: 24px;
            margin-bottom: 16px;
        }

        .markdown-body h2 {
            font-size: 20px;
            font-weight: 600;
            margin-top: 24px;
            margin-bottom: 12px;
        }

        .markdown-body h3 {
            font-size: 16px;
            font-weight: 600;
            margin-top: 20px;
            margin-bottom: 8px;
        }

        .markdown-body p {
            line-height: 1.6;
            margin-bottom: 16px;
            font-size: 14px;
        }

        .markdown-body ul, .markdown-body ol {
            padding-left: 24px;
            margin-bottom: 16px;
            font-size: 14px;
            line-height: 1.6;
        }

        .markdown-body li {
            margin-bottom: 6px;
        }

        .markdown-body strong {
            color: #ffffff;
            font-weight: 600;
        }

        .markdown-body table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 24px;
            font-size: 13px;
        }

        .markdown-body th, .markdown-body td {
            border: 1px solid var(--border-color);
            padding: 8px 12px;
            text-align: left;
        }

        .markdown-body th {
            background-color: #161b22;
            font-weight: 600;
        }

        .markdown-body tr:nth-child(2n) {
            background-color: #0d1117;
        }

        .markdown-body a {
            color: var(--link-color);
            text-decoration: none;
        }

        .markdown-body a:hover {
            text-decoration: underline;
        }

        .markdown-body blockquote {
            border-left: 3px solid var(--link-color);
            background-color: #161b22;
            padding: 12px 16px;
            border-radius: 0 6px 6px 0;
            margin-bottom: 16px;
            color: var(--text-main);
        }

        .markdown-body hr {
            border: 0;
            height: 1px;
            background-color: var(--border-color);
            margin: 24px 0;
        }

        .markdown-body code {
            font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
            background-color: #21262d;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 85%;
        }

        #code-view {
            display: none;
            font-family: monospace;
            white-space: pre-wrap;
            font-size: 13px;
            line-height: 1.5;
            background: #0d1117;
            padding: 16px;
            border-radius: 6px;
        }
    </style>
</head>
<body>

    <!-- Left Sidebar -->
    <div id="sidebar">
        <div class="sidebar-header">
            <span><i class="fa-solid fa-folder-tree"></i> Files</span>
            <span style="font-size: 11px; color: var(--text-muted);"><i class="fa-solid fa-circle" style="color: #238636; font-size: 8px;"></i> Live Vault</span>
        </div>
        <div class="search-box">
            <input type="text" id="filter-input" placeholder="🔍 Go to file..." oninput="filterTree()">
        </div>
        <div class="file-tree" id="tree-container">
            <!-- Populated via JS -->
        </div>
    </div>

    <!-- Main Content Area -->
    <div id="main">
        <div class="content-header">
            <div class="breadcrumbs" id="breadcrumb-bar">
                <span>vault</span> / <span class="current-file" id="current-filename">index.md</span>
            </div>
            <div class="header-actions">
                <span class="file-meta-badge" id="file-meta">Loading...</span>
                <button class="tab-btn active" id="btn-preview" onclick="switchTab('preview')"><i class="fa-regular fa-eye"></i> Preview</button>
                <button class="tab-btn" id="btn-code" onclick="switchTab('code')"><i class="fa-solid fa-code"></i> Code</button>
            </div>
        </div>
        <div class="content-body">
            <div id="markdown-view" class="markdown-body">
                <!-- Rendered Markdown -->
            </div>
            <div id="code-view">
                <!-- Raw Markdown Source -->
            </div>
        </div>
    </div>

    <script>
        let currentFilePath = "raw/chat-queries/2021_hamilton_verstappen_championship_overview.md";
        let rawContent = "";

        async function init() {
            await loadTree();
            await loadFile(currentFilePath);
        }

        async function loadTree() {
            const res = await fetch('/api/tree');
            const data = await res.json();
            const container = document.getElementById('tree-container');
            container.innerHTML = renderTreeNodes(data.tree);
        }

        function renderTreeNodes(nodes) {
            let html = '';
            for (const node of nodes) {
                if (node.type === 'dir') {
                    html += `
                        <div class="tree-item">
                            <div class="tree-node" onclick="toggleFolder(this)">
                                <i class="fa-regular fa-folder-open" style="color: #8b949e;"></i>
                                <span>${node.name}</span>
                            </div>
                            <div class="tree-children">
                                ${renderTreeNodes(node.children)}
                            </div>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="tree-node file-node" data-path="${node.path}" onclick="loadFile('${node.path}')">
                            <i class="fa-regular fa-file-lines" style="color: #58a6ff;"></i>
                            <span>${node.name}</span>
                        </div>
                    `;
                }
            }
            return html;
        }

        function toggleFolder(elem) {
            const children = elem.nextElementSibling;
            if (children) {
                children.classList.toggle('collapsed');
                const icon = elem.querySelector('i');
                if (children.classList.contains('collapsed')) {
                    icon.className = 'fa-regular fa-folder';
                } else {
                    icon.className = 'fa-regular fa-folder-open';
                }
            }
        }

        async function loadFile(path) {
            currentFilePath = path;
            const res = await fetch(`/api/file?path=${encodeURIComponent(path)}`);
            if (!res.ok) {
                document.getElementById('markdown-view').innerHTML = `<p style="color: #f85149;">Error loading file: ${path}</p>`;
                return;
            }
            const data = await res.json();
            rawContent = data.content;

            // Update Breadcrumbs
            const parts = data.path.split('/');
            document.getElementById('breadcrumb-bar').innerHTML = parts.map((p, idx) => {
                if (idx === parts.length - 1) return `<span class="current-file">${p}</span>`;
                return `<span>${p}</span>`;
            }).join(' / ');

            document.getElementById('file-meta').innerText = `${data.lines_count} lines (${(data.size_bytes / 1024).toFixed(2)} KB)`;

            // Convert Wikilinks [[target|label]] or [[target]] to clickable links
            let parsedMarkdown = data.content.replace(/\[\[(.*?)\]\]/g, function(match, inner) {
                let target = inner;
                let label = inner;
                if (inner.includes('|')) {
                    const parts = inner.split('|');
                    target = parts[0].trim();
                    label = parts[1].trim();
                }
                return `<a href="#" onclick="loadFile('${target}.md'); return false;">${label}</a>`;
            });

            document.getElementById('markdown-view').innerHTML = marked.parse(parsedMarkdown);
            document.getElementById('code-view').innerText = data.content;

            // Update active node highlight
            document.querySelectorAll('.file-node').forEach(el => {
                el.classList.toggle('active', el.getAttribute('data-path') === path);
            });
        }

        function switchTab(mode) {
            document.getElementById('btn-preview').classList.toggle('active', mode === 'preview');
            document.getElementById('btn-code').classList.toggle('active', mode === 'code');
            document.getElementById('markdown-view').style.display = mode === 'preview' ? 'block' : 'none';
            document.getElementById('code-view').style.display = mode === 'code' ? 'block' : 'none';
        }

        function filterTree() {
            const query = document.getElementById('filter-input').value.toLowerCase();
            document.querySelectorAll('.file-node').forEach(node => {
                const text = node.innerText.toLowerCase();
                node.style.display = text.includes(query) ? 'flex' : 'none';
            });
        }

        window.onload = init;
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8500))
    print(f"🚀 Starting Wiki Web Viewer on http://127.0.0.1:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
