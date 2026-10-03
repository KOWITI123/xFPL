"""
Tab: Head-to-Head — compare up to three players on the same percentile scale.
"""
import streamlit as st
import pandas as pd

try:
    from analytics import player_percentiles
    from charts import build_radar_compare, build_percentile_dumbbell
    from views.profile import player_label
except ImportError:
    from dashboard.analytics import player_percentiles
    from dashboard.charts import build_radar_compare, build_percentile_dumbbell
    from dashboard.views.profile import player_label


def render_compare_view(players: pd.DataFrame, min_minutes: int):
    st.subheader("⚖️ Head-to-Head")
    st.caption("Pick 2–3 players in the same position. Percentiles use the same peer pool as the Player Profile tab.")

    pos = st.radio("Position", ["FWD", "MID", "DEF", "GKP"], horizontal=True, key="cmp_pos")
    pool = players[players["position_name"] == pos].sort_values("xpts_total", ascending=False, na_position="last")
    labels = pool.apply(player_label, axis=1).tolist()
    picked = st.multiselect("Players", labels, default=labels[:2], max_selections=3, key="cmp_players")
    if len(picked) < 2:
        st.info("Select at least two players to compare.")
        return

    rows = [pool.iloc[labels.index(lbl)] for lbl in picked]
    profiles = {r["web_name"]: player_percentiles(players, r, min_minutes) for r in rows}

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("#### Shape of their game")
        st.plotly_chart(build_radar_compare(profiles), theme=None, use_container_width=True, key="radar")
    with c2:
        st.markdown("#### Metric by metric")
        st.plotly_chart(build_percentile_dumbbell(profiles), theme=None, use_container_width=True, key="dumbbell")
        st.caption("Long grey bars are where the players differ most — that's the real trade-off.")

    st.markdown("#### Decision table")
    cols = {
        "web_name": "Player", "team_short_name": "Team", "cost_million": "Price", "selected_by_percent": "Owned %",
        "total_minutes": "Mins", "total_fpl_points": "Pts", "xpts_next": "xPts next GW",
        "xpts_total": "xPts horizon", "p_return_next": "P(return) next GW", "xgi_per_90": "xGI/90",
        "xgi_delta": "G+A − xGI", "next_opponent": "Next opp", "regression_signal": "Signal",
    }
    table = pd.DataFrame(rows)[list(cols)].rename(columns=cols)
    st.dataframe(
        table, hide_index=True, use_container_width=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="£%.1fm"),
            "xPts next GW": st.column_config.NumberColumn(format="%.2f"),
            "xPts horizon": st.column_config.NumberColumn(format="%.1f"),
            "P(return) next GW": st.column_config.NumberColumn(format="percent"),
            "G+A − xGI": st.column_config.NumberColumn(format="%+.2f"),
        },
    )
