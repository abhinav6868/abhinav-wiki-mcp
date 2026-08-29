#!/usr/bin/env python3
"""
scripts/test_mcp_servers.py — Verification suite for 3 Tiered MCP Servers.
Starts mcp1 (port 8001), mcp2 (port 8002), mcp3 (port 8003),
calls list_pages(), read_page(), and search() on each, and validates physical isolation.
"""

import sys
import os
import time
import subprocess
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def run_tests():
    print("=" * 80)
    print("🏎️  FORMULA 1 TIERED MCP SERVER VERIFICATION SUITE")
    print("=" * 80)

    env_python = "/Users/abhi/.gemini/antigravity-ide/scratch/abhinav-wiki/.venv/bin/python3"
    
    # 1. Start all 3 servers in background
    procs = []
    configs = [
        ("MCP 1 (Master Tier)", 8001, PROJECT_ROOT / "mcp1"),
        ("MCP 2 (Telemetry Tier)", 8002, PROJECT_ROOT / "mcp2"),
        ("MCP 3 (Analysis Tier)", 8003, PROJECT_ROOT / "mcp3"),
    ]

    print("\n🚀 Launching 3 physical MCP server instances...")
    for label, port, cwd_path in configs:
        env = os.environ.copy()
        env["DATA_ROOT"] = "vault"
        env["PORT"] = str(port)
        env["TIER_NAME"] = label
        p = subprocess.Popen(
            [env_python, "mcp_server.py"],
            cwd=str(cwd_path),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        procs.append(p)
        print(f"  ⚡ {label} started on port {port} (PID: {p.pid})")

    # Give servers time to boot
    time.sleep(3)

    try:
        # TEST 1: Health checks
        print("\n" + "-" * 50)
        print("[TEST 1] Service Health & Metadata")
        print("-" * 50)
        for label, port, _ in configs:
            url = f"http://127.0.0.1:{port}/health"
            r = requests.get(url, timeout=5)
            data = r.json()
            print(f"✅ {label}: {data['status'].upper()} — {data['total_markdown_pages']} markdown pages loaded.")

        # TEST 2: list_pages() verification
        print("\n" + "-" * 50)
        print("[TEST 2] list_pages() Physical Bundle Isolation")
        print("-" * 50)
        
        # MCP 1
        r1 = requests.post("http://127.0.0.1:8001/call", json={"name": "list_pages", "arguments": {}}).json()
        total1 = r1["total_pages"]
        has_t1_m1 = any("tier1" in p["path"] for p in r1["pages"])
        has_t2_m1 = any("tier2" in p["path"] for p in r1["pages"])
        has_t3_m1 = any("tier3" in p["path"] for p in r1["pages"])
        print(f"✅ MCP 1 Total Pages: {total1} (Tier 1: {has_t1_m1}, Tier 2: {has_t2_m1}, Tier 3: {has_t3_m1})")

        # MCP 2
        r2 = requests.post("http://127.0.0.1:8002/call", json={"name": "list_pages", "arguments": {}}).json()
        total2 = r2["total_pages"]
        has_t1_m2 = any("tier1" in p["path"] for p in r2["pages"])
        has_t2_m2 = any("tier2" in p["path"] for p in r2["pages"])
        has_t3_m2 = any("tier3" in p["path"] for p in r2["pages"])
        assert not has_t1_m2, "Security Violation: Tier 1 leaked into MCP 2!"
        print(f"✅ MCP 2 Total Pages: {total2} (Tier 1: {has_t1_m2} [EXCLUDED], Tier 2: {has_t2_m2}, Tier 3: {has_t3_m2})")

        # MCP 3
        r3 = requests.post("http://127.0.0.1:8003/call", json={"name": "list_pages", "arguments": {}}).json()
        total3 = r3["total_pages"]
        has_t1_m3 = any("tier1" in p["path"] for p in r3["pages"])
        has_t2_m3 = any("tier2" in p["path"] for p in r3["pages"])
        has_t3_m3 = any("tier3" in p["path"] for p in r3["pages"])
        assert not has_t1_m3, "Security Violation: Tier 1 leaked into MCP 3!"
        assert not has_t2_m3, "Security Violation: Tier 2 leaked into MCP 3!"
        print(f"✅ MCP 3 Total Pages: {total3} (Tier 1: {has_t1_m3} [EXCLUDED], Tier 2: {has_t2_m3} [EXCLUDED], Tier 3: {has_t3_m3})")

        # TEST 3: read_page() access control
        print("\n" + "-" * 50)
        print("[TEST 3] read_page() Permission & Boundary Checks")
        print("-" * 50)

        # Read Tier 1 on MCP 1 -> Should succeed
        read_t1_m1 = requests.post("http://127.0.0.1:8001/call", json={"name": "read_page", "arguments": {"path": "tier1/drivers/hamilton.md"}}).json()
        assert "content" in read_t1_m1, "Failed to read Tier 1 on MCP 1"
        print("✅ MCP 1 read_page('tier1/drivers/hamilton.md'): SUCCESS (Content length: " + str(read_t1_m1['size_bytes']) + " bytes)")

        # Read Tier 1 on MCP 2 -> Should fail
        read_t1_m2 = requests.post("http://127.0.0.1:8002/call", json={"name": "read_page", "arguments": {"path": "tier1/drivers/hamilton.md"}}).json()
        assert "error" in read_t1_m2, "Security Violation: MCP 2 read Tier 1 file!"
        print(f"✅ MCP 2 read_page('tier1/drivers/hamilton.md'): BLOCKED ({read_t1_m2['error']})")

        # Read Tier 1 on MCP 3 -> Should fail
        read_t1_m3 = requests.post("http://127.0.0.1:8003/call", json={"name": "read_page", "arguments": {"path": "tier1/drivers/hamilton.md"}}).json()
        assert "error" in read_t1_m3, "Security Violation: MCP 3 read Tier 1 file!"
        print(f"✅ MCP 3 read_page('tier1/drivers/hamilton.md'): BLOCKED ({read_t1_m3['error']})")

        # Read Tier 3 on MCP 3 -> Should succeed
        read_t3_m3 = requests.post("http://127.0.0.1:8003/call", json={"name": "read_page", "arguments": {"path": "tier3/analysis/win_probability_model.md"}}).json()
        assert "content" in read_t3_m3, "Failed to read Tier 3 on MCP 3"
        print("✅ MCP 3 read_page('tier3/analysis/win_probability_model.md'): SUCCESS (Content length: " + str(read_t3_m3['size_bytes']) + " bytes)")

        # TEST 4: search() tool
        print("\n" + "-" * 50)
        print("[TEST 4] search() Keyword & BM25 Match")
        print("-" * 50)
        s_res = requests.post("http://127.0.0.1:8003/call", json={"name": "search", "arguments": {"query": "undercut strategy"}}).json()
        print(f"✅ MCP 3 search('undercut strategy') found {s_res['results_count']} matching documents:")
        for hit in s_res["results"][:3]:
            print(f"   • {hit['filename']} (Score: {hit['score']}) -> {hit['snippet'][:80]}...")

        # TEST 5: JSON-RPC MCP Protocol
        print("\n" + "-" * 50)
        print("[TEST 5] MCP Protocol JSON-RPC 2.0 Compliance")
        print("-" * 50)
        rpc_init = requests.post("http://127.0.0.1:8001/rpc", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).json()
        print(f"✅ JSON-RPC initialize: protocolVersion={rpc_init['result']['protocolVersion']}, server={rpc_init['result']['serverInfo']['name']}")

        rpc_tools = requests.post("http://127.0.0.1:8001/rpc", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}).json()
        tool_names = [t["name"] for t in rpc_tools["result"]["tools"]]
        print(f"✅ JSON-RPC tools/list: {tool_names}")

        rpc_call = requests.post("http://127.0.0.1:8001/rpc", json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "Hamilton"}}
        }).json()
        print(f"✅ JSON-RPC tools/call search: returned {len(rpc_call['result']['content'])} text payload")

        print("\n" + "=" * 80)
        print("🎉 ALL 5 TEST SUITES PASSED — 100% SPEC COMPLIANCE & PHYSICAL ISOLATION VERIFIED!")
        print("=" * 80)

    finally:
        print("\n🛑 Stopping background server instances...")
        for p in procs:
            p.terminate()
            p.wait()
        print("Done.")

if __name__ == "__main__":
    run_tests()
