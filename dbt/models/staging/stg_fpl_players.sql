WITH raw_source AS (
    SELECT
        data,
        _file_name AS source_file,
        COALESCE(
            SAFE.PARSE_DATE('%Y-%m-%d', REGEXP_EXTRACT(_file_name, r'fpl_snapshot_(\d{4}-\d{2}-\d{2})')),
            CURRENT_DATE()
        ) AS snapshot_date
    FROM {{ source('fpl_raw', 'raw_fpl_bootstrap') }}
),

unnested_elements AS (
    SELECT
        snapshot_date,
        source_file,
        element
    FROM raw_source,
    UNNEST(JSON_EXTRACT_ARRAY(data, '$.elements')) AS element
)

SELECT
    CAST(JSON_VALUE(element, '$.id') AS INT64) AS player_id,
    TRIM(CONCAT(
        COALESCE(JSON_VALUE(element, '$.first_name'), ''), ' ',
        COALESCE(JSON_VALUE(element, '$.second_name'), '')
    )) AS full_name,
    JSON_VALUE(element, '$.first_name') AS first_name,
    JSON_VALUE(element, '$.second_name') AS second_name,
    JSON_VALUE(element, '$.web_name') AS web_name,
    CAST(JSON_VALUE(element, '$.team') AS INT64) AS team_id,
    CAST(JSON_VALUE(element, '$.element_type') AS INT64) AS position_id,
    CASE CAST(JSON_VALUE(element, '$.element_type') AS INT64)
        WHEN 1 THEN 'GKP'
        WHEN 2 THEN 'DEF'
        WHEN 3 THEN 'MID'
        WHEN 4 THEN 'FWD'
        ELSE 'UNKNOWN'
    END AS position_name,
    CAST(JSON_VALUE(element, '$.now_cost') AS INT64) / 10.0 AS cost_million,
    SAFE_CAST(JSON_VALUE(element, '$.selected_by_percent') AS FLOAT64) AS selected_by_percent,
    SAFE_CAST(JSON_VALUE(element, '$.form') AS FLOAT64) AS form,
    SAFE_CAST(JSON_VALUE(element, '$.points_per_game') AS FLOAT64) AS points_per_game,
    CAST(JSON_VALUE(element, '$.total_points') AS INT64) AS total_points,
    CAST(JSON_VALUE(element, '$.event_points') AS INT64) AS event_points,
    CAST(JSON_VALUE(element, '$.transfers_in_event') AS INT64) AS transfers_in_event,
    CAST(JSON_VALUE(element, '$.transfers_out_event') AS INT64) AS transfers_out_event,
    JSON_VALUE(element, '$.status') AS availability_status,
    SAFE_CAST(JSON_VALUE(element, '$.chance_of_playing_next_round') AS INT64) AS chance_of_playing_next_round,
    CAST(JSON_VALUE(element, '$.minutes') AS INT64) AS minutes,
    CAST(JSON_VALUE(element, '$.goals_scored') AS INT64) AS goals_scored,
    CAST(JSON_VALUE(element, '$.assists') AS INT64) AS assists,
    CAST(JSON_VALUE(element, '$.clean_sheets') AS INT64) AS clean_sheets,
    CAST(JSON_VALUE(element, '$.goals_conceded') AS INT64) AS goals_conceded,
    CAST(JSON_VALUE(element, '$.own_goals') AS INT64) AS own_goals,
    CAST(JSON_VALUE(element, '$.penalties_saved') AS INT64) AS penalties_saved,
    CAST(JSON_VALUE(element, '$.penalties_missed') AS INT64) AS penalties_missed,
    CAST(JSON_VALUE(element, '$.yellow_cards') AS INT64) AS yellow_cards,
    CAST(JSON_VALUE(element, '$.red_cards') AS INT64) AS red_cards,
    CAST(JSON_VALUE(element, '$.saves') AS INT64) AS saves,
    CAST(JSON_VALUE(element, '$.bonus') AS INT64) AS bonus_points,
    CAST(JSON_VALUE(element, '$.bps') AS INT64) AS bps,
    SAFE_CAST(JSON_VALUE(element, '$.influence') AS FLOAT64) AS influence,
    SAFE_CAST(JSON_VALUE(element, '$.creativity') AS FLOAT64) AS creativity,
    SAFE_CAST(JSON_VALUE(element, '$.threat') AS FLOAT64) AS threat,
    SAFE_CAST(JSON_VALUE(element, '$.ict_index') AS FLOAT64) AS ict_index,
    SAFE_CAST(JSON_VALUE(element, '$.expected_goals') AS FLOAT64) AS fpl_expected_goals,
    SAFE_CAST(JSON_VALUE(element, '$.expected_assists') AS FLOAT64) AS fpl_expected_assists,
    SAFE_CAST(JSON_VALUE(element, '$.expected_goal_involvements') AS FLOAT64) AS fpl_expected_goal_involvements,
    SAFE_CAST(JSON_VALUE(element, '$.expected_goals_conceded') AS FLOAT64) AS fpl_expected_goals_conceded,
    snapshot_date,
    source_file
FROM unnested_elements
