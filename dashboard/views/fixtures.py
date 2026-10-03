"""
Tab: Fixture Ticker & Team Strength.
"""
import streamlit as st
import pandas as pd

try:
    from charts import build_fixture_ticker, build_team_map, build_fixture_threat_bar, FIXTURE_MODES
except ImportError:
    from dashboard.charts import build_fixture_ticker, build_team_map, build_fixture_threat_bar, FIXTURE_MODES


def render_fixtures_view(df: pd.DataFrame, outlook: pd.DataFrame, ratings: pd.DataFrame):
    st.subheader("🗓️ Fixture Ticker & Team Strength")

    mode = st.radio("Colour cells by", list(FIXTURE_MODES), horizontal=True, key="ticker_mode")
    st.plotly_chart(build_fixture_ticker(outlook, ratings, mode), theme=None, use_container_width=True, key="ticker")
    st.caption("Teams sorted easiest run first. UPPERCASE opponent = home, lowercase = away. "
               "FDR is FPL's own rating; the two model views use this season's xG for/against, "
               "so they react to form that FDR ignores — attackers want high xG, defenders want high CS%.")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("#### Team attack vs defence")
        st.plotly_chart(build_team_map(ratings), theme=None, use_container_width=True, key="team_map")
        st.caption("Model ratings (observed xG blended with a prior while the sample is small). "
                   "Target attackers from teams on the right and defenders from teams near the top.")
    with c2:
        st.markdown("#### Highest fixture-adjusted threat (next GW)")
        if df.empty:
            st.info("No players match the current filters.")
        else:
            st.plotly_chart(build_fixture_threat_bar(df[df["position_name"] != "GKP"]),
                            theme=None, use_container_width=True, key="threat")
            st.caption("xGI/90 scaled by the dbt FDR multiplier (FDR 2 = ×1.15, FDR 4 = ×0.85).")
