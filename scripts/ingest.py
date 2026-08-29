#!/usr/bin/env python3
"""
scripts/ingest.py — Ingest raw Formula 1 CSVs and build Obsidian-compatible Vault.
Follows Andrej Karpathy's 'LLM Wiki' pattern:
- Ingest raw sources once
- Write persistent interlinked markdown pages with [[wikilinks]]
- No live re-fetching at query time
- Deterministic, idempotent updates in place
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"
VAULT_DIR = PROJECT_ROOT / "vault"

TIER1_DIR = VAULT_DIR / "tier1"
TIER2_DIR = VAULT_DIR / "tier2"
TIER3_DIR = VAULT_DIR / "tier3"

DRIVERS_DIR = TIER1_DIR / "drivers"
CONSTRUCTORS_DIR = TIER1_DIR / "constructors"
CIRCUITS_DIR = TIER1_DIR / "circuits"
RACES_DIR = TIER1_DIR / "races"
RACES_DETAIL_DIR = TIER2_DIR / "races"
ANALYSIS_DIR = TIER3_DIR / "analysis"

def load_data():
    print("📂 Loading raw CSV datasets...")
    circuits = pd.read_csv(RAW_DATA_DIR / "circuits.csv")
    constructors = pd.read_csv(RAW_DATA_DIR / "constructors.csv")
    drivers = pd.read_csv(RAW_DATA_DIR / "drivers.csv")
    races = pd.read_csv(RAW_DATA_DIR / "races.csv")
    results = pd.read_csv(RAW_DATA_DIR / "results.csv")
    status = pd.read_csv(RAW_DATA_DIR / "status.csv")
    
    # Optional / large datasets
    qualifying = pd.read_csv(RAW_DATA_DIR / "qualifying.csv") if (RAW_DATA_DIR / "qualifying.csv").exists() else pd.DataFrame()
    pit_stops = pd.read_csv(RAW_DATA_DIR / "pit_stops.csv") if (RAW_DATA_DIR / "pit_stops.csv").exists() else pd.DataFrame()
    lap_times = pd.read_csv(RAW_DATA_DIR / "lap_times.csv") if (RAW_DATA_DIR / "lap_times.csv").exists() else pd.DataFrame()
    driver_standings = pd.read_csv(RAW_DATA_DIR / "driver_standings.csv") if (RAW_DATA_DIR / "driver_standings.csv").exists() else pd.DataFrame()
    constructor_standings = pd.read_csv(RAW_DATA_DIR / "constructor_standings.csv") if (RAW_DATA_DIR / "constructor_standings.csv").exists() else pd.DataFrame()

    # Preprocess numeric fields
    results['pos_num'] = pd.to_numeric(results['position'], errors='coerce')
    results['grid_num'] = pd.to_numeric(results['grid'], errors='coerce')
    results['points_num'] = pd.to_numeric(results['points'], errors='coerce').fillna(0.0)
    
    if not driver_standings.empty:
        driver_standings['pos_num'] = pd.to_numeric(driver_standings['position'], errors='coerce')
        driver_standings['points_num'] = pd.to_numeric(driver_standings['points'], errors='coerce')
    
    if not constructor_standings.empty:
        constructor_standings['pos_num'] = pd.to_numeric(constructor_standings['position'], errors='coerce')
        constructor_standings['points_num'] = pd.to_numeric(constructor_standings['points'], errors='coerce')

    return {
        "circuits": circuits,
        "constructors": constructors,
        "drivers": drivers,
        "races": races,
        "results": results,
        "status": status,
        "qualifying": qualifying,
        "pit_stops": pit_stops,
        "lap_times": lap_times,
        "driver_standings": driver_standings,
        "constructor_standings": constructor_standings
    }

def build_vault(data):
    # Ensure all directories exist
    for d in [DRIVERS_DIR, CONSTRUCTORS_DIR, CIRCUITS_DIR, RACES_DIR, RACES_DETAIL_DIR, ANALYSIS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    races = data["races"]
    results = data["results"]
    drivers = data["drivers"]
    constructors = data["constructors"]
    circuits = data["circuits"]
    status_df = data["status"]
    qualifying = data["qualifying"]
    pit_stops = data["pit_stops"]
    driver_standings = data["driver_standings"]
    constructor_standings = data["constructor_standings"]

    # Pre-calculate Championships
    # Drivers Championship: Max round per year in driver_standings with pos_num == 1
    driver_titles = {}
    if not driver_standings.empty:
        races_with_ds = races[races['raceId'].isin(driver_standings['raceId'])]
        max_ds_rounds = races_with_ds.groupby('year')['round'].max().reset_index()
        final_ds_races = pd.merge(races, max_ds_rounds, on=['year', 'round'])
        champ_ds = driver_standings[(driver_standings['raceId'].isin(final_ds_races['raceId'])) & (driver_standings['pos_num'] == 1)]
        for _, row in champ_ds.iterrows():
            d_id = int(row['driverId'])
            y = int(races.loc[races['raceId'] == row['raceId'], 'year'].values[0])
            driver_titles.setdefault(d_id, []).append(y)

    # Constructors Championship
    constructor_titles = {}
    if not constructor_standings.empty:
        races_with_cs = races[races['raceId'].isin(constructor_standings['raceId'])]
        max_cs_rounds = races_with_cs.groupby('year')['round'].max().reset_index()
        final_cs_races = pd.merge(races, max_cs_rounds, on=['year', 'round'])
        champ_cs = constructor_standings[(constructor_standings['raceId'].isin(final_cs_races['raceId'])) & (constructor_standings['pos_num'] == 1)]
        for _, row in champ_cs.iterrows():
            c_id = int(row['constructorId'])
            y = int(races.loc[races['raceId'] == row['raceId'], 'year'].values[0])
            constructor_titles.setdefault(c_id, []).append(y)

    # Merge results with races, drivers, constructors for fast lookup
    full_results = results.merge(races[['raceId', 'year', 'round', 'name', 'date', 'circuitId']], on='raceId', how='left')
    full_results = full_results.merge(drivers[['driverId', 'driverRef', 'forename', 'surname', 'nationality', 'code', 'number']], on='driverId', how='left')
    full_results = full_results.merge(constructors[['constructorId', 'constructorRef', 'name']], on='constructorId', how='left', suffixes=('', '_constructor'))
    full_results = full_results.merge(status_df, on='statusId', how='left')

    index_entries = {
        "drivers": [],
        "constructors": [],
        "circuits": [],
        "races_tier1": [],
        "races_tier2": [],
        "analysis_tier3": []
    }

    files_written = 0

    print("🏎️  Generating Driver Pages (Tier 1)...")
    for _, d in drivers.iterrows():
        d_id = d['driverId']
        ref = d['driverRef']
        name = f"{d['forename']} {d['surname']}"
        nat = d['nationality']
        dob = d['dob']
        code = d['code'] if pd.notna(d['code']) and d['code'] != r'\N' else "N/A"
        num = d['number'] if pd.notna(d['number']) and d['number'] != r'\N' else "N/A"

        d_res = full_results[full_results['driverId'] == d_id]
        entries = len(d_res)
        wins = len(d_res[d_res['pos_num'] == 1])
        podiums = len(d_res[d_res['pos_num'].isin([1, 2, 3])])
        poles = len(d_res[d_res['grid_num'] == 1])
        points = d_res['points_num'].sum()
        
        titles = driver_titles.get(d_id, [])
        titles_str = f"**{len(titles)}** ({', '.join(map(str, sorted(titles)))})" if titles else "0"

        # Teams driven for
        team_counts = d_res.groupby('constructorRef')['year'].agg(['min', 'max', 'count']).reset_index()
        team_links = []
        for _, t in team_counts.iterrows():
            era_str = f"{t['min']}" if t['min'] == t['max'] else f"{t['min']}–{t['max']}"
            team_links.append(f"- [[{t['constructorRef']}]] ({era_str}, {t['count']} entries)")

        teams_block = "\n".join(team_links) if team_links else "- None recorded"

        # Key Victories (up to 10)
        win_races = d_res[d_res['pos_num'] == 1].sort_values(['year', 'round'])
        victories_list = []
        for _, w in win_races.head(10).iterrows():
            race_code = f"{w['year']}-{int(w['round']):02d}"
            victories_list.append(f"- [[{race_code}]] ({w['year']} {w['name']}) with [[{w['constructorRef']}]]")
        
        victories_block = "\n".join(victories_list) if victories_list else "- No Grand Prix wins"

        content = f"""# {name}

**Nationality:** {nat} | **Born:** {dob} | **Driver Code:** `{code}` | **Permanent #:** `{num}`

---

## 🏆 Career Summary
- **World Championships:** {titles_str}
- **Total Grand Prix Entries:** {entries}
- **Victories:** {wins} ({round(wins / entries * 100, 1) if entries > 0 else 0}%)
- **Podiums:** {podiums}
- **Pole Positions:** {poles}
- **Career Points:** {points:.1f}

---

## 🏎️ Constructors & Teams
{teams_block}

---

## 🏁 Selected Victories & Milestones
{victories_block}

---
*Classification: Tier 1 (Public Career Statistics & Bio)*
"""
        filepath = DRIVERS_DIR / f"{ref}.md"
        filepath.write_text(content, encoding="utf-8")
        files_written += 1
        index_entries["drivers"].append(f"- [[{ref}]]: {name} ({nat}) — {titles_str} Championships, {wins} Wins, {podiums} Podiums")

    print("🏭 Generating Constructor Pages (Tier 1)...")
    for _, c in constructors.iterrows():
        c_id = c['constructorId']
        ref = c['constructorRef']
        name = c['name']
        nat = c['nationality']

        c_res = full_results[full_results['constructorId'] == c_id]
        entries = len(c_res['raceId'].unique())
        wins = len(c_res[c_res['pos_num'] == 1])
        podiums = len(c_res[c_res['pos_num'].isin([1, 2, 3])])
        poles = len(c_res[c_res['grid_num'] == 1])
        points = c_res['points_num'].sum()
        
        titles = constructor_titles.get(c_id, [])
        titles_str = f"**{len(titles)}** ({', '.join(map(str, sorted(titles)))})" if titles else "0"

        # Notable Drivers
        driver_stats = c_res.groupby('driverRef').agg(
            entries=('raceId', 'nunique'),
            wins=('pos_num', lambda x: (x == 1).sum()),
            podiums=('pos_num', lambda x: (x.isin([1,2,3])).sum())
        ).reset_index().sort_values(['wins', 'entries'], ascending=False)

        driver_links = []
        for _, d_stat in driver_stats.head(8).iterrows():
            driver_links.append(f"- [[{d_stat['driverRef']}]]: {d_stat['entries']} races, {d_stat['wins']} wins, {d_stat['podiums']} podiums")
        
        drivers_block = "\n".join(driver_links) if driver_links else "- None recorded"

        content = f"""# {name}

**Nationality:** {nat} | **First Entry:** {c_res['year'].min() if entries > 0 else 'N/A'} | **Latest Entry:** {c_res['year'].max() if entries > 0 else 'N/A'}

---

## 🏆 Team Achievements
- **Constructors' Championships:** {titles_str}
- **Total Grand Prix Starts:** {entries}
- **Grand Prix Victories:** {wins}
- **Podiums:** {podiums}
- **Pole Positions:** {poles}
- **Total Points:** {points:.1f}

---

## 👥 Notable Drivers
{drivers_block}

---
*Classification: Tier 1 (Constructor History & Standings)*
"""
        filepath = CONSTRUCTORS_DIR / f"{ref}.md"
        filepath.write_text(content, encoding="utf-8")
        files_written += 1
        index_entries["constructors"].append(f"- [[{ref}]]: {name} ({nat}) — {titles_str} Titles, {wins} Wins, {entries} Starts")

    print("🛣️  Generating Circuit Pages (Tier 1)...")
    for _, cir in circuits.iterrows():
        cir_id = cir['circuitId']
        ref = cir['circuitRef']
        name = cir['name']
        loc = cir['location']
        country = cir['country']
        lat = cir['lat']
        lng = cir['lng']
        alt = cir['alt'] if pd.notna(cir['alt']) and cir['alt'] != r'\N' else "Sea level"

        cir_races = races[races['circuitId'] == cir_id].sort_values(['year', 'round'])
        total_races = len(cir_races)

        races_list = []
        for _, r in cir_races.tail(8).iterrows():
            race_code = f"{r['year']}-{int(r['round']):02d}"
            races_list.append(f"- [[{race_code}]]: {r['year']} {r['name']}")
        
        races_block = "\n".join(races_list) if races_list else "- No recorded championship races"

        content = f"""# {name}

**Location:** {loc}, {country} | **Coordinates:** `{lat}, {lng}` | **Altitude:** `{alt}m`

---

## 📊 Circuit Details
- **Total Grands Prix Hosted:** {total_races}
- **First Championship Race:** {cir_races['year'].min() if total_races > 0 else 'N/A'}
- **Most Recent Grand Prix:** {cir_races['year'].max() if total_races > 0 else 'N/A'}

---

## 🏁 Recent & Notable Grands Prix
{races_block}

---
*Classification: Tier 1 (Circuit Characteristics & Geography)*
"""
        filepath = CIRCUITS_DIR / f"{ref}.md"
        filepath.write_text(content, encoding="utf-8")
        files_written += 1
        index_entries["circuits"].append(f"- [[{ref}]]: {name} ({loc}, {country}) — {total_races} Grands Prix Hosted")

    print("🏁 Generating Race Pages (Tier 1 & Tier 2)...")
    
    # Pre-index qualifying and pit stops by raceId for fast access
    quali_by_race = {}
    if not qualifying.empty:
        qualifying['grid_pos'] = pd.to_numeric(qualifying['position'], errors='coerce')
        quali_merged = qualifying.merge(drivers[['driverId', 'driverRef', 'forename', 'surname']], on='driverId', how='left')
        quali_merged = quali_merged.merge(constructors[['constructorId', 'constructorRef', 'name']], on='constructorId', how='left', suffixes=('', '_team'))
        for r_id, group in quali_merged.groupby('raceId'):
            quali_by_race[r_id] = group.sort_values('grid_pos')

    pit_by_race = {}
    if not pit_stops.empty:
        pit_merged = pit_stops.merge(drivers[['driverId', 'driverRef', 'forename', 'surname']], on='driverId', how='left')
        for r_id, group in pit_merged.groupby('raceId'):
            pit_by_race[r_id] = group.sort_values(['stop', 'lap'])

    # Standings after race
    ds_by_race = {}
    if not driver_standings.empty:
        ds_merged = driver_standings.merge(drivers[['driverId', 'driverRef', 'forename', 'surname']], on='driverId', how='left')
        for r_id, group in ds_merged.groupby('raceId'):
            ds_by_race[r_id] = group.sort_values('pos_num').head(5)

    cs_by_race = {}
    if not constructor_standings.empty:
        cs_merged = constructor_standings.merge(constructors[['constructorId', 'constructorRef', 'name']], on='constructorId', how='left')
        for r_id, group in cs_merged.groupby('raceId'):
            cs_by_race[r_id] = group.sort_values('pos_num').head(5)

    for _, r in races.iterrows():
        r_id = r['raceId']
        yr = r['year']
        rnd = int(r['round'])
        code = f"{yr}-{rnd:02d}"
        race_name = r['name']
        date_str = r['date']
        cir_id = r['circuitId']
        cir_row = circuits[circuits['circuitId'] == cir_id]
        cir_ref = cir_row['circuitRef'].values[0] if not cir_row.empty else "circuit"
        cir_name = cir_row['name'].values[0] if not cir_row.empty else "Unknown Circuit"

        r_res = full_results[full_results['raceId'] == r_id].sort_values('positionOrder')
        
        # Winner, Pole, Fastest Lap
        winner_row = r_res[r_res['pos_num'] == 1]
        winner_ref = winner_row['driverRef'].values[0] if not winner_row.empty else "N/A"
        winner_team = winner_row['constructorRef'].values[0] if not winner_row.empty else "N/A"

        pole_row = r_res[r_res['grid_num'] == 1]
        pole_ref = pole_row['driverRef'].values[0] if not pole_row.empty else "N/A"

        fl_row = r_res[r_res['rank'].astype(str).isin(['1', '1.0'])]
        fl_ref = fl_row['driverRef'].values[0] if not fl_row.empty else "N/A"
        fl_time = fl_row['fastestLapTime'].values[0] if not fl_row.empty and pd.notna(fl_row['fastestLapTime'].values[0]) else "N/A"

        # Classification Table
        class_rows = []
        for _, res in r_res.head(10).iterrows():
            pos_display = res['positionText']
            d_link = f"[[{res['driverRef']}]]"
            c_link = f"[[{res['constructorRef']}]]"
            grid = res['grid']
            laps = res['laps']
            time_status = res['time'] if pd.notna(res['time']) and res['time'] != r'\N' else res['status']
            pts = res['points']
            class_rows.append(f"| {pos_display} | {d_link} | {c_link} | {grid} | {laps} | {time_status} | {pts} |")

        class_table = "| Pos | Driver | Constructor | Grid | Laps | Time/Status | Points |\n| :---: | :--- | :--- | :---: | :---: | :--- | :---: |\n" + "\n".join(class_rows)

        # Standings Leaders
        ds_top = ds_by_race.get(r_id, pd.DataFrame())
        ds_leader = f"[[{ds_top.iloc[0]['driverRef']}]] ({ds_top.iloc[0]['points']} pts)" if not ds_top.empty else "N/A"

        cs_top = cs_by_race.get(r_id, pd.DataFrame())
        cs_leader = f"[[{cs_top.iloc[0]['constructorRef']}]] ({cs_top.iloc[0]['points']} pts)" if not cs_top.empty else "N/A"

        # Write Tier 1 Race Page
        t1_content = f"""# {yr} {race_name}

**Round:** {rnd} | **Date:** {date_str} | **Circuit:** [[{cir_ref}]] ({cir_name})

---

## 🏆 Key Results
- **Winner:** [[{winner_ref}]] ([[ {winner_team} ]])
- **Pole Position:** [[{pole_ref}]]
- **Fastest Lap:** [[{fl_ref}]] (`{fl_time}`)
- **Drivers' Championship Leader:** {ds_leader}
- **Constructors' Championship Leader:** {cs_leader}

---

## 📋 Race Classification (Top 10)
{class_table}

---

## 🔍 Detailed Race Telemetry & Strategy
For comprehensive lap times, pit stops, and qualifying gap charts, see [[{code}-detail]].

---
*Classification: Tier 1 (Official Race Results & Championship Impact)*
"""
        t1_path = RACES_DIR / f"{code}.md"
        t1_path.write_text(t1_content, encoding="utf-8")
        files_written += 1
        index_entries["races_tier1"].append(f"- [[{code}]]: {yr} {race_name} (Round {rnd}) — Won by [[{winner_ref}]] at [[{cir_ref}]]")

        # ── TIER 2: Race Detail Page ──
        quali_group = quali_by_race.get(r_id, pd.DataFrame())
        quali_rows = []
        if not quali_group.empty:
            for _, q in quali_group.head(10).iterrows():
                q1 = q['q1'] if pd.notna(q['q1']) and q['q1'] != r'\N' else "—"
                q2 = q['q2'] if pd.notna(q['q2']) and q['q2'] != r'\N' else "—"
                q3 = q['q3'] if pd.notna(q['q3']) and q['q3'] != r'\N' else "—"
                quali_rows.append(f"| {q['position']} | [[{q['driverRef']}]] | [[{q['constructorRef']}]] | {q1} | {q2} | {q3} |")
            quali_table = "| Pos | Driver | Team | Q1 | Q2 | Q3 |\n| :---: | :--- | :--- | :---: | :---: | :---: |\n" + "\n".join(quali_rows)
        else:
            quali_table = "*Detailed sector and qualifying session times not digitally recorded for this historical era.*"

        pit_group = pit_by_race.get(r_id, pd.DataFrame())
        pit_rows = []
        if not pit_group.empty:
            for _, p in pit_group.head(15).iterrows():
                dur = "N/A"
                if pd.notna(p['duration']) and str(p['duration']) != r'\N':
                    dur = f"{p['duration']}s"
                elif pd.notna(p.get('milliseconds')) and str(p.get('milliseconds')) != r'\N':
                    try:
                        dur = f"{float(p['milliseconds'])/1000:.2f}s"
                    except Exception:
                        dur = "N/A"
                pit_rows.append(f"| [[{p['driverRef']}]] | {p['stop']} | Lap {p['lap']} | {p['time']} | {dur} |")
            pit_table = "| Driver | Stop # | Lap | Time of Day | Stop Duration |\n| :--- | :---: | :---: | :---: | :---: |\n" + "\n".join(pit_rows)
        else:
            pit_table = "*Individual pit stop duration tracking not available for this event.*"

        # Retirements & Incidents
        retirements = r_res[r_res['pos_num'].isna() | (r_res['status'] != 'Finished')]
        ret_rows = []
        for _, ret in retirements.iterrows():
            if ret['status'] != 'Finished' and not ret['status'].startswith('+'):
                ret_rows.append(f"- [[{ret['driverRef']}]] ([[ {ret['constructorRef']} ]]): Lap {ret['laps']} — `{ret['status']}`")
        ret_block = "\n".join(ret_rows) if ret_rows else "- All classified drivers completed the race distance."

        t2_content = f"""# {yr} {race_name} — Detailed Telemetry & Strategy

Parent Race Overview: [[{code}]]

---

## ⏱️ Qualifying Grid & Sector Gaps
{quali_table}

---

## 🛠️ Pit Stop Strategy & Undercut Analysis
{pit_table}

---

## 🚨 Reliability & Retirements Breakdown
{ret_block}

---
*Classification: Tier 2 (Technical Telemetry, Pit Strategy & Session Analysis)*
"""
        t2_path = RACES_DETAIL_DIR / f"{code}-detail.md"
        t2_path.write_text(t2_content, encoding="utf-8")
        files_written += 1
        index_entries["races_tier2"].append(f"- [[{code}-detail]]: Telemetry & Strategy breakdown for {yr} {race_name}")

    print("📑 Generating Master Index (index.md)...")
    index_content = f"""# Formula 1 Knowledge Vault Index

A tiered personal knowledge wiki from historical Formula 1 data (1950–2024), built following Andrej Karpathy's 'LLM Wiki' architecture.

---

## 📊 Tier 3: Derived Analysis & Predictive Models
- [[driver_consistency]]: Driver consistency score & career variance index
- [[pit_strategy]]: Undercut vs. overcut win rates across F1 eras
- [[win_probability_model]]: ML model predicting race win probability from grid position and form
- [[style_clusters]]: K-Means clustering of driving styles and team performance profiles

---

## 🏎️ Tier 1: Drivers ({len(index_entries['drivers'])} Profiles)
{chr(10).join(index_entries['drivers'][:50])}
... *(and {len(index_entries['drivers']) - 50} more driver profiles)*

---

## 🏭 Tier 1: Constructors ({len(index_entries['constructors'])} Teams)
{chr(10).join(index_entries['constructors'])}

---

## 🛣️ Tier 1: Circuits ({len(index_entries['circuits'])} Tracks)
{chr(10).join(index_entries['circuits'])}

---

## 🏁 Tier 1: Grand Prix Races ({len(index_entries['races_tier1'])} Events)
{chr(10).join(index_entries['races_tier1'][-30:])}
... *(and {len(index_entries['races_tier1']) - 30} earlier Grand Prix entries)*

---

## 🔍 Tier 2: Detailed Race Telemetry & Pit Stops ({len(index_entries['races_tier2'])} Detailed Files)
{chr(10).join(index_entries['races_tier2'][-30:])}
... *(and {len(index_entries['races_tier2']) - 30} earlier telemetry records)*
"""
    (VAULT_DIR / "index.md").write_text(index_content, encoding="utf-8")

    print("📝 Appending to changelog (log.md)...")
    log_file = VAULT_DIR / "log.md"
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    log_entry = f"""
## [{now_utc}] — `scripts/ingest.py` Execution
- **Action:** Complete raw data ingestion and markdown vault synthesis.
- **Files Created/Updated:** {files_written} markdown pages.
  - **Tier 1 Drivers:** {len(index_entries['drivers'])} pages
  - **Tier 1 Constructors:** {len(index_entries['constructors'])} pages
  - **Tier 1 Circuits:** {len(index_entries['circuits'])} pages
  - **Tier 1 Races:** {len(index_entries['races_tier1'])} pages
  - **Tier 2 Race Details:** {len(index_entries['races_tier2'])} pages
- **Vault Status:** Deterministic update completed, index.md refreshed.
"""
    if log_file.exists():
        current_log = log_file.read_text(encoding="utf-8")
        log_file.write_text(current_log + log_entry, encoding="utf-8")
    else:
        log_file.write_text(f"# Formula 1 Knowledge Vault Changelog\n{log_entry}", encoding="utf-8")

    print(f"\n🎉 Vault successfully generated with {files_written} pages!")

if __name__ == "__main__":
    data = load_data()
    build_vault(data)
