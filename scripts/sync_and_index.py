#!/usr/bin/env python3
"""
scripts/sync_and_index.py — One-Click Re-Index, Vault Sync, and MCP Bundle Refresh.

Runs automatically:
1. Re-indexes all Concepts, Entities, and Query Threads.
2. Refreshes Master index.md and Category MOCs.
3. Records append-only timestamp to log.md.
4. Synchronizes physical MCP bundles (mcp1, mcp2, mcp3).
5. Runs test suite to verify physical isolation before deployment.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT_DIR = PROJECT_ROOT / "vault"
LOG_FILE = VAULT_DIR / "log.md"

def main():
    print("=" * 80)
    print("🔄 FORMULA 1 KNOWLEDGE VAULT: AUTOMATED SYNC & RE-INDEXING PIPELINE")
    print("=" * 80)

    env_python = sys.executable

    # 1. Build & Index Complete Wiki System
    print("\n[STEP 1] Re-indexing Concepts, Entities, and Query Threads...")
    res = subprocess.run([env_python, str(PROJECT_ROOT / "scripts" / "build_complete_wiki_system.py")], check=True)

    # 2. Synchronize MCP Bundles
    print("\n[STEP 2] Synchronizing physical MCP deployment bundles...")
    res = subprocess.run([env_python, str(PROJECT_ROOT / "scripts" / "build_bundles.py")], check=True)

    # 3. Log execution
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    log_entry = f"""
## [{now_utc}] — `scripts/sync_and_index.py` Automated Sync
- **Status:** Complete Vault & MCP bundle synchronization.
- **Index Files Updated:** `index.md`, `concepts-index.md`, `entities-index.md`, `queries-index.md`.
- **MCP Bundles:** Refreshed `mcp1/`, `mcp2/`, and `mcp3/` with physical tier boundaries.
"""
    if LOG_FILE.exists():
        current = LOG_FILE.read_text(encoding="utf-8")
        LOG_FILE.write_text(current + log_entry, encoding="utf-8")
    else:
        LOG_FILE.write_text(f"# Formula 1 Knowledge Vault Changelog\n{log_entry}", encoding="utf-8")

    # 4. Verify with test suite
    print("\n[STEP 3] Running Automated Validation Test Suite...")
    subprocess.run([env_python, str(PROJECT_ROOT / "scripts" / "test_mcp_servers.py")], check=True)

    print("\n" + "=" * 80)
    print("🎉 ALL VAULT INDEXES, ENTITY HUBS & MCP BUNDLES ARE 100% IN SYNC!")
    print("=" * 80)

if __name__ == "__main__":
    main()
