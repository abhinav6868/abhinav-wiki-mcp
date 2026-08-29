# 🏎️ Formula 1 Tiered Knowledge Vault & MCP Mesh

A persistent, tiered personal knowledge wiki built from 74 years of historical Formula 1 World Championship data (1950–2024), architected strictly according to **Andrej Karpathy's "LLM Wiki" Pattern** (ingest raw sources once, write persistent interlinked markdown pages with Obsidian `[[wikilinks]]`, zero live re-fetching at query time).

The repository includes **three physically isolated Model Context Protocol (MCP) servers**, each serving a strictly bounded security tier of the knowledge vault.

---

## 🏛️ Repository Architecture

```text
f1-wiki/
├── raw_data/                           # 11 Historical CSVs (Ergast F1 1950–2024)
│   ├── races.csv, results.csv, drivers.csv, constructors.csv, circuits.csv
│   ├── lap_times.csv, pit_stops.csv, qualifying.csv, status.csv
│   └── driver_standings.csv, constructor_standings.csv
│
├── vault/                              # Obsidian-Compatible Knowledge Vault (3,501+ Markdown Pages)
│   ├── tier1/                          # Tier 1: Public Career Statistics, Bios & Standings
│   │   ├── drivers/                    # 865 Driver profiles (e.g. hamilton.md, senna.md)
│   │   ├── constructors/               # 214 Constructor records (e.g. ferrari.md, mclaren.md)
│   │   ├── circuits/                   # 78 Circuit records (e.g. monza.md, silverstone.md)
│   │   └── races/                      # 1,172 Grand Prix Race dossiers (e.g. 2021-22.md)
│   ├── tier2/                          # Tier 2: Technical Telemetry & Pit Strategy
│   │   └── races/                      # 1,172 Detailed Telemetry dossiers (e.g. 2021-22-detail.md)
│   ├── tier3/                          # Tier 3: Derived Analysis & Machine Learning
│   │   └── analysis/                   # 4 Quantitative Analytics & Scikit-Learn Model pages
│   ├── index.md                        # Master structured catalog across all entities
│   └── log.md                          # Append-only execution changelog
│
├── scripts/                            # Pipeline & Ingestion Automation
│   ├── ingest.py                       # Step 1 & 2: Raw CSV parsing & Vault markdown generator
│   ├── analyze.py                      # Step 3: Tier 3 ML models & statistical analysis generator
│   ├── build_bundles.py                # Step 4: Physical bundling of MCP1, MCP2, MCP3
│   └── test_mcp_servers.py             # Step 5: Automated validation & access boundary test suite
│
├── mcp_server.py                       # Unified FastMCP / SSE / JSON-RPC Server Engine
├── mcp1/                               # MCP 1 Deployment Bundle (Master Tier: Tier 1 + 2 + 3, 3,506 files)
├── mcp2/                               # MCP 2 Deployment Bundle (Telemetry Tier: Tier 2 + 3, 1,177 files)
├── mcp3/                               # MCP 3 Deployment Bundle (Analysis Tier: Tier 3 Only, 5 files)
└── render.yaml                         # Cloud Blueprint for 3 independent Render web services
```

---

## 🔒 Tier-to-Data Security Mapping & Physical Isolation

| Tier Level | Target Bundle | File Count | Included Vault Paths | Excluded (Physically Absent) |
| :--- | :---: | :---: | :--- | :--- |
| **Tier 1 + 2 + 3** | `mcp1/` | **3,506** | `tier1/`, `tier2/`, `tier3/`, `index.md`, `log.md` | *None (Master Clearance)* |
| **Tier 2 + 3** | `mcp2/` | **1,177** | `tier2/`, `tier3/`, `index.md` | `tier1/` *(Physically absent)* |
| **Tier 3 Only** | `mcp3/` | **5** | `tier3/`, `index.md` | `tier1/`, `tier2/` *(Physically absent)* |

> ⚠️ **Physical Isolation Note:** `mcp2` and `mcp3` do not filter permissions at runtime; unpermitted markdown files are physically omitted from their deployment packages to prevent any possibility of data leakage.

---

## 🚀 How to Re-Run Ingestion & Refresh the Vault

The ingestion pipeline is completely deterministic and idempotent. Re-running updates files in place and refreshes `index.md` and `log.md` without duplicating records.

```bash
# 1. Ingest raw CSV data and build/update Tier 1 & Tier 2 markdown pages
python3 scripts/ingest.py

# 2. Re-compute machine learning models and generate Tier 3 analysis
python3 scripts/analyze.py

# 3. Synchronize physical bundles for MCP1, MCP2, and MCP3
python3 scripts/build_bundles.py

# 4. Run automated test suite verifying physical isolation & MCP protocol
python3 scripts/test_mcp_servers.py
```

---

## 📊 Tier 3 Derived Analysis & Machine Learning Overview

1. **`driver_consistency.md`**: Computes the Driver Consistency Index (DCI) across all drivers with 30+ starts, balancing standard deviation of finishes against points conversion rates.
2. **`pit_strategy.md`**: Evaluates the historical win rate of undercut vs. overcut across technical eras (refueling, early Pirelli high-degradation, wide-body hybrid, and ground effect).
3. **`win_probability_model.md`**: Scikit-Learn Gradient Boosted Decision Tree (GBDT) predicting Grand Prix victory probability from starting grid position, rolling form, and team strength (**95.71% accuracy, 0.9394 ROC-AUC**).
4. **`style_clusters.md`**: Unsupervised K-Means clustering ($k=4$) categorizing drivers into tactical typologies (*Elite Front-Runners*, *Midfield Points Harvesters*, *Aggressive Attackers*, *Backmarker Specialists*).

---

## 🛠️ Exposed MCP Tools

Each MCP server exposes three standard tools over JSON-RPC 2.0 and Server-Sent Events (SSE):

1. **`list_pages(directory="")`**: Returns an array of available relative page paths, file sizes, and security classifications.
2. **`read_page(path)`**: Returns the exact Markdown content of any authorized document.
3. **`search(query, limit=10)`**: Full-text BM25 and keyword match over the active bundle with header matching and snippet extraction.

---

## 🌐 Cloud Deployment (Render)

The project includes `render.yaml` declaring 3 distinct web services:
- **`f1-vault-mcp1-master`** (Port 8000 / Root: `mcp1/`)
- **`f1-vault-mcp2-telemetry`** (Port 8000 / Root: `mcp2/`)
- **`f1-vault-mcp3-analysis`** (Port 8000 / Root: `mcp3/`)
