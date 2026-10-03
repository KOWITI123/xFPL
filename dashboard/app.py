"""
xFPL Decision Engine — Streamlit Intelligence Dashboard (Phase 6)
Main layout orchestrator, sidebar filter controls, and tab routing.
"""
import sys
import os

# Ensure the dashboard package directory is available for imports
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
if DASHBOARD_DIR not in sys.path:
    sys.path.insert(0, DASHBOARD_DIR)

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd

try:
    from data import load_scouting_data, load_gameweek_history, load_fixtures, load_teams, filter_players
    import analytics
    from views import (
        render_scouting_view,
        render_regression_view,
        render_fixtures_view,
        render_call_log_view,
        render_profile_view,
        render_compare_view,
        render_planner_view,
    )
except ImportError:
    from dashboard.data import load_scouting_data, load_gameweek_history, load_fixtures, load_teams, filter_players
    from dashboard import analytics
    from dashboard.views import (
        render_scouting_view,
        render_regression_view,
        render_fixtures_view,
        render_call_log_view,
        render_profile_view,
        render_compare_view,
        render_planner_view,
    )


# Page Config
st.set_page_config(
    page_title="xFPL Scouting Engine",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=3600, show_spinner="Running the expected-points model...")
def build_model(players: pd.DataFrame, history: pd.DataFrame, fixtures: pd.DataFrame,
                teams: pd.DataFrame, horizon: int):
    players = analytics.add_derived_metrics(players, history)
    ratings, mu = analytics.team_ratings(history, fixtures, teams)
    team_fx, gws = analytics.upcoming_fixtures(fixtures, horizon)
    outlook = analytics.fixture_outlook(team_fx, ratings, mu) if gws else pd.DataFrame()
    proj = analytics.project_points(players, outlook, mu) if gws else pd.DataFrame()
    summary = analytics.projection_summary(proj, gws)
    players = players.merge(summary, on="player_id", how="left")
    players["xpts_per_m"] = players["xpts_total"] / players["cost_million"]
    players["xpts_rank_pos"] = players.groupby("position_name")["xpts_total"].rank(ascending=False, method="min")
    return players, proj, outlook, ratings, gws


# Load Data
try:
    raw_players = load_scouting_data()
    history = load_gameweek_history()
    fixtures = load_fixtures()
    teams = load_teams()
except Exception as e:
    st.error(f"Error loading BigQuery data: {e}")
    st.stop()

# Sidebar Global Controls
st.sidebar.title("⚽ xFPL Control Room")
horizon = st.sidebar.slider("Planning horizon (GWs)", 1, 8, 5,
                            help="How many upcoming gameweeks the xPts projection covers")
raw_df, proj, outlook, ratings, horizon_gws = build_model(raw_players, history, fixtures, teams, horizon)

pool_mins = st.sidebar.slider("Percentile peer pool: min minutes", 0, 900, 90, step=45,
                              help="Players below this are excluded from the comparison pool on pizza charts")

st.sidebar.divider()
st.sidebar.caption("Filters for tables & market charts")

positions = ["ALL"] + sorted(raw_df["position_name"].dropna().unique().tolist())
selected_pos = st.sidebar.selectbox("Position", positions)

min_cost, max_cost = float(raw_df["cost_million"].min()), float(raw_df["cost_million"].max())
price_range = st.sidebar.slider("Price Bracket (£m)", min_cost, max_cost, (min_cost, max_cost), step=0.1)

max_mins = int(raw_df["total_minutes"].max())
min_mins = st.sidebar.slider("Min Minutes Played", 0, max_mins, min(60, max_mins), step=15)

team_names = sorted(raw_df["team_short_name"].dropna().unique().tolist())
selected_teams = st.sidebar.multiselect("Teams", team_names)

signals = ["ALL"] + sorted(raw_df["regression_signal"].dropna().unique().tolist())
selected_signal = st.sidebar.selectbox("Regression Signal", signals)

tags = ["ALL"] + sorted(raw_df["market_arbitrage_tag"].dropna().unique().tolist())
selected_tag = st.sidebar.selectbox("Market Arbitrage Tag", tags)

# Filter Data
df = filter_players(raw_df, selected_pos, price_range, min_mins, selected_teams, selected_signal, selected_tag)

# Title & High-Level KPI Banner
st.title("⚽ xFPL: Decision Engine & Scouting Room")
st.caption("Automated market inefficiencies, expected stats regression signals, and fixture-adjusted ratings.")

ingested = sorted(history["gameweek"].unique().astype(int))
finished = sorted(fixtures.loc[fixtures["is_finished"], "gameweek"].unique().astype(int))
missing = [g for g in finished if g not in ingested]
if missing:
    st.warning(
        f"Data coverage: gameweek-level stats ingested for GW{', GW'.join(map(str, ingested))}; "
        f"GW{', GW'.join(map(str, missing))} are finished but missing from the FPL live ingest. "
        "Season totals and per-90s are based on the ingested gameweeks only.",
        icon="⚠️",
    )

k1, k2, k3, k4 = st.columns(4)
k1.metric("Players Active", f"{len(df)} / {len(raw_df)}")
k2.metric("Buy Targets", len(df[df["regression_signal"] == "UNDERPERFORMING_BUY_TARGET"]))
k3.metric("Differentials", len(df[df["market_arbitrage_tag"] == "HIDDEN_DIFFERENTIAL"]))
top_player = df.sort_values("xpts_next", ascending=False).iloc[0] if not df.empty and horizon_gws else None
k4.metric(f"Top xPts GW{horizon_gws[0]}" if horizon_gws else "Top xPts",
          f"{top_player['web_name']} ({top_player['xpts_next']:.1f})" if top_player is not None else "N/A")

# Render Tabs
tabs = st.tabs([
    "🧬 Player Profile",
    "⚖️ Head-to-Head",
    "🔮 xPts Planner",
    "🗓️ Fixtures & Teams",
    "📈 Regression",
    "🎯 Scouting Table",
    "📓 Call Log",
])

with tabs[0]:
    render_profile_view(raw_df, history, proj, pool_mins, horizon_gws)
with tabs[1]:
    render_compare_view(raw_df, pool_mins)
with tabs[2]:
    render_planner_view(df, proj, horizon_gws)
with tabs[3]:
    render_fixtures_view(df, outlook, ratings)
with tabs[4]:
    render_regression_view(df)
with tabs[5]:
    render_scouting_view(df)
with tabs[6]:
    render_call_log_view()

with st.expander("📐 Methodology — how the xPts model works"):
    st.markdown(f"""
**1. Team ratings.** Each team gets an attack and defence multiplier (1.0 = league average) from the xG it
created and conceded in ingested matches, adjusted for home advantage (×{analytics.HOME_ADV}). With few
matches observed, ratings are blended with a prior worth {analytics.TEAM_PRIOR_MATCHES} matches
(FPL strength ratings, or FPL's fixture difficulty when strengths are unavailable).

**2. Player rates.** xG/90, xA/90, bonus/90 and saves/90 are shrunk toward what a player *at that price and position*
typically produces, with the prior worth {analytics.PLAYER_PRIOR_MINUTES} minutes. A 90-minute hot streak
can't fake an elite profile, and a premium player's slow start doesn't erase their price-implied quality.

**3. Minutes.** Probability of playing / playing 60+ comes from the share of ingested gameweeks the player featured in,
multiplied by FPL's availability flag (injury percentages fade back toward fit over three gameweeks).

**4. Fixture xPts.** For each fixture, expected team goals = league mean × own attack × opponent defence × venue.
Points follow FPL scoring: appearance, goals (by position), assists, clean sheets (Poisson P(0 conceded)),
goals-conceded deductions, saves (keepers), and bonus.

**5. Defensive contributions.** Each player's defensive actions per 90 (CBIT for defenders, CBIRT for
midfielders/forwards) are lightly shrunk toward the position average. Per-match counts follow a negative binomial
(fitted spread per position), giving P(reaching 10 / 12 actions) → expected 2-pt DefCon bonus. In a
leave-one-match-out check this was well calibrated (Brier 0.115 vs 0.137 for a position-average baseline).

**Not yet modelled:** penalty-taker and set-piece duties, and rotation inside double gameweeks.
Treat projections as a ranking tool, not exact scores.
""")
