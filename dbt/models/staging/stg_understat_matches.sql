WITH raw_source AS (
    SELECT
        *
    FROM {{ source('fpl_raw', 'raw_understat_matches') }}
    WHERE player IS NOT NULL
)

SELECT
    SAFE_CAST(player_id AS INT64) AS understat_player_id,
    TRIM(player) AS understat_player_name,
    TRIM(team) AS understat_team_name,
    SAFE.PARSE_DATE('%Y-%m-%d', SUBSTR(game, 1, 10)) AS match_date,
    SAFE_CAST(game_id AS INT64) AS match_id,
    TRIM(position) AS position,
    SAFE_CAST(minutes AS INT64) AS minutes_played,
    SAFE_CAST(goals AS INT64) AS goals,
    SAFE_CAST(assists AS INT64) AS assists,
    SAFE_CAST(shots AS INT64) AS shots,
    SAFE_CAST(key_passes AS INT64) AS key_passes,
    SAFE_CAST(yellow_cards AS INT64) AS yellow_cards,
    SAFE_CAST(red_cards AS INT64) AS red_cards,
    SAFE_CAST(xg AS FLOAT64) AS xg,
    SAFE_CAST(xa AS FLOAT64) AS xa,
    SAFE_CAST(xg AS FLOAT64) AS npxg,
    SAFE_CAST(xg_chain AS FLOAT64) AS xg_chain,
    SAFE_CAST(xg_buildup AS FLOAT64) AS xg_buildup,
    CURRENT_DATE() AS snapshot_date
FROM raw_source
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY TRIM(player), TRIM(team), SAFE.PARSE_DATE('%Y-%m-%d', SUBSTR(game, 1, 10))
    ORDER BY SAFE_CAST(minutes AS INT64) DESC
) = 1
