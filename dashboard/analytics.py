"""
Player profiling and expected-points modelling for xFPL.

Pure pandas/numpy (no Streamlit) so every function is testable offline.

Model overview (see the Methodology expander in the app):
  1. Team ratings   - attack/defence multipliers from observed xG for/against,
                      shrunk toward FPL's own strength ratings (few matches = trust the prior).
  2. Player rates   - xG/xA/bonus/saves per 90, shrunk toward a price-implied prior for the
                      player's position (a £13m forward is expected to shoot more than a £5m one).
  3. Minutes        - share of ingested gameweeks started / played 60+, scaled by FPL availability.
  4. Fixture xPts   - Poisson goal expectations per fixture -> FPL scoring rules.
"""
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

POSITIONS = ["GKP", "DEF", "MID", "FWD"]

# FPL scoring rules
GOAL_PTS = {"GKP": 10, "DEF": 6, "MID": 5, "FWD": 4}
CS_PTS = {"GKP": 4, "DEF": 4, "MID": 1, "FWD": 0}
ASSIST_PTS = 3

# Model hyper-parameters
TEAM_PRIOR_MATCHES = 6      # team ratings: weight of the FPL strength prior, in matches
PLAYER_PRIOR_MINUTES = 450  # player rates: weight of the price-implied prior, in minutes
HOME_ADV = 1.08             # multiplicative home boost to expected goals (away gets 1/HOME_ADV)

# Defensive contribution points (FPL 2025/26+): 2 pts once a player reaches the threshold in a match.
# DEF count CBIT (clearances, blocks, interceptions, tackles); MID/FWD count CBIRT (CBIT + recoveries).
DEFCON_PTS = 2
DEFCON_THRESHOLD = {"DEF": 10, "MID": 12, "FWD": 12}
# Negative-binomial dispersion of per-match counts, fitted on this season's data (var = mu + mu^2 / r)
DEFCON_DISPERSION = {"DEF": 15.0, "MID": 20.0, "FWD": 40.0}
# Defensive volume is a stable trait, so a light prior calibrates best (leave-one-match-out Brier)
DEFCON_PRIOR_MINUTES = 90

XPTS_COMPONENTS = ["Appearance", "Goals", "Assists", "Clean sheet", "Saves", "Bonus",
                   "Def. contribution", "Goals conceded"]


def _per90(num: pd.Series, mins: pd.Series) -> pd.Series:
    return np.where(mins > 0, num * 90.0 / mins.where(mins > 0, 1), 0.0)


UNDERSTAT_ONLY = [
    "npxg_90", "shots_per_90", "npxg_per_shot", "conversion_rate", "key_passes_per_90",
    "xa_per_key_pass", "xg_chain_90", "xg_buildup_90",
]


# ─── Derived per-90 metrics ─────────────────────────────────────────────────

def add_derived_metrics(players: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Adds per-90 and availability metrics the pizza charts and the model rely on."""
    df = players.copy()
    mins = df["total_minutes"].fillna(0)
    for col, src in [
        ("xg_90", "total_xg"), ("npxg_90", "total_npxg"), ("xa_90", "total_xa"),
        ("xg_chain_90", "total_xg_chain"), ("xg_buildup_90", "total_xg_buildup"),
        ("xgc_90", "total_xgc"), ("pts_90", "total_fpl_points"), ("bonus_90", "total_bonus_points"),
    ]:
        df[col] = _per90(df[src].fillna(0), mins)
    df["dc_90"] = _per90(df["total_defensive_contribution"].fillna(0), mins)
    df["defcon_pts_90"] = _per90(df["total_defensive_contribution_points"].fillna(0), mins)
    df["goals_prevented_90"] = _per90(df["total_xgc"].fillna(0) - df["total_goals_conceded"].fillna(0), mins)

    # Shots, key passes and xGChain/Buildup only exist in Understat. For players with no Understat
    # match they read as 0, which would rank them bottom of the pizza; mark them unknown instead.
    no_understat = df["understat_player_name"].isna()
    df.loc[no_understat, UNDERSTAT_ONLY] = np.nan

    # Availability from the ingested gameweeks (not every GW may be ingested)
    n_gw = max(history["gameweek"].nunique(), 1)
    apps = history.groupby("player_id").agg(
        gw_played=("minutes", lambda m: int((m > 0).sum())),
        gw_60=("minutes", lambda m: int((m >= 60).sum())),
        # Typical minutes in full games vs cameos: threshold-based points (DefCon) depend on
        # the split, not just the average (four 85-min starts + a cameo != five 71-min games)
        mins_full=("minutes", lambda m: float(m[m >= 60].mean()) if (m >= 60).any() else 0.0),
        mins_cameo=("minutes", lambda m: float(m[(m > 0) & (m < 60)].mean()) if ((m > 0) & (m < 60)).any() else 0.0),
    )
    df = df.merge(apps, left_on="player_id", right_index=True, how="left")
    df[["gw_played", "gw_60", "mins_full", "mins_cameo"]] = df[["gw_played", "gw_60", "mins_full", "mins_cameo"]].fillna(0)
    df["n_gw_observed"] = n_gw
    df["minutes_share"] = mins / (n_gw * 90.0)
    df["mins_per_app"] = np.where(df["gw_played"] > 0, mins / df["gw_played"].clip(lower=1), 0.0)
    return df


# ─── Percentile profiles (pizza charts) ─────────────────────────────────────

@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    category: str
    fmt: str = "{:.2f}"
    higher_is_better: bool = True
    explain: str = ""


_M = Metric
PIZZA_METRICS: dict[str, list[Metric]] = {
    "FWD": [
        _M("npxg_90", "npxG/90", "Attacking", explain="non-penalty chance quality per 90"),
        _M("shots_per_90", "Shots/90", "Attacking", explain="shot volume"),
        _M("npxg_per_shot", "npxG/shot", "Attacking", explain="average chance quality"),
        _M("conversion_rate", "Conversion", "Attacking", "{:.0%}", explain="goals per shot (noisy, regresses)"),
        _M("xa_90", "xA/90", "Creative", explain="chances created for others"),
        _M("key_passes_per_90", "Key passes/90", "Creative", explain="passes leading to a shot"),
        _M("xg_chain_90", "xGChain/90", "Creative", explain="involvement in any shot-ending move"),
        _M("pts_90", "Pts/90", "FPL Output", "{:.1f}", explain="FPL points per 90"),
        _M("bps_per_90", "BPS/90", "FPL Output", "{:.1f}", explain="bonus-point system score"),
        _M("points_per_million", "Pts/£m", "FPL Output", "{:.1f}", explain="points per £m"),
        _M("team_xgi_share_pct", "Team xGI %", "FPL Output", "{:.0f}%", explain="share of team attacking output"),
    ],
    "MID": [
        _M("xg_90", "xG/90", "Attacking", explain="goal threat per 90"),
        _M("shots_per_90", "Shots/90", "Attacking", explain="shot volume"),
        _M("npxg_per_shot", "npxG/shot", "Attacking", explain="average chance quality"),
        _M("xa_90", "xA/90", "Creative", explain="chances created for others"),
        _M("key_passes_per_90", "Key passes/90", "Creative", explain="passes leading to a shot"),
        _M("xg_chain_90", "xGChain/90", "Creative", explain="involvement in any shot-ending move"),
        _M("pts_90", "Pts/90", "FPL Output", "{:.1f}", explain="FPL points per 90"),
        _M("bps_per_90", "BPS/90", "FPL Output", "{:.1f}", explain="bonus-point system score"),
        _M("points_per_million", "Pts/£m", "FPL Output", "{:.1f}", explain="points per £m"),
        _M("team_xgi_share_pct", "Team xGI %", "FPL Output", "{:.0f}%", explain="share of team attacking output"),
        _M("dc_90", "Def. contrib/90", "Defensive", "{:.1f}",
           explain="clearances, blocks, interceptions, tackles + recoveries (12 = 2 pts)"),
        _M("defcon_hit_rate", "DefCon hit %", "Defensive", "{:.0%}", explain="share of games earning the 2 DefCon pts"),
    ],
    "DEF": [
        _M("clean_sheet_rate", "CS rate", "Defensive", "{:.0%}", explain="clean sheets per appearance"),
        _M("xgc_90", "xGC/90", "Defensive", higher_is_better=False, explain="expected goals conceded while on pitch"),
        _M("dc_90", "Def. contrib/90", "Defensive", "{:.1f}",
           explain="clearances, blocks, interceptions, tackles (10 = 2 pts)"),
        _M("defcon_hit_rate", "DefCon hit %", "Defensive", "{:.0%}", explain="share of games earning the 2 DefCon pts"),
        _M("xg_90", "xG/90", "Attacking", explain="goal threat per 90"),
        _M("xa_90", "xA/90", "Creative", explain="chances created for others"),
        _M("key_passes_per_90", "Key passes/90", "Creative", explain="passes leading to a shot"),
        _M("xg_buildup_90", "xGBuildup/90", "Creative", explain="deep build-up involvement"),
        _M("pts_90", "Pts/90", "FPL Output", "{:.1f}", explain="FPL points per 90"),
        _M("bps_per_90", "BPS/90", "FPL Output", "{:.1f}", explain="bonus-point system score"),
        _M("points_per_million", "Pts/£m", "FPL Output", "{:.1f}", explain="points per £m"),
        _M("minutes_share", "Minutes share", "FPL Output", "{:.0%}", explain="share of available minutes played"),
    ],
    "GKP": [
        _M("saves_per_90", "Saves/90", "Defensive", "{:.1f}", explain="save volume (save points)"),
        _M("save_pct", "Save %", "Defensive", "{:.0f}%", explain="saves / shots on target faced"),
        _M("goals_prevented_90", "Goals prevented/90", "Defensive", explain="xGC minus goals conceded"),
        _M("xgc_90", "xGC/90", "Defensive", higher_is_better=False, explain="expected goals conceded"),
        _M("clean_sheet_rate", "CS rate", "Defensive", "{:.0%}", explain="clean sheets per appearance"),
        _M("pts_90", "Pts/90", "FPL Output", "{:.1f}", explain="FPL points per 90"),
        _M("bps_per_90", "BPS/90", "FPL Output", "{:.1f}", explain="bonus-point system score"),
        _M("points_per_million", "Pts/£m", "FPL Output", "{:.1f}", explain="points per £m"),
        _M("minutes_share", "Minutes share", "FPL Output", "{:.0%}", explain="share of available minutes played"),
    ],
}


def position_pool(df: pd.DataFrame, position: str, min_minutes: int) -> pd.DataFrame:
    return df[(df["position_name"] == position) & (df["total_minutes"] >= min_minutes)]


def percentile_of(value: float, pool: pd.Series, higher_is_better: bool = True) -> float:
    """Mid-rank percentile of value within pool (works for players outside the pool too)."""
    pool = pool.dropna()
    if pool.empty or pd.isna(value):
        return np.nan
    below = (pool < value).mean()
    equal = (pool == value).mean()
    pct = 100.0 * (below + 0.5 * equal)
    return pct if higher_is_better else 100.0 - pct


def player_percentiles(df: pd.DataFrame, player: pd.Series, min_minutes: int) -> pd.DataFrame:
    """Raw value + percentile vs same-position peers for every pizza metric."""
    pos = player["position_name"]
    pool = position_pool(df, pos, min_minutes)
    rows = []
    for m in PIZZA_METRICS.get(pos, []):
        val = player.get(m.key, np.nan)
        rows.append({
            "key": m.key, "label": m.label, "category": m.category, "explain": m.explain,
            "value": val,
            "display": m.fmt.format(val) if pd.notna(val) else "–",
            "percentile": percentile_of(val, pool[m.key], m.higher_is_better) if m.key in pool else np.nan,
        })
    return pd.DataFrame(rows)


# ─── Team ratings ───────────────────────────────────────────────────────────

def team_ratings(history: pd.DataFrame, fixtures: pd.DataFrame, teams: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """
    Attack / defence multipliers (1.0 = league average) and league mean xG per team-match.
    attack > 1 creates more than average; defence > 1 concedes more than average.
    """
    team_gw = history.groupby(["team_id", "gameweek"], as_index=False)["xg"].sum()
    played = fixtures[fixtures["is_finished"] & fixtures["gameweek"].isin(team_gw["gameweek"].unique())]

    rows = []
    for _, f in played.iterrows():
        h = team_gw[(team_gw.team_id == f.home_team_id) & (team_gw.gameweek == f.gameweek)]["xg"].sum()
        a = team_gw[(team_gw.team_id == f.away_team_id) & (team_gw.gameweek == f.gameweek)]["xg"].sum()
        rows.append({"team_id": f.home_team_id, "xgf": h / HOME_ADV, "xga": a * HOME_ADV})
        rows.append({"team_id": f.away_team_id, "xgf": a * HOME_ADV, "xga": h / HOME_ADV})
    obs = pd.DataFrame(rows, columns=["team_id", "xgf", "xga"])
    agg = obs.groupby("team_id").agg(n=("xgf", "size"), xgf=("xgf", "sum"), xga=("xga", "sum"))
    mu = float(obs["xgf"].mean()) if not obs.empty else 1.35

    t = teams.copy()
    strength_cols = ["strength_attack_home", "strength_attack_away", "strength_defence_home", "strength_defence_away"]
    t[strength_cols] = t[strength_cols].astype(float).fillna(0.0)
    if (t[strength_cols] > 0).all().all():
        att = (t["strength_attack_home"] + t["strength_attack_away"]) / 2
        dfn = (t["strength_defence_home"] + t["strength_defence_away"]) / 2
        t["att_prior"] = att / att.mean()
        t["def_prior"] = dfn.mean() / dfn  # stronger defence -> concedes less -> multiplier < 1
    else:
        # FPL sometimes ships zeroed strength ratings; fall back to the FDR opponents get vs this team
        # (FDR 5 opponent ≈ +24% attack / -24% conceded vs an average FDR-3 side).
        faced = pd.concat([
            fixtures[["home_team_id", "away_difficulty"]].set_axis(["team_id", "fdr"], axis=1),
            fixtures[["away_team_id", "home_difficulty"]].set_axis(["team_id", "fdr"], axis=1),
        ]).astype(float).groupby("team_id")["fdr"].mean()
        tier = t["team_id"].astype(float).map(faced).fillna(3.0) - 3.0
        t["att_prior"] = 1.0 + 0.12 * tier
        t["def_prior"] = 1.0 - 0.12 * tier
    t["team_id"] = t["team_id"].astype(int)
    t = t.merge(agg, left_on="team_id", right_index=True, how="left").fillna({"n": 0, "xgf": 0.0, "xga": 0.0})

    k = TEAM_PRIOR_MATCHES
    t["attack"] = (t["xgf"] + k * mu * t["att_prior"]) / ((t["n"] + k) * mu)
    t["defence"] = (t["xga"] + k * mu * t["def_prior"]) / ((t["n"] + k) * mu)
    t["xgf_per_match"] = mu * t["attack"]
    t["xga_per_match"] = mu * t["defence"]
    return t, mu


# ─── Player rates with price-implied shrinkage ──────────────────────────────

def _price_prior(pool: pd.DataFrame, rate_col: str) -> tuple[float, float]:
    """Minutes-weighted linear fit rate ~ a + b * price within one position."""
    p = pool[(pool["total_minutes"] >= 90) & pool[rate_col].notna()]
    if len(p) < 5:
        return float(p[rate_col].mean()) if len(p) else 0.0, 0.0
    w = p["total_minutes"].to_numpy(float)
    x, y = p["cost_million"].to_numpy(float), p[rate_col].to_numpy(float)
    b, a = np.polyfit(x, y, 1, w=np.sqrt(w))
    return float(a), float(b)


def shrunk_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Per-90 rates blended with a price-implied position prior, weighted by minutes."""
    out = df.copy()
    k = PLAYER_PRIOR_MINUTES
    mins = out["total_minutes"].fillna(0).to_numpy(float)
    for rate, total in [("xg_90", "total_xg"), ("xa_90", "total_xa"),
                        ("bonus_90", "total_bonus_points"), ("saves_per_90", "total_saves")]:
        prior = np.zeros(len(out))
        for pos in POSITIONS:
            mask = (out["position_name"] == pos).to_numpy()
            a, b = _price_prior(out[mask], rate)
            prior[mask] = np.clip(a + b * out.loc[mask, "cost_million"].to_numpy(float), 0, None)
        observed = out[total].fillna(0).to_numpy(float)
        out[f"{rate}_model"] = (observed + prior * k / 90.0) / (mins + k) * 90.0

    # Defensive work doesn't scale with price, so its prior is the plain position average
    k_dc = DEFCON_PRIOR_MINUTES
    regulars = out[out["total_minutes"] >= 90]
    pos_rate = (regulars.groupby("position_name")["total_defensive_contribution"].sum() * 90.0
                / regulars.groupby("position_name")["total_minutes"].sum())
    prior_dc = out["position_name"].map(pos_rate).fillna(0.0).to_numpy(float)
    observed_dc = out["total_defensive_contribution"].fillna(0).to_numpy(float)
    out["dc_90_model"] = (observed_dc + prior_dc * k_dc / 90.0) / (mins + k_dc) * 90.0
    return out


def nb_at_least(threshold: int, mean, dispersion: float) -> np.ndarray:
    """P(X >= threshold) for X ~ NegativeBinomial(mean, dispersion r); var = mean + mean^2 / r."""
    mean = np.asarray(mean, dtype=float)
    r = float(dispersion)
    p = r / (r + np.clip(mean, 1e-9, None))
    log_p, log_q = np.log(p), np.log1p(-p)
    cdf = np.zeros_like(mean)
    for k in range(threshold):
        cdf += np.exp(math.lgamma(k + r) - math.lgamma(r) - math.lgamma(k + 1) + r * log_p + k * log_q)
    return np.clip(1.0 - cdf, 0.0, 1.0)


def _availability(row: pd.Series) -> float:
    chance = row.get("chance_of_playing_next_round")
    if pd.notna(chance):
        return float(chance) / 100.0
    return 1.0 if row.get("availability_status", "a") == "a" else 0.0


def _expected_floor_half(lam: float, kmax: int = 12) -> float:
    """E[floor(G/2)] for G ~ Poisson(lam): the expected goals-conceded deduction."""
    k = np.arange(kmax + 1)
    pmf = np.exp(-lam) * lam ** k / np.array([math.factorial(int(i)) for i in k], dtype=float)
    return float((np.floor(k / 2) * pmf).sum())


# ─── Fixture-level expected points ──────────────────────────────────────────

def upcoming_fixtures(fixtures: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, list[int]]:
    """Unplayed fixtures in the next `horizon` gameweeks, one row per team-fixture."""
    future = fixtures[~fixtures["is_finished"]]
    if future.empty:
        return pd.DataFrame(), []
    first = int(future["gameweek"].min())
    gws = list(range(first, first + horizon))
    f = future[future["gameweek"].isin(gws)]
    home = pd.DataFrame({
        "gameweek": f.gameweek, "team_id": f.home_team_id, "opp_id": f.away_team_id,
        "opp_short": f.away_team_short_name, "is_home": True, "fdr": f.home_difficulty,
    })
    away = pd.DataFrame({
        "gameweek": f.gameweek, "team_id": f.away_team_id, "opp_id": f.home_team_id,
        "opp_short": f.home_team_short_name, "is_home": False, "fdr": f.away_difficulty,
    })
    return pd.concat([home, away], ignore_index=True), gws


def fixture_outlook(team_fx: pd.DataFrame, ratings: pd.DataFrame, mu: float) -> pd.DataFrame:
    """Adds expected goals for/against and clean-sheet probability to each team-fixture."""
    r = ratings.set_index("team_id")
    fx = team_fx.copy()
    venue = np.where(fx["is_home"], HOME_ADV, 1 / HOME_ADV)
    fx["team_lambda"] = mu * fx["team_id"].map(r["attack"]).to_numpy() * fx["opp_id"].map(r["defence"]).to_numpy() * venue
    fx["opp_lambda"] = mu * fx["opp_id"].map(r["attack"]).to_numpy() * fx["team_id"].map(r["defence"]).to_numpy() / venue
    fx["cs_prob"] = np.exp(-fx["opp_lambda"])
    fx["attack_factor"] = fx["team_lambda"] / (mu * fx["team_id"].map(r["attack"]).to_numpy())
    fx["opp_attack"] = fx["opp_id"].map(r["attack"]).to_numpy()
    return fx


def project_points(players: pd.DataFrame, outlook: pd.DataFrame, mu: float) -> pd.DataFrame:
    """
    Expected FPL points per player per upcoming fixture, broken into scoring components.
    Returns long format: player_id, gameweek, opponent, xpts + one column per component.
    """
    p = shrunk_rates(players)
    p["p_play"] = p["gw_played"] / p["n_gw_observed"]
    p["p60"] = p["gw_60"] / p["n_gw_observed"]
    p["avail"] = p.apply(_availability, axis=1)

    m = outlook.merge(
        p[["player_id", "web_name", "team_id", "position_name", "cost_million",
           "xg_90_model", "xa_90_model", "bonus_90_model", "saves_per_90_model", "dc_90_model",
           "p_play", "p60", "avail", "mins_per_app", "mins_full", "mins_cameo"]],
        on="team_id",
    )
    first_gw = m["gameweek"].min()
    # Availability flags apply to the next GW; later GWs drift back toward fully fit.
    steps = (m["gameweek"] - first_gw).clip(upper=3) / 3.0
    avail = m["avail"] + (1 - m["avail"]) * steps
    p_play = m["p_play"] * avail
    p60 = m["p60"] * avail
    mins_frac = p_play * m["mins_per_app"].clip(upper=90) / 90.0
    pos = m["position_name"]

    m["Appearance"] = 2 * p60 + 1 * (p_play - p60).clip(lower=0)
    m["Goals"] = m["xg_90_model"] * m["attack_factor"] * mins_frac * pos.map(GOAL_PTS)
    m["Assists"] = m["xa_90_model"] * m["attack_factor"] * mins_frac * ASSIST_PTS
    m["Clean sheet"] = p60 * m["cs_prob"] * pos.map(CS_PTS)
    m["Saves"] = np.where(pos == "GKP", m["saves_per_90_model"] * m["opp_attack"] * mins_frac / 3.0, 0.0)
    m["Bonus"] = m["bonus_90_model"] * mins_frac
    # DefCon: per-match count ~ NegBin(rate x minutes), evaluated separately for full games and cameos
    # because the threshold is a cliff. p_defcon = P(hit | the player features).
    p_cameo = (p_play - p60).clip(lower=0)
    m["p_defcon"] = 0.0
    m["Def. contribution"] = 0.0
    for p_name, thr in DEFCON_THRESHOLD.items():
        sel = pos == p_name
        rate = m.loc[sel, "dc_90_model"] / 90.0
        hit_full = nb_at_least(thr, rate * m.loc[sel, "mins_full"].clip(upper=90), DEFCON_DISPERSION[p_name])
        hit_cameo = nb_at_least(thr, rate * m.loc[sel, "mins_cameo"], DEFCON_DISPERSION[p_name])
        expected_hits = p60[sel] * hit_full + p_cameo[sel] * hit_cameo
        m.loc[sel, "Def. contribution"] = DEFCON_PTS * expected_hits
        m.loc[sel, "p_defcon"] = np.where(p_play[sel] > 0, expected_hits / p_play[sel].clip(lower=1e-9), 0.0)
    gc_ded = m["opp_lambda"].map(_expected_floor_half)
    m["Goals conceded"] = np.where(pos.isin(["GKP", "DEF"]), -gc_ded * p60, 0.0)
    m["xpts"] = m[XPTS_COMPONENTS].sum(axis=1)
    # Probability of at least one goal involvement (haul potential)
    m["p_return"] = 1 - np.exp(-(m["xg_90_model"] + m["xa_90_model"]) * m["attack_factor"] * mins_frac)
    m["opponent"] = m["opp_short"] + np.where(m["is_home"], " (H)", " (A)")
    return m


def projection_summary(proj: pd.DataFrame, gws: list[int]) -> pd.DataFrame:
    """Wide table: total xPts over horizon + per-GW xPts (doubles summed, blanks = 0)."""
    if proj.empty:
        return pd.DataFrame(columns=["player_id", "xpts_total", "xpts_next"])
    wide = proj.pivot_table(index="player_id", columns="gameweek", values="xpts", aggfunc="sum").reindex(columns=gws).fillna(0.0)
    wide.columns = [f"GW{c}" for c in wide.columns]
    wide["xpts_total"] = wide.sum(axis=1)
    wide["xpts_next"] = wide[f"GW{gws[0]}"]
    first = proj[proj["gameweek"] == gws[0]].groupby("player_id")
    nxt = first["p_return"].max().rename("p_return_next")
    dc_next = first["p_defcon"].max().rename("p_defcon_next")
    dc_total = proj.groupby("player_id")["Def. contribution"].sum().rename("xpts_defcon")
    return wide.join(nxt).join(dc_next).join(dc_total).reset_index()


# ─── Plain-English scout notes ──────────────────────────────────────────────

def scout_notes(player: pd.Series, pct: pd.DataFrame, min_minutes: int, pool_size: int) -> list[str]:
    notes = []
    mins = int(player.get("total_minutes", 0) or 0)
    if mins < 450:
        notes.append(f"⚠️ **Small sample** — {mins} mins logged. Percentiles are indicative until ~450+ mins; "
                     "the xPts model leans on the price-implied prior to compensate.")

    valid = pct.dropna(subset=["percentile"])
    elite = valid[valid["percentile"] >= 80].sort_values("percentile", ascending=False)
    weak = valid[valid["percentile"] <= 25].sort_values("percentile")
    pos = player["position_name"]
    if not elite.empty:
        items = ", ".join(f"**{r.label}** ({r.display}, top {100 - r.percentile:.0f}%)" for r in elite.head(3).itertuples())
        notes.append(f"💪 Strengths vs {pool_size} {pos}s: {items}.")
    if not weak.empty:
        items = ", ".join(f"**{r.label}** ({r.display} — {r.explain})" for r in weak.head(3).itertuples())
        notes.append(f"🔻 Weak spots: {items}.")

    delta = player.get("xgi_delta")
    if pd.notna(delta) and abs(delta) >= 1.0:
        if delta < 0:
            notes.append(f"📉 Returns trail underlying numbers by **{abs(delta):.1f}** G+A vs xGI — "
                         "finishing variance usually corrects, so output should catch up if the chances keep coming.")
        else:
            notes.append(f"📈 Running **{delta:.1f}** G+A above xGI — some of that is likely finishing luck; "
                         "expect returns to cool unless chance volume rises.")

    hit = player.get("defcon_hit_rate")
    if pos != "GKP" and pd.notna(hit) and hit >= 0.4 and player.get("appearances", 0) >= 3:
        thr = DEFCON_THRESHOLD[pos]
        notes.append(f"🛡️ Defensive-contribution banker: reached {thr}+ actions in **{hit:.0%}** of games "
                     f"({player['dc_90']:.1f}/90), worth about **{DEFCON_PTS * hit:.1f} pts a game** that "
                     "goals-and-assists stats don't show.")

    if pd.notna(player.get("xpts_total")) and pd.notna(player.get("xpts_rank_pos")):
        notes.append(f"🗓️ Model projects **{player['xpts_total']:.1f} xPts** over the planning horizon "
                     f"(#{int(player['xpts_rank_pos'])} among {pos}s), next up {player.get('next_opponent', 'TBD')}.")
    if player.get("selected_by_percent", 100) < 5 and player.get("xpts_rank_pos", 99) <= 15:
        notes.append(f"🕵️ Owned by only **{player['selected_by_percent']:.1f}%** — a genuine differential for its projection.")
    return notes
