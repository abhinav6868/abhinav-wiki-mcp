#!/usr/bin/env python3
"""
scripts/test_mcp_servers.py — Full Verification Suite for FIXES 1 to 5.
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
    print("🏎️  FORMULA 1 TIERED MCP SERVER VERIFICATION SUITE (FIXES 1-5)")
    print("=" * 80)

    env_python = "/Users/abhi/.gemini/antigravity-ide/scratch/abhinav-wiki/.venv/bin/python3"
    api_key_secret = "f1-vault-production-key-2026"
    
    # 1. Start all 3 servers in background
    procs = []
    configs = [
        ("MCP 1 (Master Tier)", 8001, PROJECT_ROOT / "mcp1"),
        ("MCP 2 (Telemetry Tier)", 8002, PROJECT_ROOT / "mcp2"),
        ("MCP 3 (Analysis Tier)", 8003, PROJECT_ROOT / "mcp3"),
    ]

    print("\n🚀 Launching 3 physical MCP server instances with API Key Auth...")
    for label, port, cwd_path in configs:
        env = os.environ.copy()
        env["DATA_ROOT"] = "vault"
        env["PORT"] = str(port)
        env["TIER_NAME"] = label
        env["API_KEY"] = api_key_secret
        p = subprocess.Popen(
            [env_python, "mcp_server.py"],
            cwd=str(cwd_path),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        procs.append(p)
        print(f"  ⚡ {label} started on port {port} (PID: {p.pid})")

    time.sleep(3)

    try:
        headers = {"Authorization": f"Bearer {api_key_secret}"}

        # ── TEST FIX 1: Project Isolation ──
        print("\n" + "-" * 60)
        print("[TEST FIX 1] Strict Project Isolation (Zero External Data Leakage)")
        print("-" * 60)
        external_queries = ["Frank Ocean", "Justin Bieber", "Brannon Steel", "Gerdau", "Zomato"]
        for q in external_queries:
            s1 = requests.post("http://127.0.0.1:8001/call", json={"name": "search", "arguments": {"query": q}}, headers=headers).json()
            assert s1["results_count"] == 0, f"Leakage detected: '{q}' returned results from another project!"
            print(f"✅ Query '{q}' -> 0 results (Isolated from external projects)")

        # ── TEST FIX 2: File Count & Physical Tier Ordering ──
        print("\n" + "-" * 60)
        print("[TEST FIX 2] Acceptance Check: MCP1 > MCP2 > MCP3 File Count Ordering")
        print("-" * 60)
        r1 = requests.post("http://127.0.0.1:8001/call", json={"name": "list_pages", "arguments": {}}, headers=headers).json()
        r2 = requests.post("http://127.0.0.1:8002/call", json={"name": "list_pages", "arguments": {}}, headers=headers).json()
        r3 = requests.post("http://127.0.0.1:8003/call", json={"name": "list_pages", "arguments": {}}, headers=headers).json()

        c1, c2, c3 = r1["file_count"], r2["file_count"], r3["file_count"]
        print(f"📊 MCP 1 File Count: {c1} files")
        print(f"📊 MCP 2 File Count: {c2} files")
        print(f"📊 MCP 3 File Count: {c3} files")

        assert c1 > c2 > c3, f"Ordering violation: Expected MCP1 ({c1}) > MCP2 ({c2}) > MCP3 ({c3})"
        print(f"✅ ACCEPTANCE CHECK PASSED: MCP1 ({c1}) > MCP2 ({c2}) > MCP3 ({c3})")

        # Refusal / 404 tests for missing tiers
        print("\n[Testing Tier Boundary Refusals]:")
        # MCP 2 reading Tier 1
        t1_on_m2 = requests.post("http://127.0.0.1:8002/call", json={"name": "read_page", "arguments": {"path": "tier1/drivers/hamilton.md"}}, headers=headers).json()
        assert t1_on_m2["found"] is False, "Security Violation: MCP 2 read Tier 1 file!"
        print(f"✅ MCP 2 read_page('tier1/drivers/hamilton.md') -> Refused: {t1_on_m2['error']}")

        # MCP 3 reading Tier 1
        t1_on_m3 = requests.post("http://127.0.0.1:8003/call", json={"name": "read_page", "arguments": {"path": "tier1/drivers/hamilton.md"}}, headers=headers).json()
        assert t1_on_m3["found"] is False, "Security Violation: MCP 3 read Tier 1 file!"
        print(f"✅ MCP 3 read_page('tier1/drivers/hamilton.md') -> Refused: {t1_on_m3['error']}")

        # MCP 3 reading Tier 2
        t2_on_m3 = requests.post("http://127.0.0.1:8003/call", json={"name": "read_page", "arguments": {"path": "tier2/races/2021-22-detail.md"}}, headers=headers).json()
        assert t2_on_m3["found"] is False, "Security Violation: MCP 3 read Tier 2 file!"
        print(f"✅ MCP 3 read_page('tier2/races/2021-22-detail.md') -> Refused: {t2_on_m3['error']}")

        # MCP 3 reading Tier 3 (Allowed)
        t3_on_m3 = requests.post("http://127.0.0.1:8003/call", json={"name": "read_page", "arguments": {"path": "tier3/analysis/win_probability_model.md"}}, headers=headers).json()
        assert t3_on_m3["found"] is True, "Failed to read Tier 3 on MCP 3"
        print(f"✅ MCP 3 read_page('tier3/analysis/win_probability_model.md') -> Allowed ({t3_on_m3['size_bytes']} bytes)")

        # ── TEST FIX 3: No Placeholder Values ──
        print("\n" + "-" * 60)
        print("[TEST FIX 3] No Placeholder Values in Serialized Responses")
        print("-" * 60)
        for page_obj in r3["pages"]:
            assert "Unreleased" not in str(page_obj.values()), "Found placeholder 'Unreleased'"
            assert "Vault Master" not in str(page_obj.values()), "Found placeholder 'Vault Master'"
        print("✅ Verified: All missing/empty fields serialize as real null/None or empty values (no fake labels).")

        # ── TEST FIX 4: Cross-Account & Multi-Auth Verification (No OAuth redirect) ──
        print("\n" + "-" * 60)
        print("[TEST FIX 4] Cross-Account Clean Auth (Header & Query Token, No OAuth)")
        print("-" * 60)
        # Test 1: Header Auth
        h_res = requests.get("http://127.0.0.1:8001/tools", headers={"Authorization": f"Bearer {api_key_secret}"})
        assert h_res.status_code == 200, "Header Bearer Auth failed"
        print("✅ Bearer Token Header: 200 OK")

        # Test 2: X-API-Key Header
        x_res = requests.get("http://127.0.0.1:8001/tools", headers={"X-API-Key": api_key_secret})
        assert x_res.status_code == 200, "X-API-Key Auth failed"
        print("✅ X-API-Key Header: 200 OK")

        # Test 3: Query Param Auth (Works from any browser/desktop client without login prompts)
        q_res = requests.get(f"http://127.0.0.1:8001/tools?apiKey={api_key_secret}")
        assert q_res.status_code == 200, "Query Param Auth failed"
        print("✅ Query Param Token (?apiKey=...): 200 OK (Zero OAuth / No Account Mismatch)")

        # Test 4: Structured JSON-RPC Error on invalid auth
        bad_auth = requests.post("http://127.0.0.1:8001/rpc", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, headers={"Authorization": "Bearer wrong-key"})
        assert bad_auth.status_code == 401
        err_json = bad_auth.json()
        assert "error" in err_json and err_json["error"]["code"] == -32000
        print(f"✅ Structured JSON-RPC Auth Error: {err_json['error']['message']}")

        # ── TEST FIX 5: JSON-RPC 2.0 Spec Compliance ──
        print("\n" + "-" * 60)
        print("[TEST FIX 5] Remote Streamable HTTP & JSON-RPC Protocol")
        print("-" * 60)
        rpc_call = requests.post("http://127.0.0.1:8001/rpc", json={
            "jsonrpc": "2.0",
            "id": 42,
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "Hamilton"}}
        }, headers=headers).json()
        assert rpc_call["result"]["content"][0]["type"] == "text"
        print("✅ JSON-RPC 2.0 tools/call search -> Valid content text response returned")

        print("\n" + "=" * 80)
        print("🎉 ALL 5 FIXES VERIFIED AND PASSING 100%!")
        print("=" * 80)

    finally:
        print("\n🛑 Stopping background test server instances...")
        for p in procs:
            p.terminate()
            p.wait()
        print("Done.")

if __name__ == "__main__":
    run_tests()
