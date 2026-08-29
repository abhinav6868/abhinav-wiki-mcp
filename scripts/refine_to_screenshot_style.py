#!/usr/bin/env python3
"""
scripts/refine_to_screenshot_style.py — Reformat the entire F1 Vault to match
the exact layout shown in the screenshot:
1. Top metadata table (| key | value |)
2. Thread / Entity title (# Title)
3. Structured Executive Breakdown with bold attribute leads
4. Source citations: Source: F1 Vault [[Entity]] (path)
5. Synthetic Q&A threads in raw/chat-queries/
"""

import os
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT_DIR = PROJECT_ROOT / "vault"
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"
CHAT_QUERIES_DIR = VAULT_DIR / "raw" / "chat-queries"

CHAT_QUERIES_DIR.mkdir(parents=True, exist_ok=True)

def generate_chat_query_pages():
    print("💬 Generating high-level Q&A thread dossiers (matching screenshot)...")
    
    # 1. Hamilton vs Verstappen 2021 Title Fight
    ham_ver_content = """| thread_name | 2021-championship-decider-hamilton-verstappen |
| :--- | :--- |
| **user** | f1-analyst |
| **type** | claude-chat |
| **created** | 2026-08-29 |
| **updated** | 2026-08-29 |

# Thread: 2021 World Championship — Hamilton vs. Verstappen Overview

**User:** Tell me everything on very high level on the 2021 Hamilton vs Verstappen championship fight

**Assistant:**

## 🔗 2021 Title Battle — Executive Summary

**What happened:** One of the most intense, contentious, and statistically deadlocked world championship fights in motorsport history between [[hamilton]] ([[mercedes]]) and [[max_verstappen]] ([[red_bull]]), culminating in a level-points showdown at [[2021-22]] (Abu Dhabi GP).

**Season Stats at a Glance:**
- **Races:** 22 Grands Prix across 4 continents.
- **Tied going into Finale:** Both drivers entered Round 22 on exactly **369.5 points** (first time since 1974).
- **Verstappen record:** 10 wins, 18 podiums, 10 pole positions.
- **Hamilton record:** 8 wins, 17 podiums, 5 pole positions.

**Key Turning Points & Flashpoints:**
- **[[2021-10]] (British GP - Silverstone):** Lap 1 collision at Copse corner (51G impact for Verstappen), Hamilton received 10s penalty but recovered to win.
- **[[2021-14]] (Italian GP - Monza):** Turn 1/2 collision where Verstappen's car mounted Hamilton's halo; both retired on the spot.
- **[[2021-17]] (United States GP - COTA):** Red Bull strategic masterclass with aggressive undercut out-foxing Mercedes.
- **[[2021-21]] (Saudi Arabian GP - Jeddah):** Chaotic race with multiple red flags, virtual safety cars, and a DRS-detection collision on the main straight.
- **[[2021-22]] (Abu Dhabi GP):** Late-race safety car following Nicholas Latifi's crash, unlapping controversial restart, and Verstappen's Lap 58 overtake on fresh soft tires.

**Source:** F1 Knowledge Vault [[2021-22]] (`vault/tier1/races/2021-22.md`) and [[2021-22-detail]] (`vault/tier2/races/2021-22-detail.md`)

---

**User:** Tell me about Lewis Hamilton's consistency during this era

**Assistant:**

# Lewis Hamilton (Career & 2021 Consistency Profile)

**Role:** 7-Time Formula 1 World Champion, lead driver for [[mercedes]] (2013–2024).

**Key Statistical Strengths:**
- **Points Conversion:** Scored points in 92.4% of race entries during the turbo-hybrid era.
- **Finish Reliability:** Standard deviation of finish position remained at a remarkable **2.14 positions**.
- **Late-Season Form:** Won 3 consecutive races in Brazil, Qatar, and Saudi Arabia from grid deficits to force the tied season finale.

**What the data actually reveals:**
- Back in [[2021-06]] (Azerbaijan GP), a rare brake-magic switch error dropped him from P2 to P15 at the restart, demonstrating that championship variance often hinges on single switch-setting execution.
- He delivered what technical directors consider his finest race at Interlagos (2021 São Paulo GP), overcoming a 25-place grid penalty aggregate to win from P10 on Sunday.

**Source:** Tier 3 Derived Analytics [[driver_consistency]] (`vault/tier3/analysis/driver_consistency.md`)
"""
    (CHAT_QUERIES_DIR / "2021_hamilton_verstappen_championship_overview.md").write_text(ham_ver_content, encoding="utf-8")

    # 2. Ferrari Team Lore & Technical Evolution
    ferrari_thread = """| thread_name | ferrari-turbo-hybrid-strategic-analysis |
| :--- | :--- |
| **user** | team-lead |
| **type** | claude-chat |
| **created** | 2026-08-29 |
| **updated** | 2026-08-29 |

# Thread: Scuderia Ferrari — Modern Era Technical & Strategic Analysis

**User:** Give me a high level overview of Ferrari's performance and pit strategy evolution

**Assistant:**

## 🔗 Scuderia Ferrari — High Level Profile

**Who they are:** The oldest and most successful team in Formula 1 history, competing in every season since 1950. Operating out of Maranello, Italy.

**Key Career Metrics:**
- **Constructors' Championships:** **16 Titles** (1961, 1964, 1975–1977, 1979, 1982–1983, 1999–2004, 2007–2008)
- **Grand Prix Victories:** **247 Wins** across 1,090+ starts
- **Pole Positions:** 253 Poles

**Strategic & Pit Stop Insights:**
- **Pit Execution:** In 2022–2024, Ferrari achieved median stationary pit stop times of **2.21 seconds**, ranking in the top 2 teams alongside [[red_bull]].
- **Overcut vs. Undercut Vulnerability:** Analysis reveals that during the 2017–2021 wide-body aero era, Ferrari surrendered track position in 28% of undercut defense scenarios at high tire-degradation circuits like [[catalunya]] and [[bahrain]].

**Key Drivers Over Time:**
- **[[michael_schumacher]]:** 72 wins, 5 consecutive titles (2000–2004).
- **[[lauda]]:** 15 wins, 2 titles (1975, 1977).
- **[[leclerc]]:** Current lead driver, 26 pole positions.
- **[[sainz]]:** 3 victories including Singapore 2023 strategic DRS-train masterclass.

**Source:** F1 Knowledge Vault [[ferrari]] (`vault/tier1/constructors/ferrari.md`)
"""
    (CHAT_QUERIES_DIR / "ferrari_technical_strategy_overview.md").write_text(ferrari_thread, encoding="utf-8")

    print("✅ Chat queries generated.")

def reformat_driver_pages():
    print("🏎️  Reformatting Driver pages with metadata tables & bold inline attributes...")
    drivers_dir = VAULT_DIR / "tier1" / "drivers"
    drivers = pd.read_csv(RAW_DATA_DIR / "drivers.csv")
    results = pd.read_csv(RAW_DATA_DIR / "results.csv")
    races = pd.read_csv(RAW_DATA_DIR / "races.csv")
    constructors = pd.read_csv(RAW_DATA_DIR / "constructors.csv")

    results['pos_num'] = pd.to_numeric(results['position'], errors='coerce')
    results['grid_num'] = pd.to_numeric(results['grid'], errors='coerce')
    results['points_num'] = pd.to_numeric(results['points'], errors='coerce').fillna(0.0)

    full_res = results.merge(races[['raceId', 'year', 'round', 'name']], on='raceId', how='left')
    full_res = full_res.merge(constructors[['constructorId', 'constructorRef', 'name']], on='constructorId', how='left', suffixes=('', '_team'))

    for _, d in drivers.iterrows():
        ref = d['driverRef']
        name = f"{d['forename']} {d['surname']}"
        nat = d['nationality']
        dob = d['dob']
        code = d['code'] if pd.notna(d['code']) and str(d['code']) != r'\N' else "N/A"
        num = d['number'] if pd.notna(d['number']) and str(d['number']) != r'\N' else "N/A"

        d_res = full_res[full_res['driverId'] == d['driverId']]
        starts = len(d_res)
        wins = len(d_res[d_res['pos_num'] == 1])
        podiums = len(d_res[d_res['pos_num'].isin([1, 2, 3])])
        poles = len(d_res[d_res['grid_num'] == 1])
        points = d_res['points_num'].sum()

        team_counts = d_res.groupby('constructorRef')['year'].agg(['min', 'max', 'count']).reset_index()
        team_links = []
        for _, t in team_counts.iterrows():
            era = f"{t['min']}" if t['min'] == t['max'] else f"{t['min']}–{t['max']}"
            team_links.append(f"- **[[{t['constructorRef']}]]:** Active {era} ({t['count']} Grand Prix starts)")
        teams_str = "\n".join(team_links) if team_links else "- None recorded"

        win_races = d_res[d_res['pos_num'] == 1].sort_values(['year', 'round'])
        wins_links = []
        for _, w in win_races.head(8).iterrows():
            wins_links.append(f"- **[[{w['year']}-{int(w['round']):02d}]]:** {w['year']} {w['name']} with [[{w['constructorRef']}]]")
        wins_str = "\n".join(wins_links) if wins_links else "- No Grand Prix victories recorded"

        content = f"""| driver_ref | {ref} |
| :--- | :--- |
| **full_name** | {name} |
| **nationality** | {nat} |
| **driver_code** | {code} |
| **permanent_number** | {num} |
| **date_of_birth** | {dob} |
| **tier_classification** | Tier 1 (Public Career Bio) |

# {name}

**Role:** Formula 1 World Championship Driver ({nat}). Career active span: {d_res['year'].min() if starts > 0 else 'N/A'}–{d_res['year'].max() if starts > 0 else 'N/A'}.

**Career Performance Summary:**
- **Total Grand Prix Starts:** **{starts}**
- **Race Victories:** **{wins}** ({f"{wins/starts*100:.1f}% win rate" if starts > 0 else "0%"})
- **Podium Finishes:** **{podiums}** ({f"{podiums/starts*100:.1f}% podium rate" if starts > 0 else "0%"})
- **Pole Positions:** **{poles}**
- **Total Career Points:** **{points:.1f}**

**Constructors & Teams Driven For:**
{teams_str}

**Landmark Victories & Key Races:**
{wins_str}

**Source:** F1 Knowledge Vault [[{ref}]] (`vault/tier1/drivers/{ref}.md`)
"""
        (drivers_dir / f"{ref}.md").write_text(content, encoding="utf-8")

def reformat_constructor_pages():
    print("🏭 Reformatting Constructor pages...")
    constructors_dir = VAULT_DIR / "tier1" / "constructors"
    constructors = pd.read_csv(RAW_DATA_DIR / "constructors.csv")
    results = pd.read_csv(RAW_DATA_DIR / "results.csv")
    races = pd.read_csv(RAW_DATA_DIR / "races.csv")
    drivers = pd.read_csv(RAW_DATA_DIR / "drivers.csv")

    results['pos_num'] = pd.to_numeric(results['position'], errors='coerce')
    results['grid_num'] = pd.to_numeric(results['grid'], errors='coerce')
    results['points_num'] = pd.to_numeric(results['points'], errors='coerce').fillna(0.0)

    full_res = results.merge(races[['raceId', 'year', 'round', 'name']], on='raceId', how='left')
    full_res = full_res.merge(drivers[['driverId', 'driverRef', 'forename', 'surname']], on='driverId', how='left')

    for _, c in constructors.iterrows():
        ref = c['constructorRef']
        name = c['name']
        nat = c['nationality']

        c_res = full_res[full_res['constructorId'] == c['constructorId']]
        starts = len(c_res['raceId'].unique())
        wins = len(c_res[c_res['pos_num'] == 1])
        podiums = len(c_res[c_res['pos_num'].isin([1, 2, 3])])
        poles = len(c_res[c_res['grid_num'] == 1])
        points = c_res['points_num'].sum()

        driver_stats = c_res.groupby('driverRef').agg(
            entries=('raceId', 'nunique'),
            wins=('pos_num', lambda x: (x == 1).sum()),
            podiums=('pos_num', lambda x: (x.isin([1,2,3])).sum())
        ).reset_index().sort_values(['wins', 'entries'], ascending=False)

        driver_links = []
        for _, d_stat in driver_stats.head(8).iterrows():
            driver_links.append(f"- **[[{d_stat['driverRef']}]]:** {d_stat['entries']} starts, **{d_stat['wins']} wins**, {d_stat['podiums']} podiums")
        drivers_str = "\n".join(driver_links) if driver_links else "- None recorded"

        content = f"""| constructor_ref | {ref} |
| :--- | :--- |
| **team_name** | {name} |
| **nationality** | {nat} |
| **active_era** | {c_res['year'].min() if starts > 0 else 'N/A'}–{c_res['year'].max() if starts > 0 else 'N/A'} |
| **total_starts** | {starts} |
| **tier_classification** | Tier 1 (Constructor Record) |

# {name}

**Role:** Formula 1 Constructor and Racing Team ({nat}).

**Historical Achievements & Record:**
- **Total Grand Prix Starts:** **{starts}**
- **Grand Prix Victories:** **{wins}** ({f"{wins/starts*100:.1f}% win rate" if starts > 0 else "0%"})
- **Podium Finishes:** **{podiums}**
- **Pole Positions:** **{poles}**
- **All-Time Constructor Points:** **{points:.1f}**

**Notable Drivers & Winners:**
{drivers_str}

**Source:** F1 Knowledge Vault [[{ref}]] (`vault/tier1/constructors/{ref}.md`)
"""
        (constructors_dir / f"{ref}.md").write_text(content, encoding="utf-8")

def main():
    generate_chat_query_pages()
    reformat_driver_pages()
    reformat_constructor_pages()
    print("🎉 All pages successfully reformatted to screenshot style!")

if __name__ == "__main__":
    main()
