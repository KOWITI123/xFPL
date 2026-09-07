{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['fpl_player_id', 'gameweek'],
    partition_by={
      "field": "gameweek",
      "data_type": "int64",
      "range": {
        "start": 1,
        "end": 39,
        "interval": 1
      }
    },
    cluster_by=['team_id', 'fpl_player_id']
) }}

WITH live_stats AS (
    SELECT *
    FROM {{ ref('stg_fpl_live') }}
    {% if is_incremental() %}
    WHERE gameweek >= (SELECT COALESCE(MAX(gameweek), 1) FROM {{ this }})
    {% endif %}
),

player_dim AS (
    SELECT
        player_id,
        team_id,
        position_id,
        position_name,
        cost_million
    FROM {{ ref('dim_players') }}
),

crossref AS (
    SELECT *
    FROM {{ ref('dim_player_crossref') }}
),

fixtures AS (
    SELECT
        gameweek,
        home_team_id,
        away_team_id,
        match_date
    FROM {{ ref('dim_fixtures') }}
),

understat_gw AS (
    SELECT
        cr.fpl_player_id,
        fix.gameweek,
        SUM(und.xg) AS understat_xg,
        SUM(und.xa) AS understat_xa,
        SUM(und.npxg) AS understat_npxg,
        SUM(und.shots) AS understat_shots,
        SUM(und.key_passes) AS understat_key_passes,
        SUM(und.xg_chain) AS understat_xg_chain,
        SUM(und.xg_buildup) AS understat_xg_buildup
    FROM {{ ref('stg_understat_matches') }} und
    JOIN crossref cr ON und.understat_player_name = cr.understat_player_name
    JOIN fixtures fix ON und.match_date = fix.match_date
    GROUP BY cr.fpl_player_id, fix.gameweek
),

fbref_season AS (
    SELECT
        cr.fpl_player_id,
        fb.goals_against AS fbref_goals_against,
        fb.goals_against_per_90 AS fbref_ga90,
        fb.shots_on_target_against AS fbref_sota,
        fb.fbref_saves,
        fb.fbref_save_pct,
        fb.fbref_clean_sheets,
        fb.fbref_clean_sheet_pct,
        fb.pk_faced AS fbref_pk_faced,
        fb.pk_saved AS fbref_pk_saved,
        fb.fbref_shots,
        fb.shots_on_target AS fbref_shots_on_target,
        fb.shots_on_target_pct AS fbref_sot_pct,
        fb.tackles_won AS fbref_tackles_won,
        fb.interceptions AS fbref_interceptions,
        fb.crosses AS fbref_crosses,
        fb.fouls_committed AS fbref_fouls_committed,
        fb.fouls_drawn AS fbref_fouls_drawn,
        fb.offsides AS fbref_offsides,
        fb.penalties_won AS fbref_penalties_won,
        fb.penalties_conceded AS fbref_penalties_conceded,
        fb.own_goals AS fbref_own_goals
    FROM {{ ref('stg_fbref_season') }} fb
    JOIN crossref cr ON fb.fbref_player_name = cr.fbref_player_name
)

SELECT
    l.player_id AS fpl_player_id,
    l.gameweek,
    p.team_id,
    p.position_id,
    p.position_name,
    p.cost_million,
    l.minutes,
    l.total_points AS fpl_points,
    l.goals_scored,
    l.assists,
    l.clean_sheets,
    l.goals_conceded,
    l.bonus_points,
    l.bps,
    l.influence,
    l.creativity,
    l.threat,
    l.ict_index,

    -- GKP / DEF relevant fields
    l.saves,
    l.penalties_saved,
    l.penalties_missed,
    l.own_goals,
    COALESCE(l.expected_goals_conceded, 0.0) AS expected_goals_conceded,

    -- Underlying Advanced Metrics (attacking)
    COALESCE(u.understat_xg, l.expected_goals, 0.0) AS xg,
    COALESCE(u.understat_xa, l.expected_assists, 0.0) AS xa,
    COALESCE(u.understat_npxg, u.understat_xg, l.expected_goals, 0.0) AS npxg,
    COALESCE(u.understat_shots, 0) AS shots,
    COALESCE(u.understat_key_passes, 0) AS key_passes,
    COALESCE(u.understat_xg_chain, 0.0) AS xg_chain,
    COALESCE(u.understat_xg_buildup, 0.0) AS xg_buildup,

    -- Combined Expected Goal Involvement (xGI)
    (COALESCE(u.understat_xg, l.expected_goals, 0.0) + COALESCE(u.understat_xa, l.expected_assists, 0.0)) AS xgi,

    -- Deltas: Over/Underperformance Variance (attacking)
    ROUND(l.goals_scored - COALESCE(u.understat_xg, l.expected_goals, 0.0), 2) AS xg_delta,
    ROUND(l.assists - COALESCE(u.understat_xa, l.expected_assists, 0.0), 2) AS xa_delta,
    ROUND((l.goals_scored + l.assists) - (COALESCE(u.understat_xg, l.expected_goals, 0.0) + COALESCE(u.understat_xa, l.expected_assists, 0.0)), 2) AS xgi_delta,

    -- Defensive Delta: xGC over/underperformance (GKP/DEF — negative = outperforming)
    ROUND(l.goals_conceded - COALESCE(l.expected_goals_conceded, 0.0), 2) AS xgc_delta,

    -- Standardized Per-90 Rates (attacking)
    CASE
        WHEN l.minutes > 0 THEN ROUND((COALESCE(u.understat_xg, l.expected_goals, 0.0) + COALESCE(u.understat_xa, l.expected_assists, 0.0)) * 90.0 / l.minutes, 2)
        ELSE 0.0
    END AS xgi_per_90,

    -- Shot Quality (npxG per shot)
    CASE
        WHEN COALESCE(u.understat_shots, 0) > 0 THEN ROUND(COALESCE(u.understat_npxg, u.understat_xg, l.expected_goals, 0.0) / u.understat_shots, 2)
        ELSE 0.0
    END AS npxg_per_shot,

    -- BPS Generation Rate
    CASE
        WHEN l.minutes > 0 THEN ROUND(l.bps * 90.0 / l.minutes, 1)
        ELSE 0.0
    END AS bps_per_90,

    -- GKP: Saves per 90
    CASE
        WHEN l.minutes > 0 THEN ROUND(l.saves * 90.0 / l.minutes, 2)
        ELSE 0.0
    END AS saves_per_90,

    -- DEF/GKP: Goals conceded per 90
    CASE
        WHEN l.minutes > 0 THEN ROUND(l.goals_conceded * 90.0 / l.minutes, 2)
        ELSE 0.0
    END AS goals_conceded_per_90,

    -- FWD/MID: Conversion rate (goals / shots)
    CASE
        WHEN COALESCE(u.understat_shots, 0) > 0 THEN ROUND(l.goals_scored * 1.0 / u.understat_shots, 2)
        ELSE 0.0
    END AS conversion_rate,

    -- Verified FBRef season metrics (available when cross-referenced)
    fb.fbref_sota,
    fb.fbref_save_pct,
    fb.fbref_shots_on_target,
    fb.fbref_sot_pct,
    fb.fbref_tackles_won,
    fb.fbref_interceptions,
    fb.fbref_crosses,
    fb.fbref_fouls_committed

FROM live_stats l
LEFT JOIN player_dim p ON l.player_id = p.player_id
LEFT JOIN understat_gw u ON l.player_id = u.fpl_player_id AND l.gameweek = u.gameweek
LEFT JOIN fbref_season fb ON l.player_id = fb.fpl_player_id
