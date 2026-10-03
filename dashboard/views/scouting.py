"""
Tab 1: Filterable Scouting Room & Unified Player Mart.
"""
import streamlit as st
import pandas as pd


def render_scouting_view(df: pd.DataFrame):
    st.subheader("🎯 Unified Scouting & Edge Mart")
    st.caption("Cross-mart table combining Understat xG, FBRef metrics, FPL points, and fixture difficulty.")

    search_query = st.text_input("🔍 Search player name:", "")
    view_df = df.copy()
    if search_query:
        view_df = view_df[view_df["web_name"].str.contains(search_query, case=False, na=False)]

    cols_to_show = [
        "web_name", "team_short_name", "position_name", "cost_million",
        "total_minutes", "total_fpl_points", "xpts_next", "xpts_total", "actual_goals", "total_xg", "xg_delta",
        "npxg_per_shot", "team_xgi_share_pct", "next_opponent", "fixture_difficulty_rating",
        "xfpl_edge_score", "regression_signal", "edge_badge", "market_arbitrage_tag"
    ]

    st.dataframe(
        view_df[cols_to_show].sort_values("xfpl_edge_score", ascending=False),
        column_config={
            "web_name": "Player",
            "team_short_name": "Team",
            "position_name": "Pos",
            "cost_million": st.column_config.NumberColumn("Cost", format="£%.1fm"),
            "total_fpl_points": "Pts",
            "xpts_next": st.column_config.NumberColumn("xPts next", format="%.1f"),
            "xpts_total": st.column_config.NumberColumn("xPts horizon", format="%.1f"),
            "actual_goals": "G",
            "total_xg": "xG",
            "xg_delta": st.column_config.NumberColumn("xG Delta", format="%+.2f"),
            "npxg_per_shot": "Shot Qual",
            "team_xgi_share_pct": "Talisman %",
            "next_opponent": "Next Opp",
            "fixture_difficulty_rating": "FDR",
            "xfpl_edge_score": st.column_config.ProgressColumn("Edge Score", min_value=0, max_value=100, format="%.1f"),
        },
        use_container_width=True,
        hide_index=True,
    )

    csv_data = view_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Filtered Scouting Dataset (CSV)",
        data=csv_data,
        file_name="xfpl_scouting_marts.csv",
        mime="text/csv"
    )
