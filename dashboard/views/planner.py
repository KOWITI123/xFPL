"""
Tab: xPts Planner — projected points, captaincy, value and differentials.
"""
import streamlit as st
import pandas as pd

try:
    from charts import build_xpts_breakdown, build_value_map, build_differentials_scatter, build_defcon_leaders
except ImportError:
    from dashboard.charts import build_xpts_breakdown, build_value_map, build_differentials_scatter, build_defcon_leaders


def render_planner_view(df: pd.DataFrame, proj: pd.DataFrame, horizon_gws: list):
    st.subheader("🔮 Expected Points Planner")
    if not horizon_gws:
        st.info("No upcoming fixtures found.")
        return
    gw_cols = [f"GW{g}" for g in horizon_gws]
    st.caption(f"Projections for GW{horizon_gws[0]}–GW{horizon_gws[-1]} (sidebar filters apply). "
               "Doubles are summed, blanks score 0.")

    if df.empty:
        st.info("No players match the current filters.")
        return

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.markdown("#### Transfer shortlist")
        table = df.sort_values("xpts_total", ascending=False)[
            ["web_name", "team_short_name", "position_name", "cost_million", "selected_by_percent",
             "xpts_total", "xpts_per_m", "p_return_next", "p_defcon_next", *gw_cols]
        ]
        st.dataframe(
            table, hide_index=True, use_container_width=True, height=520,
            column_config={
                "web_name": "Player", "team_short_name": "Team", "position_name": "Pos",
                "cost_million": st.column_config.NumberColumn("Price", format="£%.1fm"),
                "selected_by_percent": st.column_config.NumberColumn("Owned", format="%.1f%%"),
                "xpts_total": st.column_config.ProgressColumn(
                    "xPts total", min_value=0, max_value=float(max(df["xpts_total"].max(), 1)), format="%.1f"),
                "xpts_per_m": st.column_config.NumberColumn("xPts/£m", format="%.2f"),
                "p_return_next": st.column_config.NumberColumn("P(return) next", format="percent",
                                                               help="Chance of at least one goal or assist next GW"),
                "p_defcon_next": st.column_config.NumberColumn("P(DefCon) next", format="percent",
                                                               help="Chance of earning the 2 defensive-contribution pts next GW"),
                **{c: st.column_config.NumberColumn(c, format="%.1f") for c in gw_cols},
            },
        )
    with c2:
        st.markdown(f"#### Captaincy board · GW{horizon_gws[0]}")
        nxt = proj[(proj["gameweek"] == horizon_gws[0]) & proj["player_id"].isin(df["player_id"])]
        st.plotly_chart(build_xpts_breakdown(nxt, by="player", top_n=10), theme=None, use_container_width=True, key="captaincy")
        st.caption("Segments show *why* each candidate projects well: goal-heavy captains have higher ceilings "
                   "than clean-sheet-heavy ones.")

    st.markdown("#### Defensive-contribution bankers")
    st.plotly_chart(build_defcon_leaders(df), theme=None, use_container_width=True, key="defcon")
    st.caption("2 pts whenever a defender makes 10+ clearances/blocks/interceptions/tackles, or a midfielder/forward "
               "12+ including recoveries. Bars = expected DefCon points over the horizon; label = how often they've "
               "hit it so far. Cheap high-volume players here are the floor-raisers the template underrates.")

    st.markdown("#### Value map — who beats their price?")
    st.plotly_chart(build_value_map(df), theme=None, use_container_width=True, key="value_map")
    st.caption("Grey line = what a player at that price typically projects. Named players sit furthest above it.")

    st.markdown("#### Differential finder")
    st.plotly_chart(build_differentials_scatter(df), theme=None, use_container_width=True, key="diffs")
    st.caption("Shaded zone: owned by under 10% but in the top quartile of projected points — "
               "rank gains if they return, low cost if they don't.")
