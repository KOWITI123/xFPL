"""
Tab 4: Weekly Scouting Thesis & Running Accountability Call Log.
"""
import streamlit as st
import pandas as pd


def render_call_log_view():
    st.subheader("📓 Phase 6: Grounded Scouting Report & The Accountability Ledger")
    st.caption("We record our picks with exact numbers before the deadline, and review whether the thesis held up.")

    st.markdown("### 🎯 Gameweek 1 Scouting Trio (Data-Flagged Picks)")
    c1, c2, c3 = st.columns(3)

    with c1:
        with st.container(border=True):
            st.markdown("#### Jean-Philippe Mateta (£6.5m)")
            st.caption("Crystal Palace · FWD")
            st.metric("Total xG", "6.59", delta="-6.59 xG Delta", delta_color="inverse")
            st.write("**Signal:** `UNDERPERFORMING_BUY_TARGET`")
            st.write("**Shot Quality:** 0.66 npxG/shot | **Team Share:** 29.7%")
            st.info("Generating high-value box chances without converting. Mean regression favors imminent goals.")

    with c2:
        with st.container(border=True):
            st.markdown("#### Pedro Neto (£6.5m)")
            st.caption("Chelsea · MID")
            st.metric("Ownership", "1.3%", delta="7.61 Adj xGI")
            st.write("**Signal:** `HIDDEN_DIFFERENTIAL`")
            st.write("**Fixture:** Brighton (H), FDR 2")
            st.info("Completely off template radar. High-line opponent creates optimal transition opportunities.")

    with c3:
        with st.container(border=True):
            st.markdown("#### Maxim De Cuyper (£4.6m)")
            st.caption("Brighton · DEF")
            st.metric("GW1 Points", "17", delta="4.14 xG Generated")
            st.write("**Signal:** `OUT_OF_POSITION_THREAT`")
            st.write("**Underlying:** 5.33 xGI/90 | 1G, 1A, CS")
            st.info("Defender classification with winger attacking positioning. Significant price-to-output arbitrage.")

    st.markdown("---")
    st.markdown("### 📓 Running Call Log")

    log_df = pd.DataFrame([
        {
            "GW": "GW1",
            "Player": "Jean-Philippe Mateta",
            "Price": "£6.5m",
            "Pre-Deadline Tag": "UNDERPERFORMING_BUY_TARGET",
            "Data Thesis": "6.59 xG underperformance; regression overdue",
            "Post-GW Outcome": "Pending Matchday Completion",
            "Verdict": "⏳ PENDING",
        },
        {
            "GW": "GW1",
            "Player": "Pedro Neto",
            "Price": "£6.5m",
            "Pre-Deadline Tag": "HIDDEN_DIFFERENTIAL",
            "Data Thesis": "1.3% ownership vs Brighton high-line (FDR 2); 7.61 adj xGI",
            "Post-GW Outcome": "Pending Matchday Completion",
            "Verdict": "⏳ PENDING",
        },
        {
            "GW": "GW1",
            "Player": "Maxim De Cuyper",
            "Price": "£4.6m",
            "Pre-Deadline Tag": "OUT_OF_POSITION_THREAT",
            "Data Thesis": "5.33 xGI/90 winger attacking behavior at defender price",
            "Post-GW Outcome": "17 FPL Points (1 Goal, 1 Assist, Clean Sheet)",
            "Verdict": "✅ HIT",
        },
    ])

    st.dataframe(log_df, use_container_width=True, hide_index=True)
