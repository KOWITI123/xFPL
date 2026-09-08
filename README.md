# ⚽ xFPL: End-to-End Fantasy Premier League Intelligence Engine

[![dbt](https://img.shields.io/badge/dbt-1.12-orange?logo=dbt)](https://www.getdbt.com/)
[![Google Cloud](https://img.shields.io/badge/GCP-BigQuery%20%2B%20GCS-blue?logo=google-cloud)](https://cloud.google.com/)
[![Kestra](https://img.shields.io/badge/Orchestrator-Kestra-purple)](https://kestra.io/)
[![Looker Studio](https://img.shields.io/badge/Visuals-Looker%20Studio-brightgreen)](https://lookerstudio.google.com/)

An end-to-end modern data stack platform that ingests, cleans, resolves, and models multi-source football analytics to uncover market inefficiencies and predictive edges in Fantasy Premier League.

---

## 🏗️ Architecture Overview

```
[ FPL API ]       [ Understat Scraper ]       [ FBRef (soccerdata) ]
      │                    │                           │
      └────────────────────┼───────────────────────────┘
                           │ (Kestra Orchestration)
                           ▼
               [ Google Cloud Storage ] (Raw CSV/JSON)
                           │
                           ▼
           [ Google BigQuery External Tables ]
                           │
                           ▼ (dbt Core Transformations)
           ┌───────────────────────────────────────────┐
           │ Staging Layer (stg_*)                     │
           │ Intermediate Resolution (int_player_*)    │
           │ Cross-Referenced Identity (dim_player_*)  │
           │ Unified Fact Layer (fct_player_*)         │
           │ Production Marts (mart_*)                 │
           └───────────────────────────────────────────┘
                           │
                           ▼
          [ Google Looker Studio Dashboard ]
```

---

## 🧠 The Hard Problem: Multi-Source Identity Resolution

Football statistics live in silos. To find true statistical edges, we fuse **FPL** (official prices, minutes, bonus points), **Understat** (shot-level expected goals/assists `xG` and `xA`), and **FBRef** (per-90 defensive actions, progressive passes, tackles won).

However, each provider names players differently:
* *Heung-Min Son* (FPL) vs. *Son Heung-Min* (Understat)
* *Rodrigo 'Rodri' Hernandez Cascante* (FPL) vs. *Rodrigo* (Understat) vs. *Rodri* (FBRef)
* *Carlos Henrique Casimiro* (FPL) vs. *Casemiro* (FBRef/Understat)
* *Martin Ødegaard* (FPL) vs. *Martin Odegaard* (Understat)

### How We Solved It (Two Intuitive Systems)

#### 1. The "Airport Customs Funnel" (`dim_player_crossref.sql`)
Think of player matching like an international airport checkpoint:
1. **Diplomatic Pass:** Manual overrides table (`seeds/player_overrides.csv`) for mononyms like *Rodri*, *Casemiro*, or *Alisson*.
2. **Automated E-Gates:** Deterministic string matching — exact names, inverted surname order (e.g. *Son Heung-min*), and name containment (e.g. *David Raya* inside *David Raya Martín*).
3. **Facial Recognition:** Fuzzy string matching via Levenshtein edit distance ($\le 3$) for minor spelling differences.

#### 2. The "Universal Accent Translator" (`macros/normalize_name.sql`)
Accents break database joins because computers treat `Ø` as different from `O`. We built a transliteration macro that maps non-ASCII letters to clean English equivalents (`ø→o`, `æ→ae`, `ß→ss`, `đ→d`, `ł→l`) and collapses irregular whitespace.

---

## 📊 Phase 6: The Scouting Dashboard + The Story

Data pipelines are useless if they don't drive actionable decisions. This project closes the loop with an interactive **Looker Studio Dashboard** and a live **Scouting Call Log**.

### 🔗 Dashboard Link
> **[Interactive Looker Studio Dashboard: xFPL Scouting Room](https://lookerstudio.google.com/)** *(Connect to `fpl_analytics_marts` in BigQuery)*

#### What's in the Dashboard:
1. **Filterable Scouting Table:** Filter by position, price bracket, and team. Sort by `xg_delta`, `npxg_per_shot`, and automated tags (`CLINICAL_FINISHER`, `DEFENSIVE_ROCK`, `OUT_OF_POSITION_THREAT`).
2. **Regression Scatter Plot (Points vs. xG):**
   * **Above the 45° trendline:** Overperformers due for negative regression (sell candidates).
   * **Below the 45° trendline:** Unlucky underperformers generating high chances without goals (buy-low targets).
3. **Fixture Difficulty Heatmap:** Color-coded FDR for the next 3–5 gameweeks to spot impending fixture swings.

---

## 🎯 Weekly Scouting Picks (Data-Flagged Calls)

Using our production dbt marts (`mart_player_performance_edge` and `mart_fixture_player_recommendations`), here are **three high-conviction calls** identified by the data:

### Pick 1: Jean-Philippe Mateta (Crystal Palace) — FWD | £6.5m
* **The Data Signal:** `UNDERPERFORMING_BUY_TARGET` | `BUDGET_TALISMAN`
* **The Numbers:**
  * Actual Goals: **0** vs. Expected Goals (**6.59 xG**)
  * xG Delta: **-6.59** (largest underperformance in the league)
  * Shot Quality: **0.66 npxG/shot**
  * Team Attack Dominance: **29.7% of Palace's total xGI**
* **The Thesis:** Mateta has generated nearly 7 expected goals without finding the net. His 0.66 non-penalty xG per shot proves he is getting high-quality box chances rather than taking speculative long-range shots. Mean regression strongly dictates that an explosive haul is imminent.

---

### Pick 2: Pedro Neto (Chelsea) — MID | £6.5m
* **The Data Signal:** `HIDDEN_DIFFERENTIAL` | **xFPL Edge Score: 100.0**
* **The Numbers:**
  * Ownership: **1.3%**
  * Next Fixture: **Brighton (Home), FDR 2**
  * Fixture-Adjusted xGI: **7.61**
* **The Thesis:** Completely ignored by the template at 1.3% ownership. Facing a high-line Brighton defense at Stamford Bridge (FDR 2), his fixture-adjusted xGI of 7.61 makes him the highest-value midfield differential on the board for managers hunting rank gains.

---

### Pick 3: Maxim De Cuyper (Brighton) — DEF | £4.6m
* **The Data Signal:** `OUT_OF_POSITION_THREAT`
* **The Numbers:**
  * Position: **Defender (£4.6m)**
  * Underlying Threat: **4.14 xG generated** (xGI/90: **5.33**)
  * GW1 Output: **17 FPL points** (1 goal, 1 assist, clean sheet)
* **The Thesis:** Priced as a budget defender, but playing with the attacking freedom of an advanced winger. His 4.14 xG demonstrates sustained box entry, offering clean sheet safety paired with attacker-grade ceiling.

---

## 📓 The Running Call Log (The Accountability Ledger)

To maintain intellectual honesty, we log predictions before the Gameweek deadline and grade them after the final whistle:

| Gameweek | Player Selected | Data Thesis Summary | Pre-Deadline Tag | Post-GW Outcome | Model Verdict & Learnings |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **GW1** | **J. Mateta** (£6.5m) | 6.59 xG underperformance; positive regression due | `UNDERPERFORMING_BUY_TARGET` | *Pending GW Matches* | *Evaluated post-deadline* |
| **GW1** | **P. Neto** (£6.5m) | 1.3% ownership vs Brighton high line (FDR 2) | `HIDDEN_DIFFERENTIAL` | *Pending GW Matches* | *Evaluated post-deadline* |
| **GW1** | **M. De Cuyper** (£4.6m) | 5.33 xGI/90 winger behavior at defender price | `OUT_OF_POSITION_THREAT` | *17 pts (1G, 1A, CS)* | **HIT:** Validated high attacking floor |

---

## 🛠️ Tech Stack & Local Setup

* **Database & Warehouse:** Google BigQuery
* **Cloud Storage:** Google Cloud Storage (GCS)
* **Transformations:** dbt Core 1.12 (`dbt compile`, `dbt test`, `dbt run`)
* **Orchestration:** Kestra 2.0 (Docker Compose)
* **Data Scrapers:** `soccerdata` (FBRef), Understat, Official FPL REST endpoints

### Running Locally
```bash
# 1. Start Kestra Orchestrator
cd orchestration
docker compose up -d

# 2. Compile & Test dbt Models
cd ../dbt
dbt deps
dbt compile
dbt test

# 3. Preview Live Marts & Recommendations
python ../scripts/preview_marts.py
```
