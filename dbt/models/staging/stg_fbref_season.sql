{#
  FBRef ingestion is disabled by default: the soccerdata scraper needs a Chrome
  binary the Kestra container does not have, so every raw_fbref_* file in GCS is an
  error row. Enable with `dbt build --vars '{enable_fbref: true}'` once it is fixed.
  When disabled this model returns zero rows with the same schema, so the crossref
  and marts build normally with NULL FBRef columns.
#}
{% if var('enable_fbref', false) %}

WITH raw_standard AS (
    SELECT
        TRIM(player) AS fbref_player_name,
        TRIM(team) AS fbref_team_name,
        SAFE_CAST(playing_time_mp AS INT64) AS matches_played,
        SAFE_CAST(playing_time_min AS INT64) AS minutes_played,
        SAFE_CAST(performance_gls AS INT64) AS goals,
        SAFE_CAST(performance_ast AS INT64) AS assists,
        SAFE_CAST(performance_crdy AS INT64) AS yellow_cards,
        SAFE_CAST(performance_crdr AS INT64) AS red_cards
    FROM {{ source('fpl_raw', 'raw_fbref_standard') }}
    WHERE player IS NOT NULL AND player != 'player'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY TRIM(player), TRIM(team) ORDER BY SAFE_CAST(playing_time_min AS INT64) DESC) = 1
),

raw_keeper AS (
    SELECT
        TRIM(player) AS fbref_player_name,
        TRIM(team) AS fbref_team_name,
        SAFE_CAST(performance_ga AS INT64) AS goals_against,
        SAFE_CAST(performance_ga90 AS FLOAT64) AS goals_against_per_90,
        SAFE_CAST(performance_sota AS INT64) AS shots_on_target_against,
        SAFE_CAST(performance_saves AS INT64) AS saves,
        SAFE_CAST(REPLACE(CAST(performance_save_pct AS STRING), '%', '') AS FLOAT64) AS save_pct,
        SAFE_CAST(performance_cs AS INT64) AS clean_sheets,
        SAFE_CAST(REPLACE(CAST(performance_cs_pct AS STRING), '%', '') AS FLOAT64) AS clean_sheet_pct,
        SAFE_CAST(penalty_kicks_pkatt AS INT64) AS pk_faced,
        SAFE_CAST(penalty_kicks_pksv AS INT64) AS pk_saved
    FROM {{ source('fpl_raw', 'raw_fbref_keeper') }}
    WHERE player IS NOT NULL AND player != 'player'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY TRIM(player), TRIM(team) ORDER BY SAFE_CAST(performance_saves AS INT64) DESC) = 1
),

raw_shooting AS (
    SELECT
        TRIM(player) AS fbref_player_name,
        TRIM(team) AS fbref_team_name,
        SAFE_CAST(standard_sh AS INT64) AS shots,
        SAFE_CAST(standard_sot AS INT64) AS shots_on_target,
        SAFE_CAST(REPLACE(CAST(standard_sot_pct AS STRING), '%', '') AS FLOAT64) AS shots_on_target_pct
    FROM {{ source('fpl_raw', 'raw_fbref_shooting') }}
    WHERE player IS NOT NULL AND player != 'player'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY TRIM(player), TRIM(team) ORDER BY SAFE_CAST(standard_sh AS INT64) DESC) = 1
),

raw_misc AS (
    SELECT
        TRIM(player) AS fbref_player_name,
        TRIM(team) AS fbref_team_name,
        SAFE_CAST(performance_tklw AS INT64) AS tackles_won,
        SAFE_CAST(performance_int AS INT64) AS interceptions,
        SAFE_CAST(performance_crs AS INT64) AS crosses,
        SAFE_CAST(performance_fls AS INT64) AS fouls_committed,
        SAFE_CAST(performance_fld AS INT64) AS fouls_drawn,
        SAFE_CAST(performance_off AS INT64) AS offsides,
        SAFE_CAST(performance_pkwon AS INT64) AS penalties_won,
        SAFE_CAST(performance_pkcon AS INT64) AS penalties_conceded,
        SAFE_CAST(performance_og AS INT64) AS own_goals
    FROM {{ source('fpl_raw', 'raw_fbref_misc') }}
    WHERE player IS NOT NULL AND player != 'player'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY TRIM(player), TRIM(team) ORDER BY SAFE_CAST(performance_tklw AS INT64) DESC) = 1
)

SELECT
    s.fbref_player_name,
    s.fbref_team_name,
    COALESCE(s.matches_played, 0) AS matches_played,
    COALESCE(s.minutes_played, 0) AS minutes_played,
    COALESCE(s.goals, 0) AS goals,
    COALESCE(s.assists, 0) AS assists,
    COALESCE(s.yellow_cards, 0) AS yellow_cards,
    COALESCE(s.red_cards, 0) AS red_cards,

    -- Goalkeeper metrics
    k.goals_against,
    k.goals_against_per_90,
    k.shots_on_target_against,
    k.saves AS fbref_saves,
    k.save_pct AS fbref_save_pct,
    k.clean_sheets AS fbref_clean_sheets,
    k.clean_sheet_pct AS fbref_clean_sheet_pct,
    k.pk_faced,
    k.pk_saved,

    -- Shooting metrics
    sh.shots AS fbref_shots,
    sh.shots_on_target,
    sh.shots_on_target_pct,

    -- Misc / Defensive metrics
    COALESCE(m.tackles_won, 0) AS tackles_won,
    COALESCE(m.interceptions, 0) AS interceptions,
    COALESCE(m.crosses, 0) AS crosses,
    COALESCE(m.fouls_committed, 0) AS fouls_committed,
    COALESCE(m.fouls_drawn, 0) AS fouls_drawn,
    COALESCE(m.offsides, 0) AS offsides,
    COALESCE(m.penalties_won, 0) AS penalties_won,
    COALESCE(m.penalties_conceded, 0) AS penalties_conceded,
    COALESCE(m.own_goals, 0) AS own_goals,

    -- Backward compatibility aliases
    CAST(COALESCE(m.tackles_won, 0) AS FLOAT64) AS tackles,
    CAST(0.0 AS FLOAT64) AS blocks,
    CAST(0.0 AS FLOAT64) AS clearances,
    CAST(0.0 AS FLOAT64) AS passes_completed,
    CAST(0.0 AS FLOAT64) AS passes_attempted,
    CAST(0.0 AS FLOAT64) AS progressive_passes,
    CAST(0.0 AS FLOAT64) AS passes_into_final_third,
    CAST(0.0 AS FLOAT64) AS touches,
    CAST(0.0 AS FLOAT64) AS progressive_carries,
    CAST(0.0 AS FLOAT64) AS touches_in_box,
    CAST(0.0 AS FLOAT64) AS take_ons,
    CAST(0.0 AS FLOAT64) AS take_ons_won,
    CAST(0.0 AS FLOAT64) AS shot_creating_actions,
    CAST(0.0 AS FLOAT64) AS goal_creating_actions

FROM raw_standard s
LEFT JOIN raw_keeper k
    ON s.fbref_player_name = k.fbref_player_name AND s.fbref_team_name = k.fbref_team_name
LEFT JOIN raw_shooting sh
    ON s.fbref_player_name = sh.fbref_player_name AND s.fbref_team_name = sh.fbref_team_name
LEFT JOIN raw_misc m
    ON s.fbref_player_name = m.fbref_player_name AND s.fbref_team_name = m.fbref_team_name

{% else %}

SELECT
    CAST(NULL AS STRING) AS fbref_player_name,
    CAST(NULL AS STRING) AS fbref_team_name,
    CAST(NULL AS INT64) AS matches_played,
    CAST(NULL AS INT64) AS minutes_played,
    CAST(NULL AS INT64) AS goals,
    CAST(NULL AS INT64) AS assists,
    CAST(NULL AS INT64) AS yellow_cards,
    CAST(NULL AS INT64) AS red_cards,
    CAST(NULL AS INT64) AS goals_against,
    CAST(NULL AS INT64) AS shots_on_target_against,
    CAST(NULL AS INT64) AS fbref_saves,
    CAST(NULL AS INT64) AS fbref_clean_sheets,
    CAST(NULL AS INT64) AS pk_faced,
    CAST(NULL AS INT64) AS pk_saved,
    CAST(NULL AS INT64) AS fbref_shots,
    CAST(NULL AS INT64) AS shots_on_target,
    CAST(NULL AS INT64) AS tackles_won,
    CAST(NULL AS INT64) AS interceptions,
    CAST(NULL AS INT64) AS crosses,
    CAST(NULL AS INT64) AS fouls_committed,
    CAST(NULL AS INT64) AS fouls_drawn,
    CAST(NULL AS INT64) AS offsides,
    CAST(NULL AS INT64) AS penalties_won,
    CAST(NULL AS INT64) AS penalties_conceded,
    CAST(NULL AS INT64) AS own_goals,
    CAST(NULL AS FLOAT64) AS goals_against_per_90,
    CAST(NULL AS FLOAT64) AS fbref_save_pct,
    CAST(NULL AS FLOAT64) AS fbref_clean_sheet_pct,
    CAST(NULL AS FLOAT64) AS shots_on_target_pct,
    CAST(NULL AS FLOAT64) AS tackles,
    CAST(NULL AS FLOAT64) AS blocks,
    CAST(NULL AS FLOAT64) AS clearances,
    CAST(NULL AS FLOAT64) AS passes_completed,
    CAST(NULL AS FLOAT64) AS passes_attempted,
    CAST(NULL AS FLOAT64) AS progressive_passes,
    CAST(NULL AS FLOAT64) AS passes_into_final_third,
    CAST(NULL AS FLOAT64) AS touches,
    CAST(NULL AS FLOAT64) AS progressive_carries,
    CAST(NULL AS FLOAT64) AS touches_in_box,
    CAST(NULL AS FLOAT64) AS take_ons,
    CAST(NULL AS FLOAT64) AS take_ons_won,
    CAST(NULL AS FLOAT64) AS shot_creating_actions,
    CAST(NULL AS FLOAT64) AS goal_creating_actions
LIMIT 0

{% endif %}
