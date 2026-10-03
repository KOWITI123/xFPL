"""
Tab: Player Profile — percentile pizza, scout notes, form trend and fixture-by-fixture xPts.
"""
import streamlit as st
import pandas as pd

try:
    from analytics import player_percentiles, position_pool, scout_notes, DEFCON_THRESHOLD
    from charts import build_pizza_chart, build_gameweek_trend, build_xpts_breakdown
except ImportError:
    from dashboard.analytics import player_percentiles, position_pool, scout_notes, DEFCON_THRESHOLD
    from dashboard.charts import build_pizza_chart, build_gameweek_trend, build_xpts_breakdown


def player_label(r: pd.Series) -> str:
    return f"{r['web_name']} — {r['team_short_name']} {r['position_name']} £{r['cost_million']:.1f}m"


def player_picker(df: pd.DataFrame, key: str, label: str = "Player", default: str | None = None) -> pd.Series | None:
    """Search-as-you-type player select, ordered by projected points so the relevant names come first."""
    opts = df.sort_values("xpts_total", ascending=False, na_position="last")
    labels = opts.apply(player_label, axis=1).tolist()
    idx = next((i for i, l in enumerate(labels) if default and l.startswith(default + " —")), 0)
    choice = st.selectbox(label, labels, index=idx if labels else None, key=key)
    if choice is None:
        return None
    return opts.iloc[labels.index(choice)]


def render_profile_view(players: pd.DataFrame, history: pd.DataFrame, proj: pd.DataFrame,
                        min_minutes: int, horizon_gws: list):
    st.subheader("🧬 Player Profile")
    st.caption("Percentiles compare the player with every same-position player who has logged at least "
               f"{min_minutes} minutes (adjust in the sidebar). Hover any slice for the raw number and what it means.")

    player = player_picker(players, key="profile_player", default="Haaland")
    if player is None:
        st.info("No players available.")
        return

    pos = player["position_name"]
    pool = position_pool(players, pos, min_minutes)
    pct = player_percentiles(players, player, min_minutes)

    k = st.columns(6)
    k[0].metric("Price", f"£{player['cost_million']:.1f}m")
    k[1].metric("Owned", f"{player['selected_by_percent']:.1f}%")
    k[2].metric("Points", f"{player['total_fpl_points']:.0f}", help="Season total across ingested gameweeks")
    k[3].metric("Minutes", f"{player['total_minutes']:.0f}")
    k[4].metric(f"xPts next {len(horizon_gws)} GWs", f"{player.get('xpts_total', float('nan')):.1f}",
                help="Model projection — see Methodology at the bottom of the page")
    k[5].metric("Edge score", f"{player['xfpl_edge_score']:.0f}", help="dbt mart composite (0–100)")

    left, right = st.columns([3, 2], gap="large")
    with left:
        fig = build_pizza_chart(pct, title=f"{player['web_name']} vs {len(pool)} {pos}s")
        st.plotly_chart(fig, theme=None, use_container_width=True, key="pizza")
    with right:
        st.markdown("#### Scout notes")
        for note in scout_notes(player, pct, min_minutes, len(pool)):
            st.markdown(f"- {note}")
        if pct["percentile"].isna().any():
            st.caption("“–” = no Understat match for this player yet, so shot and chance-creation detail is unavailable.")
        st.markdown("#### How to read the pizza")
        st.caption("Each slice is one metric. Length = percentile rank among position peers (50 = median, "
                   "100 = best). Number at the tip = percentile; label = the player's actual value. "
                   "Metrics where lower is better (e.g. goals conceded) are flipped so a longer slice is always better.")
        with st.expander("Raw values & percentiles"):
            st.dataframe(
                pct[["label", "display", "percentile", "category", "explain"]],
                column_config={
                    "label": "Metric", "display": "Value",
                    "percentile": st.column_config.ProgressColumn("Percentile", min_value=0, max_value=100, format="%.0f"),
                    "category": "Category", "explain": "What it measures",
                },
                hide_index=True, use_container_width=True,
            )

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("#### Gameweek form")
        hist = history[history["player_id"] == player["player_id"]]
        st.plotly_chart(build_gameweek_trend(hist, DEFCON_THRESHOLD.get(pos)),
                        theme=None, use_container_width=True, key="trend")
        st.caption("Bars below show chance quality (xG + xA); diamonds show what actually happened. "
                   "Consistent bars with few diamonds = unlucky; diamonds above bars = running hot.")
    with c2:
        st.markdown("#### Where the projected points come from")
        p = proj[proj["player_id"] == player["player_id"]]
        st.plotly_chart(build_xpts_breakdown(p, by="gameweek"), theme=None, use_container_width=True, key="xpts_breakdown")
        st.caption("Each bar is one upcoming gameweek; (H)/(A) = home/away. "
                   "Segments split the expectation into FPL scoring sources; negative values are goals-conceded deductions.")
