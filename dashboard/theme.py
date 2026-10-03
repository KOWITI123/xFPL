"""
Chart palette + Plotly layout shared by every xFPL visual.

Colours are validated (CVD-safe adjacent pairs, both modes) and assigned by job:
  categorical  -> metric category / compared players, fixed order, never cycled
  diverging    -> good (blue) <-> neutral grey <-> bad (red), e.g. fixture difficulty, luck
"""
import streamlit as st
import plotly.graph_objects as go

_LIGHT = {
    "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
    "grid": "#e1e0d9", "axis": "#c3c2b7", "neutral": "#f0efec",
    "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    "good": "#2a78d6", "bad": "#e34948",
}
_DARK = {
    "surface": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7", "muted": "#898781",
    "grid": "#2c2c2a", "axis": "#383835", "neutral": "#383835",
    "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
    "good": "#3987e5", "bad": "#e66767",
}

# Metric categories own a fixed slot so colour always means the same thing.
# Order keeps orange (Creative) and yellow (Defensive) apart on every pizza.
CATEGORY_SLOT = {"Attacking": 0, "Creative": 1, "FPL Output": 2, "Defensive": 3}


def tokens() -> dict:
    """Palette for the viewer's active Streamlit theme."""
    try:
        mode = st.context.theme.type
    except Exception:
        mode = None
    return _DARK if mode == "dark" else _LIGHT


def category_color(category: str) -> str:
    return tokens()["series"][CATEGORY_SLOT[category]]


def diverging_scale(reverse: bool = False) -> list:
    """Blue (good) -> grey midpoint -> red (bad). reverse=True when high values are good."""
    t = tokens()
    lo, hi = (t["bad"], t["good"]) if reverse else (t["good"], t["bad"])
    return [[0.0, lo], [0.5, t["neutral"]], [1.0, hi]]


def style(fig: go.Figure, height: int = 420, legend: bool = True) -> go.Figure:
    """Recessive hairline chrome, transparent background, theme-aware ink."""
    t = tokens()
    fig.update_layout(
        height=height,
        template="none",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=12, color=t["ink2"]),
        margin=dict(l=8, r=8, t=56, b=8),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(color=t["ink2"])),
        hoverlabel=dict(bgcolor=t["surface"], bordercolor=t["axis"], font=dict(color=t["ink"])),
    )
    axis = dict(gridcolor=t["grid"], linecolor=t["axis"], zerolinecolor=t["axis"], automargin=True,
                tickfont=dict(color=t["muted"]), title_font=dict(color=t["ink2"]))
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig
