"""
Reusable Plotly visualization functions for xFPL analytics.
Every figure goes through theme.style() so colours, gridlines and ink stay consistent.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from theme import tokens, category_color, diverging_scale, style, CATEGORY_SLOT
    from analytics import XPTS_COMPONENTS
except ImportError:
    from dashboard.theme import tokens, category_color, diverging_scale, style, CATEGORY_SLOT
    from dashboard.analytics import XPTS_COMPONENTS


def _empty(msg: str = "No data for the current selection") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(color=tokens()["muted"]))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style(fig, height=240, legend=False)


# ─── Player profile ─────────────────────────────────────────────────────────

def build_pizza_chart(pct: pd.DataFrame, title: str = "") -> go.Figure:
    """
    Percentile pizza: one slice per metric, slice length = percentile vs position peers,
    colour = metric category. Labels carry the raw value so colour is never the only cue.
    """
    if pct.empty:
        return _empty()
    t = tokens()
    n = len(pct)
    width = 360.0 / n
    thetas = [i * width for i in range(n)]
    labels = [f"<b>{r.label}</b><br>{r.display}" for r in pct.itertuples()]
    r_vals = pct["percentile"].fillna(0).clip(lower=2).tolist()

    fig = go.Figure()
    # Faint full-length track so short slices still read as "out of 100"
    fig.add_trace(go.Barpolar(
        r=[100] * n, theta=thetas, width=[width] * n,
        marker=dict(color=t["grid"], line=dict(color=t["surface"], width=2)),
        opacity=0.6, hoverinfo="skip", showlegend=False,
    ))
    for cat in sorted(pct["category"].unique(), key=lambda c: CATEGORY_SLOT[c]):
        idx = [i for i, c in enumerate(pct["category"]) if c == cat]
        sub = pct.iloc[idx]
        fig.add_trace(go.Barpolar(
            r=[r_vals[i] for i in idx], theta=[thetas[i] for i in idx], width=[width] * len(idx),
            name=cat,
            marker=dict(color=category_color(cat), line=dict(color=t["surface"], width=2)),
            customdata=np.stack([sub["label"], sub["display"], sub["percentile"].fillna(0), sub["explain"]], axis=1),
            hovertemplate="<b>%{customdata[0]}</b>: %{customdata[1]}<br>"
                          "Percentile vs position: %{customdata[2]:.0f}<br>"
                          "<i>%{customdata[3]}</i><extra>" + cat + "</extra>",
        ))
    # Percentile value at the tip of each slice
    fig.add_trace(go.Scatterpolar(
        r=[min(v + 9, 112) for v in r_vals], theta=thetas, mode="text",
        text=[f"{p:.0f}" if pd.notna(p) else "–" for p in pct["percentile"]],
        textfont=dict(color=t["ink"], size=11), hoverinfo="skip", showlegend=False,
    ))
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(color=t["ink"], size=14)),
        polar=dict(
            barmode="overlay",  # slices sit over the 0-100 track instead of stacking on it
            bgcolor="rgba(0,0,0,0)",
            hole=0.08,
            radialaxis=dict(range=[0, 118], tickvals=[25, 50, 75, 100], showticklabels=False, ticks="", showline=False,
                            gridcolor=t["grid"], linecolor="rgba(0,0,0,0)"),
            angularaxis=dict(tickvals=thetas, ticktext=labels, direction="clockwise", rotation=90, ticks="",
                             gridcolor="rgba(0,0,0,0)", linecolor="rgba(0,0,0,0)",
                             tickfont=dict(size=11, color=t["ink2"])),
        ),
    )
    style(fig, height=560)
    fig.update_layout(margin=dict(l=70, r=70, t=60, b=40), legend=dict(y=-0.08, yanchor="top"))
    return fig


def build_radar_compare(profiles: dict[str, pd.DataFrame]) -> go.Figure:
    """Overlaid percentile shapes for up to 3 players (first three slots are all-pairs CVD safe)."""
    if not profiles:
        return _empty()
    t = tokens()
    fig = go.Figure()
    for i, (name, pct) in enumerate(profiles.items()):
        color = t["series"][i]
        r = pct["percentile"].fillna(0).tolist()
        fig.add_trace(go.Scatterpolar(
            r=r + r[:1], theta=pct["label"].tolist() + pct["label"].tolist()[:1],
            name=name, mode="lines+markers", fill="toself",
            line=dict(color=color, width=2), marker=dict(size=8, color=color, line=dict(color=t["surface"], width=2)),
            fillcolor=color, opacity=0.85,
            customdata=np.stack([pct["display"].tolist() + pct["display"].tolist()[:1]], axis=1),
            hovertemplate="<b>" + name + "</b><br>%{theta}: %{customdata[0]}<br>Percentile %{r:.0f}<extra></extra>",
        ))
    for tr in fig.data:
        tr.fillcolor = _rgba(tr.line.color, 0.12)
    fig.update_layout(polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75], tickfont=dict(size=9, color=t["muted"]),
                        gridcolor=t["grid"], linecolor="rgba(0,0,0,0)"),
        angularaxis=dict(direction="clockwise", rotation=90, gridcolor=t["grid"], linecolor=t["axis"],
                         tickfont=dict(size=11, color=t["ink2"])),
    ))
    style(fig, height=520)
    fig.update_layout(margin=dict(l=60, r=60, t=50, b=30))
    return fig


def build_percentile_dumbbell(profiles: dict[str, pd.DataFrame]) -> go.Figure:
    """Metric-by-metric percentile dots for compared players; the grey bar shows the gap."""
    if not profiles:
        return _empty()
    t = tokens()
    names = list(profiles)
    base = profiles[names[0]][["label"]].copy()
    for n in names:
        base[n] = profiles[n]["percentile"].to_numpy()
        base[n + "__disp"] = profiles[n]["display"].to_numpy()
    fig = go.Figure()
    lo, hi = base[names].min(axis=1), base[names].max(axis=1)
    for i, row in base.iterrows():
        fig.add_trace(go.Scatter(x=[lo[i], hi[i]], y=[row["label"]] * 2, mode="lines",
                                 line=dict(color=t["axis"], width=4), hoverinfo="skip", showlegend=False))
    for j, n in enumerate(names):
        fig.add_trace(go.Scatter(
            x=base[n], y=base["label"], mode="markers", name=n,
            marker=dict(size=12, color=t["series"][j], line=dict(color=t["surface"], width=2)),
            customdata=base[[n + "__disp"]].to_numpy(),
            hovertemplate="<b>" + n + "</b><br>%{y}: %{customdata[0]}<br>Percentile %{x:.0f}<extra></extra>",
        ))
    fig.update_xaxes(range=[-2, 102], title="Percentile vs position peers", dtick=25)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return style(fig, height=max(320, 34 * len(base) + 80))


def build_gameweek_trend(hist: pd.DataFrame, defcon_threshold: int | None = None) -> go.Figure:
    """
    Aligned panels (no dual axis): FPL points, xG/xA vs actual G+A, and — for outfield players —
    defensive actions per GW against the DefCon threshold.
    """
    if hist.empty:
        return _empty("No gameweek history ingested for this player")
    t = tokens()
    h = hist.sort_values("gameweek")
    x = "GW" + h["gameweek"].astype(int).astype(str)
    show_dc = defcon_threshold is not None and "defensive_contribution" in h
    titles = ["FPL points", "Expected goal involvement vs actual"]
    if show_dc:
        titles.append(f"Defensive contributions (2 pts at {defcon_threshold}+)")
    fig = make_subplots(rows=len(titles), cols=1, shared_xaxes=True, vertical_spacing=0.11, subplot_titles=titles)
    fig.add_trace(go.Bar(x=x, y=h["fpl_points"], name="Points", marker_color=t["series"][0],
                         showlegend=False, hovertemplate="%{x}: %{y} pts<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=x, y=h["xg"], name="xG", marker_color=t["series"][0],
                         hovertemplate="%{x} xG %{y:.2f}<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Bar(x=x, y=h["xa"], name="xA", marker_color=t["series"][1],
                         hovertemplate="%{x} xA %{y:.2f}<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=h["goals_scored"] + h["assists"], name="Actual G+A", mode="markers",
                             marker=dict(symbol="diamond", size=11, color=t["ink"], line=dict(color=t["surface"], width=2)),
                             hovertemplate="%{x} actual G+A %{y}<extra></extra>"), row=2, col=1)
    if show_dc:
        hit = h["defensive_contribution_points"].fillna(0) > 0
        for mask, name, color in [(hit, "DefCon hit (+2)", category_color("Defensive")), (~hit, "Below threshold", t["axis"])]:
            fig.add_trace(go.Bar(x=x[mask], y=h.loc[mask, "defensive_contribution"], name=name, marker_color=color,
                                 customdata=h.loc[mask, "minutes"],
                                 hovertemplate="%{x}: %{y} actions in %{customdata} mins<extra>" + name + "</extra>"),
                          row=3, col=1)
        fig.add_hline(y=defcon_threshold, line=dict(color=t["ink2"], width=1), row=3, col=1)
    fig.update_layout(barmode="stack", bargap=0.45)
    fig.update_xaxes(categoryorder="array", categoryarray=list(x))
    fig.update_annotations(font=dict(size=12, color=t["ink2"]))
    style(fig, height=600 if show_dc else 460)
    fig.update_layout(margin=dict(t=80), legend=dict(y=1.10 if show_dc else 1.12))
    return fig


def build_defcon_leaders(df: pd.DataFrame, n: int = 12) -> go.Figure:
    """Expected defensive-contribution points over the horizon, with the observed hit rate in the label."""
    d = df[df["xpts_defcon"].notna() & (df["position_name"] != "GKP")].nlargest(n, "xpts_defcon")
    if d.empty:
        return _empty()
    t = tokens()
    fig = go.Figure(go.Bar(
        x=d["xpts_defcon"], y=d["web_name"] + " (" + d["team_short_name"] + " " + d["position_name"] + ")",
        orientation="h", marker_color=category_color("Defensive"),
        text=[f"  hit {r:.0%} · {v:.1f}/90" for r, v in zip(d["defcon_hit_rate"], d["dc_90"])],
        textposition="outside", textfont=dict(color=t["ink2"], size=11), cliponaxis=False,
        customdata=np.stack([d["p_defcon_next"], d["cost_million"], d["selected_by_percent"]], axis=1),
        hovertemplate="%{y}<br>Expected DefCon pts over horizon: %{x:.1f}<br>"
                      "P(hit) next GW: %{customdata[0]:.0%}<br>£%{customdata[1]:.1f}m · owned %{customdata[2]:.1f}%"
                      "<extra></extra>",
    ))
    fig.update_xaxes(title="Expected defensive-contribution points", range=[0, d["xpts_defcon"].max() * 1.35])
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return style(fig, height=max(340, 28 * len(d) + 90), legend=False)


def build_xpts_breakdown(proj: pd.DataFrame, by: str = "gameweek", top_n: int = 12) -> go.Figure:
    """
    Stacked expected-points components. by='gameweek' -> one player's upcoming GWs;
    by='player' -> captaincy board for one GW. Explains *where* the projection comes from.
    """
    if proj.empty:
        return _empty()
    t = tokens()
    if by == "gameweek":
        g = proj.groupby(["gameweek"], as_index=False).agg({**{c: "sum" for c in XPTS_COMPONENTS}, "opponent": " + ".join, "xpts": "sum"})
        y = "GW" + g["gameweek"].astype(int).astype(str) + " · " + g["opponent"]
        orientation_kwargs = dict(orientation="h")
    else:
        g = proj.groupby(["player_id", "web_name", "opponent"], as_index=False)[XPTS_COMPONENTS + ["xpts"]].sum()
        g = g.groupby(["player_id", "web_name"], as_index=False).agg({**{c: "sum" for c in XPTS_COMPONENTS}, "xpts": "sum",
                                                                       "opponent": " + ".join})
        g = g.nlargest(top_n, "xpts")
        y = g["web_name"] + " · " + g["opponent"]
        orientation_kwargs = dict(orientation="h")
    fig = go.Figure()
    for i, comp in enumerate(XPTS_COMPONENTS):
        if g[comp].abs().sum() < 1e-6:
            continue
        fig.add_trace(go.Bar(
            y=y, x=g[comp], name=comp, marker=dict(color=t["series"][i], line=dict(color=t["surface"], width=1)),
            hovertemplate="%{y}<br>" + comp + ": %{x:.2f} xPts<extra></extra>", **orientation_kwargs,
        ))
    fig.add_trace(go.Scatter(
        y=y, x=g["xpts"], mode="text", text=[f"  {v:.1f}" for v in g["xpts"]], textposition="middle right",
        textfont=dict(color=t["ink"]), hoverinfo="skip", showlegend=False,
    ))
    fig.update_layout(barmode="relative", bargap=0.35)
    fig.update_xaxes(title="Expected FPL points", zeroline=True)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return style(fig, height=max(300, 34 * len(g) + 110))


# ─── Fixtures & teams ───────────────────────────────────────────────────────

FIXTURE_MODES = {
    "FPL difficulty (FDR)": ("fdr", False, "FDR", "{:.0f}"),
    "Expected goals scored": ("team_lambda", True, "Team xG", "{:.2f}"),
    "Clean-sheet probability": ("cs_prob", True, "CS %", "{:.0%}"),
}


def build_fixture_ticker(outlook: pd.DataFrame, teams: pd.DataFrame, mode: str) -> go.Figure:
    """Teams x upcoming gameweeks; easiest runs on top. Doubles are combined, blanks left empty."""
    if outlook.empty:
        return _empty("No upcoming fixtures")
    t = tokens()
    col, high_good, label, fmt = FIXTURE_MODES[mode]
    agg = "mean" if col == "fdr" else ("sum" if col == "team_lambda" else lambda s: 1 - np.prod(1 - s))
    cell = outlook.groupby(["team_id", "gameweek"]).agg(val=(col, agg), opp=("opp_short", list), home=("is_home", list)).reset_index()
    # FPL convention: UPPERCASE = home, lowercase = away
    cell["text"] = [" + ".join(o.upper() if h else o.lower() for o, h in zip(os_, hs))
                    for os_, hs in zip(cell["opp"], cell["home"])]
    names = teams.set_index("team_id")["short_name"]
    cell["team"] = cell["team_id"].map(names)
    z = cell.pivot(index="team", columns="gameweek", values="val")
    txt = cell.pivot(index="team", columns="gameweek", values="text")
    order = z.mean(axis=1).sort_values(ascending=not high_good).index
    z, txt = z.loc[order], txt.loc[order]
    gw_labels = [f"GW{int(c)}" for c in z.columns]

    if col == "fdr":
        zmin, zmax = 1, 5
    else:
        mid = float(np.nanmedian(z.values))
        spread = float(np.nanmax(np.abs(z.values - mid))) or 1.0
        zmin, zmax = mid - spread, mid + spread
    hover_val = np.vectorize(lambda v: fmt.format(v) if pd.notna(v) else "blank")(z.values)
    fig = go.Figure(go.Heatmap(
        z=z.values, x=gw_labels, y=z.index, colorscale=diverging_scale(reverse=high_good),
        zmin=zmin, zmax=zmax, xgap=2, ygap=2,
        text=txt.fillna("—").values, texttemplate="%{text}", textfont=dict(size=11, color=t["ink"]),
        customdata=hover_val,
        hovertemplate="<b>%{y}</b> %{x}<br>vs %{text}<br>" + label + ": %{customdata}<extra></extra>",
        colorbar=dict(title=dict(text=label, side="right"), thickness=10, outlinewidth=0,
                      tickfont=dict(color=t["muted"]), tickformat=".0%" if col == "cs_prob" else None),
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(side="top", showgrid=False)
    return style(fig, height=max(420, 24 * len(z) + 80), legend=False)


def build_team_map(ratings: pd.DataFrame) -> go.Figure:
    """Team attack vs defence (per match). Top-right = creates a lot, concedes little."""
    if ratings.empty:
        return _empty()
    t = tokens()
    r = ratings.copy()
    fig = go.Figure(go.Scatter(
        x=r["xgf_per_match"], y=r["xga_per_match"], mode="markers+text", text=r["short_name"],
        textposition="top center", textfont=dict(size=10, color=t["ink2"]),
        marker=dict(size=10, color=t["series"][0], line=dict(color=t["surface"], width=2)),
        customdata=np.stack([r["team_name"], r["n"]], axis=1),
        hovertemplate="<b>%{customdata[0]}</b><br>Model xG for/match %{x:.2f}<br>"
                      "Model xG against/match %{y:.2f}<br>Matches observed %{customdata[1]:.0f}<extra></extra>",
    ))
    fig.add_vline(x=r["xgf_per_match"].mean(), line=dict(color=t["axis"], width=1))
    fig.add_hline(y=r["xga_per_match"].mean(), line=dict(color=t["axis"], width=1))
    fig.add_annotation(xref="paper", yref="paper", x=0.99, y=0.99, text="Strong attack · strong defence",
                       showarrow=False, xanchor="right", font=dict(size=10, color=t["muted"]))
    fig.add_annotation(xref="paper", yref="paper", x=0.01, y=0.01, text="Weak attack · leaky defence",
                       showarrow=False, xanchor="left", font=dict(size=10, color=t["muted"]))
    fig.update_xaxes(title="Expected goals for per match")
    fig.update_yaxes(title="Expected goals against per match (lower is better)", autorange="reversed")
    return style(fig, height=460, legend=False)


def build_fixture_threat_bar(df: pd.DataFrame) -> go.Figure:
    """Top 10 players ranked by fixture-adjusted attacking threat."""
    top = df.sort_values("fixture_adjusted_xgi", ascending=False).head(10)
    if top.empty:
        return _empty()
    t = tokens()
    fig = go.Figure(go.Bar(
        x=top["fixture_adjusted_xgi"], y=top["web_name"] + " vs " + top["next_opponent"].astype(str),
        orientation="h", marker_color=t["series"][0],
        customdata=top["fixture_difficulty_rating"],
        hovertemplate="%{y}<br>Fixture-adjusted xGI/90 %{x:.2f}<br>FDR %{customdata}<extra></extra>",
    ))
    fig.update_xaxes(title="Fixture-adjusted xGI/90")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return style(fig, height=400, legend=False)


# ─── Market, value, regression ──────────────────────────────────────────────

def build_value_map(df: pd.DataFrame, highlight: list | None = None) -> go.Figure:
    """Price vs projected points, one panel per position, with a fair-value trend line.
    Players above the line deliver more projected points than their price implies."""
    d = df[df["xpts_total"].notna()]
    if d.empty:
        return _empty()
    t = tokens()
    positions = [p for p in ["GKP", "DEF", "MID", "FWD"] if p in d["position_name"].unique()]
    fig = make_subplots(rows=1, cols=len(positions), subplot_titles=positions, shared_yaxes=True,
                        horizontal_spacing=0.04)
    highlight = set(highlight or [])
    for i, pos in enumerate(positions, start=1):
        sub = d[d["position_name"] == pos]
        fig.add_trace(go.Scatter(
            x=sub["cost_million"], y=sub["xpts_total"], mode="markers", showlegend=False,
            marker=dict(size=8, color=t["series"][0], opacity=0.75, line=dict(color=t["surface"], width=1)),
            customdata=np.stack([sub["web_name"], sub["team_short_name"], sub["selected_by_percent"]], axis=1),
            hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]})<br>£%{x:.1f}m · %{y:.1f} xPts"
                          "<br>Owned %{customdata[2]:.1f}%<extra></extra>",
        ), row=1, col=i)
        if len(sub) >= 3:
            b, a = np.polyfit(sub["cost_million"], sub["xpts_total"], 1)
            xs = np.linspace(sub["cost_million"].min(), sub["cost_million"].max(), 20)
            fig.add_trace(go.Scatter(x=xs, y=a + b * xs, mode="lines", line=dict(color=t["muted"], width=2),
                                     hoverinfo="skip", showlegend=False), row=1, col=i)
            resid = sub["xpts_total"] - (a + b * sub["cost_million"])
            labelled = sub.loc[resid.nlargest(3).index]
            labelled = pd.concat([labelled, sub[sub["web_name"].isin(highlight)]]).drop_duplicates("player_id")
            _stagger_labels(fig, labelled["cost_million"], labelled["xpts_total"], labelled["web_name"], row=1, col=i)
        fig.update_xaxes(title_text="Price £m", row=1, col=i)
    fig.update_yaxes(title_text="Projected xPts", row=1, col=1)
    fig.update_annotations(selector=dict(text=positions[0]), font=dict(color=t["ink2"]))
    return style(fig, height=430, legend=False)


def build_differentials_scatter(df: pd.DataFrame, y_col: str = "xpts_total") -> go.Figure:
    """Ownership vs projected points. Shaded zone: under 10% owned but top-quartile projection."""
    d = df[df[y_col].notna()]
    if d.empty:
        return _empty()
    t = tokens()
    own = d["selected_by_percent"].clip(lower=0.1)
    q75 = d[y_col].quantile(0.75)
    fig = go.Figure()
    # Shapes on a log axis take raw data values (annotations take log10)
    fig.add_shape(type="rect", x0=0.1, x1=10, y0=q75, y1=d[y_col].max() * 1.05,
                  fillcolor=_rgba(t["series"][2], 0.10), line=dict(width=0), layer="below")
    fig.add_trace(go.Scatter(
        x=own, y=d[y_col], mode="markers",
        marker=dict(size=8, color=t["series"][0], opacity=0.75, line=dict(color=t["surface"], width=1)),
        customdata=np.stack([d["web_name"], d["team_short_name"], d["position_name"], d["cost_million"]], axis=1),
        hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]} %{customdata[2]}, £%{customdata[3]}m)"
                      "<br>Owned %{x:.1f}% · %{y:.1f} xPts<extra></extra>",
    ))
    gems = d[(d["selected_by_percent"] < 10) & (d[y_col] >= q75)].nlargest(6, y_col)
    _stagger_labels(fig, np.log10(gems["selected_by_percent"].clip(lower=0.1)), gems[y_col], gems["web_name"])
    fig.add_annotation(xref="x", yref="paper", x=np.log10(0.12), y=1.0, text="Differential zone", xanchor="left",
                       showarrow=False, font=dict(size=10, color=t["ink2"]))
    fig.update_xaxes(type="log", title="Ownership % (log scale)")
    fig.update_yaxes(title="Projected xPts")
    return style(fig, height=430, legend=False)


def build_luck_ledger(df: pd.DataFrame, n: int = 10) -> go.Figure:
    """Actual goal involvements minus xGI. Blue = output trailing chances (due), red = running hot."""
    d = df[df["xgi_delta"].notna()]
    d = pd.concat([d.nsmallest(n, "xgi_delta"), d.nlargest(n, "xgi_delta")]).drop_duplicates("player_id")
    d = d.sort_values("xgi_delta")
    if d.empty:
        return _empty()
    t = tokens()
    colors = np.where(d["xgi_delta"] < 0, t["good"], t["bad"])
    fig = go.Figure(go.Bar(
        x=d["xgi_delta"], y=d["web_name"] + " (" + d["team_short_name"] + ")", orientation="h", marker_color=colors,
        customdata=np.stack([d["actual_goals"] + d["actual_assists"], d["total_xgi"]], axis=1),
        hovertemplate="%{y}<br>G+A %{customdata[0]:.0f} vs xGI %{customdata[1]:.2f}<br>Delta %{x:+.2f}<extra></extra>",
    ))
    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.06, xanchor="left", showarrow=False,
                       text="◀ Underperforming (due a correction)", font=dict(size=11, color=t["good"]))
    fig.add_annotation(xref="paper", yref="paper", x=1, y=1.06, xanchor="right", showarrow=False,
                       text="Overperforming (likely to cool) ▶", font=dict(size=11, color=t["bad"]))
    fig.update_xaxes(title="Goals + assists minus xGI", zeroline=True, zerolinewidth=1)
    fig.update_yaxes(showgrid=False)
    return style(fig, height=max(380, 24 * len(d) + 90), legend=False)


SIGNAL_LABELS = {
    "UNDERPERFORMING_BUY_TARGET": "Buy target (underperforming)",
    "OVERPERFORMING_SELL_RISK": "Sell risk (overperforming)",
    "NEUTRAL": "Neutral",
}


def build_regression_scatter(df: pd.DataFrame, y_metric: str) -> go.Figure:
    """Goals (or points) vs xG with a parity line; colour carries the regression signal's meaning."""
    if df.empty:
        return _empty()
    t = tokens()
    d = df.assign(signal=df["regression_signal"].map(SIGNAL_LABELS).fillna("Neutral"))
    color_map = {SIGNAL_LABELS["UNDERPERFORMING_BUY_TARGET"]: t["good"],
                 SIGNAL_LABELS["OVERPERFORMING_SELL_RISK"]: t["bad"],
                 "Neutral": t["muted"]}
    fig = px.scatter(
        d, x="total_xg", y=y_metric, color="signal", size="cost_million", size_max=16,
        hover_name="web_name",
        hover_data={"team_short_name": True, "cost_million": True, "actual_goals": True,
                    "total_xg": ":.2f", "xg_delta": ":+.2f", "npxg_per_shot": ":.2f", "signal": False},
        labels={"total_xg": "Expected Goals (xG)", "actual_goals": "Actual Goals",
                "total_fpl_points": "Total FPL Points", "cost_million": "Cost (£m)", "signal": "Signal",
                "team_short_name": "Team", "xg_delta": "Goals − xG", "npxg_per_shot": "npxG/shot"},
        color_discrete_map=color_map, category_orders={"signal": list(color_map)},
    )
    fig.update_traces(marker=dict(line=dict(color=t["surface"], width=1), opacity=0.85))
    if y_metric == "actual_goals":
        max_val = max(d["total_xg"].max(), d[y_metric].max()) + 0.5
        fig.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val], mode="lines", line=dict(color=t["axis"], width=1),
                                 name="Goals = xG", hoverinfo="skip"))
        fig.add_annotation(x=max_val * 0.2, y=max_val * 0.85, text="Overperforming (sell risk)", showarrow=False,
                           font=dict(color=t["bad"], size=11))
        fig.add_annotation(x=max_val * 0.8, y=max_val * 0.15, text="Underperforming (buy-low)", showarrow=False,
                           font=dict(color=t["good"], size=11))
    return style(fig, height=520)


def _stagger_labels(fig: go.Figure, xs, ys, texts, **cell):
    """Direct labels with short leader lines, fanned out vertically so clustered points stay readable."""
    t = tokens()
    order = np.argsort(-np.asarray(ys, dtype=float))
    xs, ys, texts = np.asarray(xs)[order], np.asarray(ys)[order], np.asarray(texts)[order]
    for k, (x, y, txt) in enumerate(zip(xs, ys, texts)):
        fig.add_annotation(x=x, y=y, text=txt, showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=t["muted"],
                           ax=28 if k % 2 else -28, ay=-16 - 13 * k, font=dict(size=10, color=t["ink"]),
                           bgcolor=t["surface"], **cell)


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"
