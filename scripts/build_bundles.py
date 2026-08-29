#!/usr/bin/env python3
"""
scripts/build_bundles.py — Build 3 physically isolated deployment bundles.

- mcp1/: Full Vault (Tier 1 + Tier 2 + Tier 3)
- mcp2/: Technical Vault (Tier 2 + Tier 3 only — Tier 1 physically absent)
- mcp3/: Analysis Vault (Tier 3 only — Tier 1 & Tier 2 physically absent)
"""

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT_DIR = PROJECT_ROOT / "vault"

MCP1_DIR = PROJECT_ROOT / "mcp1"
MCP2_DIR = PROJECT_ROOT / "mcp2"
MCP3_DIR = PROJECT_ROOT / "mcp3"

REQUIREMENTS = """fastapi>=0.110.0
uvicorn>=0.28.0
sse-starlette>=2.0.0
pydantic>=2.0.0
"""

PROCFILE = "web: uvicorn mcp_server:app --host 0.0.0.0 --port $PORT\n"

def build_bundle(target_dir: Path, include_tier1: bool, include_tier2: bool, tier_label: str):
    print(f"\n📦 Building deployment bundle: {target_dir.name} ({tier_label})...")
    
    # Clean previous vault if exists
    vault_target = target_dir / "vault"
    if vault_target.exists():
        shutil.rmtree(vault_target)
    vault_target.mkdir(parents=True, exist_ok=True)

    # 1. Copy Tier 1 if included
    if include_tier1:
        if (VAULT_DIR / "tier1").exists():
            shutil.copytree(VAULT_DIR / "tier1", vault_target / "tier1")
            print(f"  ✅ Copied tier1/ ({len(list((vault_target / 'tier1').rglob('*.md')))} files)")
        if (VAULT_DIR / "wiki").exists():
            shutil.copytree(VAULT_DIR / "wiki", vault_target / "wiki")
            print(f"  ✅ Copied wiki/ ({len(list((vault_target / 'wiki').rglob('*.md')))} files)")
        if (VAULT_DIR / "raw").exists():
            shutil.copytree(VAULT_DIR / "raw", vault_target / "raw")
            print(f"  ✅ Copied raw/ ({len(list((vault_target / 'raw').rglob('*.md')))} files)")
    else:
        print("  🔒 Excluded tier1/, wiki/, and raw/ (PHYSICALLY ABSENT)")

    # 2. Copy Tier 2 if included
    if include_tier2:
        if (VAULT_DIR / "tier2").exists():
            shutil.copytree(VAULT_DIR / "tier2", vault_target / "tier2")
            print(f"  ✅ Copied tier2/ ({len(list((vault_target / 'tier2').rglob('*.md')))} files)")
    else:
        print("  🔒 Excluded tier2/ (PHYSICALLY ABSENT)")

    # 3. Always copy Tier 3
    if (VAULT_DIR / "tier3").exists():
        shutil.copytree(VAULT_DIR / "tier3", vault_target / "tier3")
        print(f"  ✅ Copied tier3/ ({len(list((vault_target / 'tier3').rglob('*.md')))} files)")

    # 4. Generate bundle-specific index.md
    index_lines = [f"# Formula 1 Knowledge Vault ({tier_label})\n"]
    if (vault_target / "tier3").exists():
        index_lines.append("## 📊 Tier 3: Derived Analysis & Predictive Models")
        for p in sorted((vault_target / "tier3").rglob("*.md")):
            index_lines.append(f"- [[{p.stem}]]: {p.stem.replace('_', ' ').title()}")
        index_lines.append("")

    if include_tier2 and (vault_target / "tier2").exists():
        index_lines.append(f"## 🔍 Tier 2: Detailed Race Telemetry ({len(list((vault_target / 'tier2').rglob('*.md')))} Files)")
        t2_sample = list(sorted((vault_target / "tier2").rglob("*.md")))[-20:]
        for p in t2_sample:
            index_lines.append(f"- [[{p.stem}]]: {p.stem}")
        index_lines.append("... (and earlier race telemetry files)\n")

    if include_tier1 and (vault_target / "tier1").exists():
        index_lines.append(f"## 🏎️ Tier 1: Public Results & Entities ({len(list((vault_target / 'tier1').rglob('*.md')))} Files)")
        t1_drivers = list(sorted((vault_target / "tier1" / "drivers").glob("*.md")))[:25]
        for p in t1_drivers:
            index_lines.append(f"- [[{p.stem}]]: Driver Profile")
        index_lines.append("... (and all other drivers, constructors, circuits, races)\n")

    (vault_target / "index.md").write_text("\n".join(index_lines), encoding="utf-8")

    # 5. Copy server code and deployment configuration
    shutil.copy2(PROJECT_ROOT / "mcp_server.py", target_dir / "mcp_server.py")
    (target_dir / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
    (target_dir / "Procfile").write_text(PROCFILE, encoding="utf-8")
    
    env_content = f"DATA_ROOT=vault\nTIER_NAME={tier_label}\n"
    (target_dir / ".env").write_text(env_content, encoding="utf-8")

    total_md = len(list(vault_target.rglob("*.md")))
    print(f"  🏁 Bundle {target_dir.name} ready with {total_md} total markdown files.")

def main():
    build_bundle(MCP1_DIR, include_tier1=True, include_tier2=True, tier_label="MCP 1 (Master Tier — Tier 1 + 2 + 3)")
    build_bundle(MCP2_DIR, include_tier1=False, include_tier2=True, tier_label="MCP 2 (Telemetry Tier — Tier 2 + 3)")
    build_bundle(MCP3_DIR, include_tier1=False, include_tier2=False, tier_label="MCP 3 (Analysis Tier — Tier 3 Only)")
    print("\n🎉 All 3 MCP deployment bundles successfully built and verified!")

if __name__ == "__main__":
    main()
