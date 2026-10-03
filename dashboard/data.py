"""
BigQuery data extraction, caching, and filtering layer for xFPL.
"""
import os
import streamlit as st
import pandas as pd
from google.cloud import bigquery

MARTS = "de-project-allan.fpl_analytics_marts"


def get_bigquery_client():
    """Resolves BigQuery credentials across local and cloud environments."""
    creds_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "creds", "gcp_key.json"))
    if os.path.exists(creds_path):
        return bigquery.Client.from_service_account_json(creds_path)
    if "gcp_service_account" in st.secrets:
        return bigquery.Client.from_service_account_info(dict(st.secrets["gcp_service_account"]))
    return bigquery.Client()


def _query(sql: str) -> pd.DataFrame:
    df = get_bigquery_client().query(sql).to_dataframe()
    # BigQuery returns nullable Int64/Float64 extension types; downstream maths wants plain numpy
    for col in df.columns:
        if pd.api.types.is_bool_dtype(df[col]):
            df[col] = df[col].fillna(False).astype(bool)
        elif pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].astype("float64")
    for col in ("player_id", "team_id", "gameweek", "fixture_id", "home_team_id", "away_team_id"):
        if col in df.columns and df[col].notna().all():
            df[col] = df[col].astype("int64")
    return df


@st.cache_data(ttl=3600, show_spinner="Loading xFPL Analytics Marts from BigQuery...")
def load_scouting_data() -> pd.DataFrame:
    """One row per player: every season metric from the edge mart plus fixture/market signals."""
    df = _query(f"""
    SELECT
        e.*,
        d.team_id,
        d.chance_of_playing_next_round,
        d.understat_player_name,
        COALESCE(r.next_opponent, 'TBD') AS next_opponent,
        COALESCE(r.venue, 'HOME') AS venue,
        COALESCE(r.fixture_difficulty_rating, 3) AS fixture_difficulty_rating,
        COALESCE(r.fixture_adjusted_primary, 0.0) AS fixture_adjusted_xgi,
        COALESCE(r.market_arbitrage_tag, 'STANDARD') AS market_arbitrage_tag,
        COALESCE(r.xfpl_edge_score, 0.0) AS xfpl_edge_score,
        r.position_rank,
        r.overall_rank
    FROM `{MARTS}.mart_player_performance_edge` e
    LEFT JOIN `{MARTS}.mart_fixture_player_recommendations` r USING (player_id)
    LEFT JOIN `{MARTS}.dim_players` d USING (player_id)
    """)
    df["selected_by_percent"] = df["selected_by_percent"].fillna(0.0)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_gameweek_history() -> pd.DataFrame:
    """One row per player per ingested gameweek (drives form trends and team ratings)."""
    return _query(f"""
    SELECT
        f.fpl_player_id AS player_id,
        f.gameweek,
        f.team_id,
        f.position_name,
        f.minutes,
        f.fpl_points,
        f.goals_scored,
        f.assists,
        f.clean_sheets,
        f.goals_conceded,
        f.bonus_points,
        f.bps,
        f.saves,
        f.expected_goals_conceded,
        f.defensive_contribution,
        f.defensive_contribution_points,
        f.xg,
        f.xa,
        f.npxg,
        f.xgi,
        f.shots,
        f.key_passes
    FROM `{MARTS}.fct_player_underlying` f
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def load_fixtures() -> pd.DataFrame:
    return _query(f"""
    SELECT fixture_id, gameweek, kickoff_time, home_team_id, away_team_id,
           home_team_short_name, away_team_short_name,
           home_team_score, away_team_score, home_difficulty, away_difficulty, is_finished
    FROM `{MARTS}.dim_fixtures`
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def load_teams() -> pd.DataFrame:
    return _query(f"""
    SELECT team_id, team_name, short_name,
           strength_attack_home, strength_attack_away,
           strength_defence_home, strength_defence_away
    FROM `{MARTS}.dim_teams`
    """)


def filter_players(
    df: pd.DataFrame,
    pos: str,
    price_range: tuple,
    min_mins: int,
    teams: list,
    signal: str,
    tag: str
) -> pd.DataFrame:
    """Applies cross-mart filter constraints in pandas."""
    res = df.copy()
    if pos != "ALL":
        res = res[res["position_name"] == pos]
    res = res[(res["cost_million"] >= price_range[0]) & (res["cost_million"] <= price_range[1])]
    res = res[res["total_minutes"] >= min_mins]
    if teams:
        res = res[res["team_short_name"].isin(teams)]
    if signal != "ALL":
        res = res[res["regression_signal"] == signal]
    if tag != "ALL":
        res = res[res["market_arbitrage_tag"] == tag]
    return res
