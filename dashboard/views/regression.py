"""
Tab 2: Over/Under Statistical Regression View.
"""
import streamlit as st
import pandas as pd

try:
    from charts import build_regression_scatter, build_luck_ledger
except ImportError:
    from dashboard.charts import build_regression_scatter, build_luck_ledger


def render_regression_view(df: pd.DataFrame):
    st.subheader("📈 Statistical Regression: Output vs Expected")
    st.caption("Identify clinical finishing, bad luck, and high-volume players overdue for hauls.")

    if df.empty:
        st.info("No players match the current filters.")
        return

    c1, c2 = st.columns(2, gap="large")
    with c1:
        y_metric = st.radio("Y-Axis Metric:", ["actual_goals", "total_fpl_points"], horizontal=True,
                            format_func={"actual_goals": "Goals", "total_fpl_points": "FPL points"}.get)
        st.plotly_chart(build_regression_scatter(df, y_metric), theme=None, use_container_width=True, key="reg_scatter")
        st.caption("Bubble size = price. Below the diagonal = fewer goals than chances deserve.")
    with c2:
        st.markdown("#### Luck ledger")
        st.plotly_chart(build_luck_ledger(df), theme=None, use_container_width=True, key="luck")
        st.caption("Biggest gaps between returns and xGI. Small samples swing hard — "
                   "trust a gap more when xGI/90 is also high.")
