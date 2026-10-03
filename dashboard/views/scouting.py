"""
Tab: Player Search — the advanced search results for the Control Room filters.
Click a row to open that player's profile.
"""
import streamlit as st
import pandas as pd

try:
    from views.profile import player_label, PROFILE_KEY
except ImportError:
    from dashboard.views.profile import player_label, PROFILE_KEY

TABS_KEY = "main_tabs"
PROFILE_TAB = "🧬 Player Profile"

SORT_OPTIONS = {
    "Projected points (horizon)": ("xpts_total", False),
    "Projected points next GW": ("xpts_next", False),
    "Value: xPts per £m": ("xpts_per_m", False),
    "Chance of goal/assist next GW": ("p_return_next", False),
    "DefCon chance next GW": ("p_defcon_next", False),
    "xGI per 90": ("xgi_per_90", False),
    "Most unlucky (G+A − xGI)": ("xgi_delta", True),
    "Lowest ownership": ("selected_by_percent", True),
    "Cheapest": ("cost_million", True),
    "Season points": ("total_fpl_points", False),
}

COLUMNS = {
    "web_name": "Player", "team_short_name": "Team", "position_name": "Pos",
    "cost_million": st.column_config.NumberColumn("Price", format="£%.1fm"),
    "selected_by_percent": st.column_config.NumberColumn("Owned", format="%.1f%%"),
    "total_minutes": st.column_config.NumberColumn("Mins", format="%d"),
    "total_fpl_points": st.column_config.NumberColumn("Pts", format="%d"),
    "xpts_next": st.column_config.NumberColumn("xPts next", format="%.1f"),
    "xpts_total": st.column_config.NumberColumn("xPts horizon", format="%.1f"),
    "xpts_per_m": st.column_config.NumberColumn("xPts/£m", format="%.2f"),
    "p_return_next": st.column_config.NumberColumn("P(G/A) next", format="percent"),
    "p_defcon_next": st.column_config.NumberColumn("P(DefCon) next", format="percent"),
    "xgi_per_90": st.column_config.NumberColumn("xGI/90", format="%.2f"),
    "xgi_delta": st.column_config.NumberColumn("G+A − xGI", format="%+.2f"),
    "next_opponent": "Next opp",
    "fixture_difficulty_rating": st.column_config.NumberColumn("FDR", format="%d"),
    "regression_signal": "Signal",
    "edge_badge": "Badge",
}


def _open_profile(labels: list[str]):
    """Row click -> load that player in the Profile tab and switch to it."""
    rows = st.session_state["search_table"].selection.rows
    if rows:
        st.session_state[PROFILE_KEY] = labels[rows[0]]
        st.session_state[TABS_KEY] = PROFILE_TAB


def render_scouting_view(df: pd.DataFrame, total: int):
    st.subheader("🔎 Player Search")
    st.caption("Results for the filters in the **Control Room** (left). Filters apply instantly — "
               "no search button needed. **Click any row to open that player's profile.**")

    if df.empty:
        st.warning("No players match these filters. Loosen them in the Control Room or press **Reset filters**.")
        return

    c1, c2 = st.columns([2, 3])
    sort_label = c1.selectbox("Sort by", list(SORT_OPTIONS), key="search_sort")
    col, ascending = SORT_OPTIONS[sort_label]
    c2.markdown(f"<div style='padding-top:2rem'><b>{len(df)}</b> of {total} players match</div>",
                unsafe_allow_html=True)

    view = df.sort_values(col, ascending=ascending, na_position="last")
    labels = view.apply(player_label, axis=1).tolist()
    st.dataframe(
        view[list(COLUMNS)],
        column_config=COLUMNS,
        hide_index=True,
        use_container_width=True,
        height=560,
        key="search_table",
        on_select=lambda: _open_profile(labels),
        selection_mode="single-row",
    )

    st.download_button(
        "📥 Download these results (CSV)",
        data=view.to_csv(index=False).encode("utf-8"),
        file_name="xfpl_player_search.csv",
        mime="text/csv",
    )
