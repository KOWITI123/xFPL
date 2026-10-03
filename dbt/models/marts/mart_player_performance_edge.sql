/*
  mart_player_performance_edge.sql
  Season-to-date + rolling form analytics with position-specific metrics,
  regression signals, and edge badges for GKP / DEF / MID / FWD.
  Integrates verified underlying metrics from FPL, Understat, and FBRef.
*/

WITH player_facts AS (
    SELECT
        fpl_player_id,
        team_id,
        position_name,
        cost_million,
        gameweek,
        minutes,
        fpl_points,
        goals_scored,
        assists,
        clean_sheets,
        goals_conceded,
        bonus_points,
        bps,
        saves,
        penalties_saved,
        expected_goals_conceded,
        defensive_contribution,
        defensive_contribution_points,
        xg,
        xa,
        npxg,
        xgi,
        shots,
        key_passes,
        xg_chain,
        xg_buildup,
        xgc_delta,
        conversion_rate,
        fbref_sota,
        fbref_save_pct,
        fbref_shots_on_target,
        fbref_sot_pct,
        fbref_tackles_won,
        fbref_interceptions,
        fbref_crosses,
        fbref_fouls_committed
    FROM {{ ref('fct_player_underlying') }}
),

-- ─── Season Aggregates ───────────────────────────────────────────────
season_agg AS (
    SELECT
        fpl_player_id,
        team_id,
        position_name,
        cost_million,
        COUNT(DISTINCT gameweek) AS matches_played,
        COUNTIF(minutes > 0) AS appearances,
        SUM(defensive_contribution) AS total_defensive_contribution,
        SUM(defensive_contribution_points) AS total_defensive_contribution_points,
        SUM(minutes) AS total_minutes,
        SUM(fpl_points) AS total_fpl_points,
        SUM(goals_scored) AS actual_goals,
        SUM(assists) AS actual_assists,
        SUM(clean_sheets) AS total_clean_sheets,
        SUM(goals_conceded) AS total_goals_conceded,
        SUM(saves) AS total_saves,
        SUM(penalties_saved) AS total_penalties_saved,
        SUM(shots) AS total_shots,
        SUM(key_passes) AS total_key_passes,
        SUM(bonus_points) AS total_bonus_points,
        SUM(bps) AS total_bps,
        ROUND(SUM(xg), 2) AS total_xg,
        ROUND(SUM(xa), 2) AS total_xa,
        ROUND(SUM(npxg), 2) AS total_npxg,
        ROUND(SUM(xgi), 2) AS total_xgi,
        ROUND(SUM(xg_chain), 2) AS total_xg_chain,
        ROUND(SUM(xg_buildup), 2) AS total_xg_buildup,
        ROUND(SUM(expected_goals_conceded), 2) AS total_xgc,
        ROUND(SUM(xgc_delta), 2) AS total_xgc_delta,
        MAX(fbref_sota) AS fbref_sota,
        MAX(fbref_save_pct) AS fbref_save_pct,
        MAX(fbref_shots_on_target) AS fbref_shots_on_target,
        MAX(fbref_sot_pct) AS fbref_sot_pct,
        MAX(fbref_tackles_won) AS fbref_tackles_won,
        MAX(fbref_interceptions) AS fbref_interceptions,
        MAX(fbref_crosses) AS fbref_crosses,
        MAX(fbref_fouls_committed) AS fbref_fouls_committed
    FROM player_facts
    GROUP BY fpl_player_id, team_id, position_name, cost_million
),

-- ─── Rolling Form Windows (3 GW & 5 GW) ─────────────────────────────
max_gw AS (
    SELECT MAX(gameweek) AS latest_gw FROM player_facts
),

rolling_form AS (
    SELECT
        pf.fpl_player_id,
        -- Last 3 gameweeks
        SUM(CASE WHEN pf.gameweek > mg.latest_gw - 3 THEN pf.fpl_points ELSE 0 END) AS rolling_3gw_points,
        ROUND(SUM(CASE WHEN pf.gameweek > mg.latest_gw - 3 THEN pf.xgi ELSE 0.0 END), 2) AS rolling_3gw_xgi,
        SUM(CASE WHEN pf.gameweek > mg.latest_gw - 3 THEN pf.minutes ELSE 0 END) AS rolling_3gw_minutes,
        SUM(CASE WHEN pf.gameweek > mg.latest_gw - 3 THEN pf.saves ELSE 0 END) AS rolling_3gw_saves,
        SUM(CASE WHEN pf.gameweek > mg.latest_gw - 3 THEN pf.goals_conceded ELSE 0 END) AS rolling_3gw_goals_conceded,
        SUM(CASE WHEN pf.gameweek > mg.latest_gw - 3 THEN pf.clean_sheets ELSE 0 END) AS rolling_3gw_clean_sheets,
        -- Last 5 gameweeks
        SUM(CASE WHEN pf.gameweek > mg.latest_gw - 5 THEN pf.fpl_points ELSE 0 END) AS rolling_5gw_points,
        ROUND(SUM(CASE WHEN pf.gameweek > mg.latest_gw - 5 THEN pf.xgi ELSE 0.0 END), 2) AS rolling_5gw_xgi,
        SUM(CASE WHEN pf.gameweek > mg.latest_gw - 5 THEN pf.minutes ELSE 0 END) AS rolling_5gw_minutes,
        SUM(CASE WHEN pf.gameweek > mg.latest_gw - 5 THEN pf.saves ELSE 0 END) AS rolling_5gw_saves,
        SUM(CASE WHEN pf.gameweek > mg.latest_gw - 5 THEN pf.goals_conceded ELSE 0 END) AS rolling_5gw_goals_conceded,
        SUM(CASE WHEN pf.gameweek > mg.latest_gw - 5 THEN pf.clean_sheets ELSE 0 END) AS rolling_5gw_clean_sheets
    FROM player_facts pf
    CROSS JOIN max_gw mg
    GROUP BY pf.fpl_player_id
),

-- ─── Team Totals (for talisman share) ────────────────────────────────
team_totals AS (
    SELECT
        team_id,
        SUM(total_xgi) AS team_total_xgi
    FROM season_agg
    GROUP BY team_id
),

-- ─── Player Dimension Lookup ─────────────────────────────────────────
player_dim AS (
    SELECT
        player_id,
        full_name,
        web_name,
        team_name,
        team_short_name,
        selected_by_percent,
        availability_status
    FROM {{ ref('dim_players') }}
)

SELECT
    p.player_id,
    p.full_name,
    p.web_name,
    p.team_name,
    p.team_short_name,
    s.position_name,
    s.cost_million,
    p.selected_by_percent,
    p.availability_status,
    s.matches_played,
    s.total_minutes,
    s.total_fpl_points,
    s.actual_goals,
    s.actual_assists,
    s.total_clean_sheets,
    s.total_goals_conceded,
    s.total_xg,
    s.total_xa,
    s.total_xgi,
    s.total_npxg,
    s.total_shots,
    s.total_key_passes,
    s.total_bonus_points,
    s.total_xg_chain,
    s.total_xg_buildup,

    -- ═══ GKP Metrics ════════════════════════════════════════════════
    s.total_saves,
    s.total_penalties_saved,
    s.total_xgc,
    s.total_xgc_delta,

    -- Saves per 90
    CASE WHEN s.total_minutes > 0 THEN ROUND(s.total_saves * 90.0 / s.total_minutes, 2) ELSE 0.0 END AS saves_per_90,

    -- Save percentage: saves / (saves + goals_conceded)
    CASE WHEN (s.total_saves + s.total_goals_conceded) > 0
         THEN ROUND(s.total_saves * 100.0 / (s.total_saves + s.total_goals_conceded), 1)
         ELSE 0.0
    END AS save_pct,

    -- FBRef Goalkeeper Context
    s.fbref_sota,
    s.fbref_save_pct,

    -- ═══ DEF / GKP Shared Metrics ═══════════════════════════════════
    -- Clean sheet rate
    CASE WHEN s.matches_played > 0
         THEN ROUND(s.total_clean_sheets * 1.0 / s.matches_played, 2)
         ELSE 0.0
    END AS clean_sheet_rate,

    -- Goals conceded per 90
    CASE WHEN s.total_minutes > 0
         THEN ROUND(s.total_goals_conceded * 90.0 / s.total_minutes, 2)
         ELSE 0.0
    END AS goals_conceded_per_90,

    -- ═══ Attacking Deltas (all positions) ═══════════════════════════
    ROUND(s.actual_goals - s.total_xg, 2) AS xg_delta,
    ROUND(s.actual_assists - s.total_xa, 2) AS xa_delta,
    ROUND((s.actual_goals + s.actual_assists) - s.total_xgi, 2) AS xgi_delta,
    -- npxG overperformance (FWD focused but computed for all)
    ROUND(s.actual_goals - s.total_npxg, 2) AS npxg_overperformance,

    -- ═══ Per-90 Rates ═══════════════════════════════════════════════
    CASE WHEN s.total_minutes > 0 THEN ROUND(s.total_xgi * 90.0 / s.total_minutes, 2) ELSE 0.0 END AS xgi_per_90,
    CASE WHEN s.total_minutes > 0 THEN ROUND(s.total_shots * 90.0 / s.total_minutes, 2) ELSE 0.0 END AS shots_per_90,
    CASE WHEN s.total_minutes > 0 THEN ROUND(s.total_key_passes * 90.0 / s.total_minutes, 2) ELSE 0.0 END AS key_passes_per_90,
    CASE WHEN s.total_minutes > 0 THEN ROUND(s.total_bps * 90.0 / s.total_minutes, 1) ELSE 0.0 END AS bps_per_90,

    -- ═══ Defensive Contribution points (DEF / MID / FWD) ═══════════
    s.appearances,
    s.total_defensive_contribution,
    s.total_defensive_contribution_points,
    CASE WHEN s.total_minutes > 0
         THEN ROUND(s.total_defensive_contribution * 90.0 / s.total_minutes, 2)
         ELSE 0.0
    END AS defensive_contribution_per_90,
    -- Share of appearances that hit the threshold (2 pts per hit)
    CASE WHEN s.appearances > 0
         THEN ROUND(s.total_defensive_contribution_points / 2.0 / s.appearances, 2)
         ELSE 0.0
    END AS defcon_hit_rate,

    -- ═══ MID / DEF: Defensive & Playmaking Work ═══════════════════════
    -- FBRef Defensive actions per 90
    CASE WHEN s.total_minutes > 0
         THEN ROUND(COALESCE(s.fbref_tackles_won, 0) * 90.0 / s.total_minutes, 2)
         ELSE 0.0
    END AS tackles_won_per_90,
    CASE WHEN s.total_minutes > 0
         THEN ROUND(COALESCE(s.fbref_interceptions, 0) * 90.0 / s.total_minutes, 2)
         ELSE 0.0
    END AS interceptions_per_90,
    CASE WHEN s.total_minutes > 0
         THEN ROUND(COALESCE(s.fbref_crosses, 0) * 90.0 / s.total_minutes, 2)
         ELSE 0.0
    END AS crosses_per_90,

    -- Chance creation per 90 (key passes per 90)
    CASE WHEN s.total_minutes > 0
         THEN ROUND(s.total_key_passes * 90.0 / s.total_minutes, 2)
         ELSE 0.0
    END AS chance_creation_per_90,

    -- Creative quality: xA per key pass
    CASE WHEN s.total_key_passes > 0
         THEN ROUND(s.total_xa / s.total_key_passes, 2)
         ELSE 0.0
    END AS xa_per_key_pass,

    -- Deep progression rate: xGBuildup per 90 (Holding MIDs / Ball-playing CBs)
    CASE WHEN s.total_minutes > 0
         THEN ROUND(s.total_xg_buildup * 90.0 / s.total_minutes, 2)
         ELSE 0.0
    END AS xg_buildup_per_90,

    -- ═══ FWD: Clinical Finishing & Shooting Context ═════════════════
    -- Conversion rate (goals / shots)
    CASE WHEN s.total_shots > 0
         THEN ROUND(s.actual_goals * 1.0 / s.total_shots, 2)
         ELSE 0.0
    END AS conversion_rate,

    -- Shot quality (npxG per shot)
    CASE WHEN s.total_shots > 0
         THEN ROUND(s.total_npxg / s.total_shots, 2)
         ELSE 0.0
    END AS npxg_per_shot,

    -- FBRef Shooting accuracy
    s.fbref_shots_on_target,
    s.fbref_sot_pct,

    -- ═══ Talisman / Centrality ══════════════════════════════════════
    CASE WHEN t.team_total_xgi > 0
         THEN ROUND(s.total_xgi * 100.0 / t.team_total_xgi, 1)
         ELSE 0.0
    END AS team_xgi_share_pct,

    -- ═══ Value Efficiency ═══════════════════════════════════════════
    CASE WHEN s.cost_million > 0 THEN ROUND(s.total_xgi / s.cost_million, 2) ELSE 0.0 END AS xgi_per_million,
    CASE WHEN s.cost_million > 0 THEN ROUND(s.total_fpl_points / s.cost_million, 1) ELSE 0.0 END AS points_per_million,

    -- ═══ Rolling Form ═══════════════════════════════════════════════
    r.rolling_3gw_points,
    r.rolling_3gw_xgi,
    r.rolling_5gw_points,
    r.rolling_5gw_xgi,
    -- Rolling GKP/DEF form
    r.rolling_3gw_saves,
    r.rolling_3gw_clean_sheets,
    r.rolling_5gw_saves,
    r.rolling_5gw_clean_sheets,
    -- Rolling saves per 90 (3 GW)
    CASE WHEN r.rolling_3gw_minutes > 0
         THEN ROUND(r.rolling_3gw_saves * 90.0 / r.rolling_3gw_minutes, 2)
         ELSE 0.0
    END AS rolling_3gw_saves_per_90,
    -- Rolling clean sheet rate (5 GW)
    CASE WHEN r.rolling_5gw_minutes > 0
         THEN ROUND(r.rolling_5gw_clean_sheets * 90.0 / r.rolling_5gw_minutes, 2)
         ELSE 0.0
    END AS rolling_5gw_cs_per_90,

    -- ═══ Position-Conditional Regression Signal ═════════════════════
    CASE
        -- GKP: unlucky keeper conceding more than expected despite high save rate
        WHEN s.position_name = 'GKP'
             AND s.total_xgc_delta > 2.0
             AND (s.total_saves + s.total_goals_conceded) > 0
             AND (s.total_saves * 100.0 / (s.total_saves + s.total_goals_conceded)) > 70.0
        THEN 'UNDERPERFORMING_BUY_TARGET'
        -- GKP: lucky keeper with high CS count despite negative xGC delta
        WHEN s.position_name = 'GKP'
             AND s.matches_played > 0
             AND (s.total_clean_sheets * 1.0 / s.matches_played) > 0.40
             AND s.total_xgc_delta < -2.0
        THEN 'OVERPERFORMING_SELL_RISK'
        -- DEF: poor CS record but stingy xGC = buy target
        WHEN s.position_name = 'DEF'
             AND s.matches_played > 0
             AND (s.total_clean_sheets * 1.0 / s.matches_played) < 0.20
             AND s.total_xgc_delta > 2.0
        THEN 'UNDERPERFORMING_BUY_TARGET'
        -- MID/FWD: standard xGI delta logic
        WHEN s.position_name IN ('MID', 'FWD')
             AND (s.actual_goals + s.actual_assists) - s.total_xgi <= -1.50
             AND s.total_minutes > 0
             AND (s.total_xgi * 90.0 / s.total_minutes) >= 0.40
        THEN 'UNDERPERFORMING_BUY_TARGET'
        WHEN s.position_name IN ('MID', 'FWD')
             AND (s.actual_goals + s.actual_assists) - s.total_xgi >= 2.50
             AND s.total_minutes > 0
             AND (s.total_xgi * 90.0 / s.total_minutes) <= 0.30
        THEN 'OVERPERFORMING_SELL_RISK'
        ELSE 'NEUTRAL'
    END AS regression_signal,

    -- ═══ Position-Conditional Edge Badge ════════════════════════════
    CASE
        -- GKP: sweeper keeper with attacking involvement
        WHEN s.position_name = 'GKP'
             AND s.total_minutes > 0
             AND (s.total_xgi * 90.0 / s.total_minutes) >= 0.05
        THEN 'GKP_SWEEPER_KEEPER'
        -- GKP/DEF: clean sheet machine
        WHEN s.position_name IN ('GKP', 'DEF')
             AND s.matches_played > 0
             AND (s.total_clean_sheets * 1.0 / s.matches_played) >= 0.45
        THEN 'CLEAN_SHEET_MACHINE'
        -- DEF: defensive rock — low goals conceded per 90 or high tackles/interceptions
        WHEN s.position_name = 'DEF'
             AND s.total_minutes > 0
             AND (
                 (s.total_goals_conceded * 90.0 / s.total_minutes) <= 0.80
                 OR (COALESCE(s.fbref_tackles_won, 0) + COALESCE(s.fbref_interceptions, 0)) * 90.0 / s.total_minutes >= 2.5
             )
        THEN 'DEFENSIVE_ROCK'
        -- DEF: out of position attacking threat
        WHEN s.position_name = 'DEF'
             AND s.total_minutes > 0
             AND (s.total_xgi * 90.0 / s.total_minutes) >= 0.20
        THEN 'OUT_OF_POSITION_THREAT'
        -- MID: creative engine
        WHEN s.position_name = 'MID'
             AND s.total_minutes > 0
             AND (s.total_key_passes * 90.0 / s.total_minutes) >= 2.5
        THEN 'CREATIVE_ENGINE'
        -- FWD: clinical finisher
        WHEN s.position_name = 'FWD'
             AND s.total_shots >= 15
             AND s.actual_goals > 0
             AND (
                 (s.actual_goals * 1.0 / s.total_shots) >= 0.20
                 OR COALESCE(s.fbref_sot_pct, 0.0) >= 50.0
             )
        THEN 'CLINICAL_FINISHER'
        -- Any position: budget talisman
        WHEN s.cost_million <= 6.5
             AND s.cost_million > 0
             AND (s.total_xgi / s.cost_million) >= 0.80
        THEN 'BUDGET_TALISMAN'
        -- Any position: elite premium
        WHEN s.cost_million >= 9.5
             AND s.total_minutes > 0
             AND (s.total_xgi * 90.0 / s.total_minutes) >= 0.65
        THEN 'ELITE_PREMIUM'
        ELSE 'ROTATION_OR_STANDARD'
    END AS edge_badge

FROM season_agg s
JOIN player_dim p ON s.fpl_player_id = p.player_id
JOIN team_totals t ON s.team_id = t.team_id
LEFT JOIN rolling_form r ON s.fpl_player_id = r.fpl_player_id
