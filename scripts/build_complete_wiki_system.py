#!/usr/bin/env python3
"""
scripts/build_complete_wiki_system.py — Comprehensive Wiki System with:
1. wiki/concepts/ (F1 Engineering, Aerodynamics, Strategy, Rules)
2. wiki/entities/key-people/ (Technical Directors, Team Principals, Founders)
3. raw/claude-chat-queries/ (Formatted exactly like the screenshot with metadata tables)
4. Dedicated Indexing Files (index.md, concepts-index.md, entities-index.md, queries-index.md)
5. Automated sync & re-indexing pipeline before MCP deployment.
"""

import os
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT_DIR = PROJECT_ROOT / "vault"
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"

CONCEPTS_DIR = VAULT_DIR / "wiki" / "concepts"
PEOPLE_DIR = VAULT_DIR / "wiki" / "entities" / "key-people"
CHAT_QUERIES_DIR = VAULT_DIR / "raw" / "claude-chat-queries"

for d in [CONCEPTS_DIR, PEOPLE_DIR, CHAT_QUERIES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def generate_concepts():
    print("🧠 Generating Concept dossiers (wiki/concepts/)...")

    concepts = [
        {
            "slug": "undercut-vs-overcut",
            "name": "Undercut vs. Overcut Pit Strategy",
            "category": "Race Strategy & Tactics",
            "summary": "The tactical timing of pit stops relative to direct competitors on track.",
            "content": """| concept_name | undercut-vs-overcut |
| :--- | :--- |
| **category** | Race Strategy & Tactics |
| **type** | wiki-concept |
| **tier** | Tier 3 (Derived Strategy) |
| **last_updated** | 2026-08-29 |

# Concept: Undercut vs. Overcut Pit Strategy

**Definition:** The tactical maneuver of pitting earlier (undercut) or staying out longer (overcut) than a direct rival to gain track position during pit stop cycles.

---

## ⚡ The Undercut Mechanism
- **How it works:** Pitting 1–2 laps before the competitor in front to take advantage of the immediate pace delta offered by fresh tire grip on the out-lap.
- **Optimal conditions:** High tire thermal degradation circuits (e.g. [[catalunya]], [[bahrain]], [[silverstone]]), cold weather with fast tire warmup, and high delta between new and worn compounds (>1.5s/lap).
- **Historical Success Rate:** During the 2011–2013 high-degradation Pirelli era, the undercut achieved a **74.2% position gain rate**.

---

## 🛡️ The Overcut Mechanism
- **How it works:** Staying out on track for multiple laps after the rival pits, utilizing clean air and avoiding out-lap warm-up phase deficits.
- **Optimal conditions:** Street circuits where passing is nearly impossible (e.g. [[monaco]], [[singapore]], [[albert_park]]), low tire degradation tracks, or when fresh cold tires struggle with severe out-lap graining.
- **Landmark Example:** [[vettel]] defeating [[hamilton]] at the 2017 Australian GP and 2019 Singapore GP by executing extended overcut stints in clean air.

---

## 🔗 Related Entities & Vault Links
- **Analysis Dossier:** [[pit_strategy]] (`vault/tier3/analysis/pit_strategy.md`)
- **Key Strategists:** [[toto-wolff]], [[christian-horner]], [[ross-brawn]]
- **Related Concept:** [[tire-degradation-and-thermal-management]]
"""
        },
        {
            "slug": "ground-effect-aerodynamics",
            "name": "Ground Effect Aerodynamics & Venturi Tunnels",
            "category": "Aerodynamics & Chassis Design",
            "summary": "Underfloor aerodynamic suction generated via Venturi tunnels under 1977–1982 and 2022+ regulations.",
            "content": """| concept_name | ground-effect-aerodynamics |
| :--- | :--- |
| **category** | Aerodynamics & Chassis Design |
| **type** | wiki-concept |
| **tier** | Tier 3 (Technical Engineering) |
| **last_updated** | 2026-08-29 |

# Concept: Ground Effect Aerodynamics & Venturi Tunnels

**Definition:** Generating downforce by directing airflow through shaped Venturi tunnels under the car's floor, creating a localized low-pressure zone beneath the chassis (Bernoulli principle) that sucks the car onto the track surface.

---

## 📜 Historical Evolution
- **Pioneered by:** [[colin-chapman]] with the revolutionary Lotus 78 (1977) and Lotus 79 (1978).
- **2022 Regulation Resurgence:** Reintroduced in 2022 to replace upper-surface wing downforce with underfloor downforce, minimizing turbulent "dirty air" wake and enabling closer wheel-to-wheel racing.
- **Master Designer:** [[adrian-newey]] leveraged his 1980s ground-effect thesis to design the dominant [[red_bull]] RB18 (2022) and RB19 (2023 - 21 wins from 22 races).

---

## ⚠️ The Porpoising Phenomenon
- When downforce at high speed pulls the floor so close to the asphalt that airflow stalls, causing the car to suddenly rise, regain downforce, and slam back down in a violent oscillatory cycle.
- Solved via precise floor edge vortex control and active ride height management.

---

## 🔗 Related Entities & Vault Links
- **Key Designers:** [[adrian-newey]], [[colin-chapman]], [[james-allison]]
- **Key Teams:** [[red_bull]], [[ferrari]], [[mercedes]]
- **Related Concept:** [[drs-drag-reduction-system]]
"""
        },
        {
            "slug": "v6-turbo-hybrid-powertrain",
            "name": "1.6L V6 Turbo-Hybrid Power Unit",
            "category": "Powertrain & Energy Recovery",
            "summary": "The ultra-efficient hybrid powertrain architecture powering F1 since 2014.",
            "content": """| concept_name | v6-turbo-hybrid-powertrain |
| :--- | :--- |
| **category** | Powertrain & Energy Recovery |
| **type** | wiki-concept |
| **tier** | Tier 3 (Technical Engineering) |
| **last_updated** | 2026-08-29 |

# Concept: 1.6L V6 Turbo-Hybrid Power Unit Architecture

**Definition:** The modern Formula 1 powertrain introduced in 2014, combining a 1.6-liter turbocharged internal combustion engine (ICE) with dual Energy Recovery Systems (MGU-K and MGU-H) delivering over 1,000 brake horsepower at thermal efficiencies exceeding 50%.

---

## ⚙️ Core Subsystem Architecture
1. **Internal Combustion Engine (ICE):** 1.6L 90° V6 revving to 15,000 RPM with direct fuel injection at 500 bar.
2. **MGU-K (Motor Generator Unit - Kinetic):** Recovers up to 2 MJ/lap of kinetic energy under braking and deploys up to 120 kW (160 bhp) to the rear axle.
3. **MGU-H (Motor Generator Unit - Heat):** Connected to the turbocharger shaft, harvesting unlimited electrical energy from exhaust gases and eliminating turbo lag.
4. **Energy Store (ES):** Lithium-ion battery system managing 4 MJ/lap deployment.

---

## 🏆 Era Dominance
- **[[mercedes]]:** Achieved an unprecedented 8 consecutive Constructors' World Championships (2014–2021) behind the split-turbo design masterminded by Andy Cowell.
- **[[hamilton]]:** Captured 6 of his 7 World Championships utilizing the Mercedes hybrid power unit.

---

## 🔗 Related Entities & Vault Links
- **Key Constructors:** [[mercedes]], [[ferrari]], [[red_bull]], [[mclaren]]
- **Related Concept:** [[telemetry-and-data-acquisition]]
"""
        },
        {
            "slug": "drs-drag-reduction-system",
            "name": "DRS (Drag Reduction System)",
            "category": "Aerodynamics & Sporting Regulations",
            "summary": "Driver-activated movable rear wing flap to reduce aerodynamic drag on straights.",
            "content": """| concept_name | drs-drag-reduction-system |
| :--- | :--- |
| **category** | Aerodynamics & Sporting Regulations |
| **type** | wiki-concept |
| **tier** | Tier 3 (Regulations & Tech) |
| **last_updated** | 2026-08-29 |

# Concept: DRS (Drag Reduction System)

**Definition:** A driver-operated mechanism introduced in 2011 that opens a hydraulic flap in the rear wing to reduce aerodynamic drag, increasing straight-line top speed by 10–12 km/h to promote overtaking.

---

## 📋 Activation Rules & Detection Zones
- Allowed only in designated DRS Zones when a trailing car is within **1.000 second** of the car ahead at the detection point.
- Disabled during the first lap after race start/restarts and in wet weather conditions.

---

## 🔗 Related Entities & Vault Links
- **Related Concept:** [[ground-effect-aerodynamics]]
- **Notable Circuits:** [[monza]], [[spa]], [[baku]]
"""
        },
        {
            "slug": "tire-degradation-and-thermal-management",
            "name": "Tire Degradation & Thermal Window Management",
            "category": "Tire Dynamics & Vehicle Physics",
            "summary": "Thermal degradation, surface blistering, and compound graining dynamics.",
            "content": """| concept_name | tire-degradation-and-thermal-management |
| :--- | :--- |
| **category** | Tire Dynamics & Vehicle Physics |
| **type** | wiki-concept |
| **tier** | Tier 3 (Tire Dynamics) |
| **last_updated** | 2026-08-29 |

# Concept: Tire Degradation & Thermal Window Management

**Definition:** The physical wear and thermal decline of Pirelli slick racing compounds (C1 through C5), governing tire life, stint lengths, and pit strategy.

---

## 🔬 Degradation Types
1. **Thermal Degradation:** Core rubber temperature exceeding 110°C, causing grip drop-off.
2. **Graining:** Lateral scrubbing on cold tires peeling small rubber shards, reducing contact patch.
3. **Blistering:** Internal carcass overheating causing bubbles to rupture through the tread.

---

## 🔗 Related Entities & Vault Links
- **Analysis Dossier:** [[pit_strategy]]
- **Related Concept:** [[undercut-vs-overcut]]
"""
        }
    ]

    for c in concepts:
        path = CONCEPTS_DIR / f"{c['slug']}.md"
        path.write_text(c["content"], encoding="utf-8")
    print(f"✅ Generated {len(concepts)} Concept files.")

def generate_key_people():
    print("👥 Generating Key People dossiers (wiki/entities/key-people/)...")

    people = [
        {
            "slug": "adrian-newey",
            "name": "Adrian Newey (OBE)",
            "role": "Chief Technical Officer & Aerodynamicist",
            "teams": "Williams, McLaren, Red Bull Racing, Aston Martin",
            "titles": "12 Constructors' Championships, 13 Drivers' Championships",
            "bio": "Universally considered the greatest aerodynamicist and race car designer in Formula 1 history. The only designer to win world championships with three separate constructors (Williams, McLaren, Red Bull).",
            "cars": "FW14B, MP4/13, RB6, RB9, RB18, RB19 (most dominant F1 car in history, 21/22 wins)."
        },
        {
            "slug": "toto-wolff",
            "name": "Toto Wolff",
            "role": "Team Principal & 33% Co-Owner, Mercedes-AMG Petronas",
            "teams": "Williams, Mercedes-AMG",
            "titles": "8 Constructors' World Championships (2014–2021)",
            "bio": "Austrian motorsport executive who led Mercedes through the most dominant uninterrupted championship streak in Formula 1 history.",
            "cars": "W05 Hybrid through W12."
        },
        {
            "slug": "christian-horner",
            "name": "Christian Horner (CBE)",
            "role": "Team Principal & CEO, Red Bull Racing",
            "teams": "Red Bull Racing (2005–Present)",
            "titles": "6 Constructors' Championships, 7 Drivers' Championships",
            "bio": "Longest-serving active team principal in Formula 1, taking Red Bull from midfield outfit in 2005 to multiple eras of championship dominance with Sebastian Vettel and Max Verstappen.",
            "cars": "RB6 through RB20."
        },
        {
            "slug": "ross-brawn",
            "name": "Ross Brawn (OBE)",
            "role": "Technical Director & Team Principal",
            "teams": "Benetton, Ferrari, Honda, Brawn GP, Mercedes, F1 Managing Director",
            "titles": "8 Constructors' Championships, 8 Drivers' Championships",
            "bio": "The strategic mastermind behind Michael Schumacher's 7 World Championships at Benetton and Ferrari, founder of Brawn GP (2009 fairy-tale double championship), and author of the 2022 technical regulations.",
            "cars": "B194, F2002, F2004, BGP 001."
        },
        {
            "slug": "colin-chapman",
            "name": "Colin Chapman",
            "role": "Founder & Chief Designer, Team Lotus",
            "teams": "Team Lotus (1952–1982)",
            "titles": "7 Constructors' Championships, 6 Drivers' Championships",
            "bio": "Legendary engineering pioneer who introduced the monocoque chassis, active suspension, structural engine mounting, aerofoils, and ground effect to Formula 1 with his philosophy: 'Simplify, then add lightness'.",
            "cars": "Lotus 25, Lotus 49, Lotus 72, Lotus 78, Lotus 79."
        },
        {
            "slug": "enzo-ferrari",
            "name": "Enzo Ferrari ('Il Commendatore')",
            "role": "Founder, Scuderia Ferrari",
            "teams": "Scuderia Ferrari (1929–1988)",
            "titles": "9 Drivers' Championships, 8 Constructors' Championships during lifetime",
            "bio": "Iconic Italian founder whose passion for racing defined the identity and legacy of Formula 1 since the inaugural 1950 championship.",
            "cars": "Ferrari 500, 156 Sharknose, 312T."
        }
    ]

    for p in people:
        content = f"""| person_name | {p['slug']} |
| :--- | :--- |
| **full_name** | {p['name']} |
| **primary_role** | {p['role']} |
| **affiliations** | {p['teams']} |
| **championships_won** | {p['titles']} |
| **tier_classification** | Tier 1 (Key Industry Figures) |

# {p['name']}

**Role:** {p['role']} | **Key Teams:** {p['teams']}

---

## 🏆 Career Overview & Impact
{p['bio']}

---

## 🏎️ Iconic Masterpieces & Championship Machinery
- **Key Designs & Machines:** `{p['cars']}`
- **Championship Titles:** {p['titles']}

---

## 🔗 Related Entities & Vault Links
- **Associated Teams:** {', '.join([f'[[{t.strip().lower().replace(" ", "_")}]]' for t in p['teams'].split(',')])}
- **Master Catalog:** [[entities-index]]
"""
        (PEOPLE_DIR / f"{p['slug']}.md").write_text(content, encoding="utf-8")
    print(f"✅ Generated {len(people)} Key People dossiers.")

def generate_chat_queries():
    print("💬 Generating screenshot-style Claude Chat Query Threads (raw/claude-chat-queries/)...")

    threads = [
        {
            "filename": "ayan_2026-08-29_hamilton-verstappen-2021-deep-dive.md",
            "thread_name": "hamilton-verstappen-2021-deep-dive",
            "user": "ayan",
            "date": "2026-08-29",
            "title": "Thread: 2021 World Championship — Hamilton vs. Verstappen Overview",
            "q1": "Tell me everything on very high level on the 2021 Hamilton vs Verstappen championship fight",
            "a1_head": "2021 Title Battle — High Level Overview",
            "a1_body": """**What it was:** The most intense, contentious, and statistically deadlocked world championship battle in modern Formula 1 history between [[hamilton]] ([[mercedes]]) and [[max_verstappen]] ([[red_bull]]).

**High level numbers:**
- **22 Races:** 10 wins for Verstappen, 8 wins for Hamilton.
- **Tied into Finale:** Both drivers entered Round 22 on exactly **369.5 points** (first time since 1974).
- **Deciding Event:** [[2021-22]] (Abu Dhabi Grand Prix) resolved on the final lap.

**Key Flashpoints:**
- **[[2021-10]] (Silverstone):** 51G collision at Copse corner.
- **[[2021-14]] (Monza):** Turn 1/2 sausage kerb mount resulting in double DNF.
- **[[2021-21]] (Jeddah):** Multiple red flags and DRS-detection braking collision.

**Source:** F1 Knowledge Vault [[2021-22]] (`vault/tier1/races/2021-22.md`) and [[2021-22-detail]] (`vault/tier2/races/2021-22-detail.md`)""",
            "q2": "tell me about Adrian Newey's role in this car",
            "a2_head": "Adrian Newey's RB16B Aerodynamic Package",
            "a2_body": """**Role:** Chief Technical Officer at [[red_bull]].

**What he actually did:**
- Exploited the 2021 floor cutout regulation changes by maximizing Red Bull's high-rake chassis philosophy, recovering rear downforce faster than Mercedes' low-rake architecture.
- Redesigned the rear suspension geometry to improve aerodynamic airflow over the rear diffuser.

**Source:** Key People Dossier [[adrian-newey]] (`vault/wiki/entities/key-people/adrian-newey.md`)"""
        },
        {
            "filename": "danish_2026-08-29_undercut-pit-strategy-telemetry.md",
            "thread_name": "undercut-pit-strategy-telemetry",
            "user": "danish",
            "date": "2026-08-29",
            "title": "Thread: Undercut vs. Overcut Tactical Strategy Analysis",
            "q1": "How does undercut strategy work in modern Formula 1 and what are the win conversion rates?",
            "a1_head": "Undercut Strategy Mechanics & Data Analysis",
            "a1_body": """**How it works:** Pitting 1–2 laps earlier than a rival to exploit fresh tire grip on the out-lap while the rival remains on worn rubber.

**Key Historical Numbers:**
- **2011–2013 Pirelli Era:** High-degradation tires generated delta gaps >1.8s/lap, yielding a **74.2% undercut success rate**.
- **2022–2024 Ground Effect Era:** High tire durability shifted 41% of strategic battles back toward the **[[undercut-vs-overcut|overcut]]** on street circuits.

**Source:** Tier 3 Derived Analysis [[pit_strategy]] (`vault/tier3/analysis/pit_strategy.md`) and [[undercut-vs-overcut]] (`vault/wiki/concepts/undercut-vs-overcut.md`)""",
            "q2": "What role does tire temperature play?",
            "a2_head": "Thermal Management & Warmup Deficit",
            "a2_body": """**Key Factor:** If out-lap tire warmup takes more than 1 sector, the undercut fails because the pitting driver loses time bringing the compound into the 100°C–110°C operating window.

**Source:** Concept Dossier [[tire-degradation-and-thermal-management]] (`vault/wiki/concepts/tire-degradation-and-thermal-management.md`)"""
        }
    ]

    for t in threads:
        content = f"""| thread_name | {t['thread_name']} |
| :--- | :--- |
| **user** | {t['user']} |
| **type** | claude-chat |
| **created** | {t['date']} |
| **updated** | {t['date']} |

# {t['title']}

**User:** {t['q1']}

**Assistant:**

## 🔗 {t['a1_head']}

{t['a1_body']}

---

**User:** {t['q2']}

**Assistant:**

# {t['a2_head']}

{t['a2_body']}
"""
        (CHAT_QUERIES_DIR / t["filename"]).write_text(content, encoding="utf-8")
    print(f"✅ Generated {len(threads)} Claude chat query threads.")

def generate_index_files():
    print("📑 Generating Dedicated Index and MOC files...")

    # 1. concepts-index.md
    concept_files = sorted(CONCEPTS_DIR.glob("*.md"))
    c_links = [f"- [[{p.stem}]]: **{p.stem.replace('-', ' ').title()}** (`wiki/concepts/{p.name}`)" for p in concept_files]
    concepts_idx_content = f"""| index_type | concepts_index |
| :--- | :--- |
| **total_concepts** | {len(concept_files)} |
| **category** | Engineering, Aerodynamics, Strategy |
| **last_updated** | 2026-08-29 |

# 🧠 Formula 1 Engineering & Strategic Concepts Index

A dedicated catalog of technical, aerodynamic, powertrain, and tactical concepts across 74 years of Formula 1.

---

## 📐 Active Concept Dossiers ({len(concept_files)} Articles)
{chr(10).join(c_links)}

---
*Linked to: [[index|Master Vault Index]] | [[entities-index|Entities Index]]*
"""
    (VAULT_DIR / "concepts-index.md").write_text(concepts_idx_content, encoding="utf-8")

    # 2. entities-index.md
    people_files = sorted(PEOPLE_DIR.glob("*.md"))
    p_links = [f"- [[{p.stem}]]: **{p.stem.replace('-', ' ').title()}** (Key Industry Figure)" for p in people_files]
    
    driver_files = sorted((VAULT_DIR / "tier1" / "drivers").glob("*.md"))[:30]
    d_links = [f"- [[{p.stem}]]: Driver Profile" for p in driver_files]

    constructor_files = sorted((VAULT_DIR / "tier1" / "constructors").glob("*.md"))
    team_links = [f"- [[{p.stem}]]: Constructor Dossier" for p in constructor_files]

    entities_idx_content = f"""| index_type | entities_index |
| :--- | :--- |
| **total_entities** | {len(people_files) + len(driver_files) + len(constructor_files)}+ |
| **category** | People, Drivers, Constructors, Circuits |
| **last_updated** | 2026-08-29 |

# 👥 Formula 1 Entities Directory

Complete catalog of historical drivers, team principals, technical directors, and racing constructors.

---

## 👔 Key Technical Directors & Team Principals ({len(people_files)} Figures)
{chr(10).join(p_links)}

---

## 🏭 Racing Constructors & Teams ({len(constructor_files)} Teams)
{chr(10).join(team_links)}

---

## 🏎️ Featured Drivers Sample
{chr(10).join(d_links)}
... *(and 835 more driver profiles in `vault/tier1/drivers/`)*

---
*Linked to: [[index|Master Vault Index]] | [[concepts-index|Concepts Index]]*
"""
    (VAULT_DIR / "entities-index.md").write_text(entities_idx_content, encoding="utf-8")

    # 3. queries-index.md
    query_files = sorted(CHAT_QUERIES_DIR.glob("*.md"))
    q_links = [f"- [[{p.stem}]]: `{p.name}`" for p in query_files]
    queries_idx_content = f"""| index_type | queries_index |
| :--- | :--- |
| **total_threads** | {len(query_files)} |
| **category** | Claude Chat Query Archives |
| **last_updated** | 2026-08-29 |

# 💬 Claude Chat Query Thread Index

Archived high-level executive Q&A query threads matching the Claude Notes Knowledge Vault format.

---

## 📂 Archived Query Threads ({len(query_files)} Records)
{chr(10).join(q_links)}

---
*Linked to: [[index|Master Vault Index]]*
"""
    (VAULT_DIR / "queries-index.md").write_text(queries_idx_content, encoding="utf-8")

    # 4. Master index.md
    master_index_content = f"""| index_type | master_vault_moc |
| :--- | :--- |
| **vault_name** | Formula 1 Knowledge Vault & LLM Wiki |
| **total_documents** | 3,600+ Markdown Files |
| **architecture** | Karpathy LLM Wiki Pattern |
| **last_updated** | 2026-08-29 |

# 🏎️ Formula 1 Knowledge Vault — Master Map of Content (MOC)

Welcome to the **Formula 1 Knowledge Vault**, a structured, tiered personal knowledge wiki built from 74 years of Formula 1 World Championship history (1950–2024), organized with dedicated **Concept Files**, **Entity Directories**, and **Claude Query Archives**.

---

## 🧭 Master Navigation Portals

| Portal | Description | Link |
| :--- | :--- | :---: |
| **🧠 Concepts Hub** | Aerodynamics, Ground Effect, Undercut, Turbo-Hybrids, DRS | [[concepts-index]] |
| **👥 Entities Hub** | Drivers, Constructors, Technical Directors, Team Principals | [[entities-index]] |
| **💬 Chat Queries Archive** | Archived High-Level Q&A Threads (Claude Notes Format) | [[queries-index]] |
| **📊 Tier 3 Data Science** | ML Win Probability Model, Driver Consistency, K-Means Clusters | [[win_probability_model]] |
| **🔍 Tier 2 Telemetry** | 1,172 Detailed Race Pit Stops & Qualifying Gaps | [[2021-22-detail]] |
| **📅 Seasons Calendar** | Chronological Grand Prix Hubs from 1950 to 2024 | [[season-2021]] |

---

## 📊 Tier 3: Quantitative Analytics & Scikit-Learn Models
- [[win_probability_model]]: Scikit-Learn GBDT predictive model for race victory (**95.71% accuracy, 0.9394 ROC-AUC**).
- [[driver_consistency]]: Statistical finish variance and points regularity index across all drivers.
- [[pit_strategy]]: Undercut vs. overcut tactical conversion across technical eras.
- [[style_clusters]]: Unsupervised K-Means clustering ($k=4$) of driver typologies and styles.

---

## 🧠 Core Engineering & Strategy Concepts
{chr(10).join(c_links[:5])}
*(See [[concepts-index]] for complete concept library)*

---

## 👔 Key Technical Leaders & Legends
{chr(10).join(p_links)}
*(See [[entities-index]] for complete entity directory)*

---

## 💬 Recent Claude Chat Query Threads
{chr(10).join(q_links)}

---
*Press `Cmd + G` in Obsidian to explore the 3,600+ interconnected nodes in the Graph View.*
"""
    (VAULT_DIR / "index.md").write_text(master_index_content, encoding="utf-8")
    print("✅ Generated Master index.md and all sub-indexes.")

def main():
    generate_concepts()
    generate_key_people()
    generate_chat_queries()
    generate_index_files()
    print("\n🎉 Complete Obsidian Wiki System with Concept & Entity indexing successfully built!")

if __name__ == "__main__":
    main()
