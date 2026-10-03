WITH raw_source AS (
    SELECT
        data,
        _file_name AS source_file,
        COALESCE(
            CAST(JSON_VALUE(data, '$._gameweek') AS INT64),
            SAFE_CAST(REGEXP_EXTRACT(_file_name, r'gw_(\d+)_live') AS INT64)
        ) AS gameweek,
        COALESCE(
            SAFE.PARSE_DATE('%Y-%m-%d', REGEXP_EXTRACT(_file_name, r'(\d{4}-\d{2}-\d{2})\.json')),
            CURRENT_DATE()
        ) AS snapshot_date
    FROM {{ source('fpl_raw', 'raw_fpl_gameweek_live') }}
),

unnested_elements AS (
    SELECT
        gameweek,
        snapshot_date,
        source_file,
        player
    FROM raw_source,
    UNNEST(JSON_EXTRACT_ARRAY(data, '$.elements')) AS player
)

SELECT
    CAST(JSON_VALUE(player, '$.id') AS INT64) AS player_id,
    gameweek,
    CAST(JSON_VALUE(player, '$.stats.minutes') AS INT64) AS minutes,
    CAST(JSON_VALUE(player, '$.stats.total_points') AS INT64) AS total_points,
    CAST(JSON_VALUE(player, '$.stats.goals_scored') AS INT64) AS goals_scored,
    CAST(JSON_VALUE(player, '$.stats.assists') AS INT64) AS assists,
    CAST(JSON_VALUE(player, '$.stats.clean_sheets') AS INT64) AS clean_sheets,
    CAST(JSON_VALUE(player, '$.stats.goals_conceded') AS INT64) AS goals_conceded,
    CAST(JSON_VALUE(player, '$.stats.own_goals') AS INT64) AS own_goals,
    CAST(JSON_VALUE(player, '$.stats.penalties_saved') AS INT64) AS penalties_saved,
    CAST(JSON_VALUE(player, '$.stats.penalties_missed') AS INT64) AS penalties_missed,
    CAST(JSON_VALUE(player, '$.stats.yellow_cards') AS INT64) AS yellow_cards,
    CAST(JSON_VALUE(player, '$.stats.red_cards') AS INT64) AS red_cards,
    CAST(JSON_VALUE(player, '$.stats.saves') AS INT64) AS saves,
    CAST(JSON_VALUE(player, '$.stats.bonus') AS INT64) AS bonus_points,
    CAST(JSON_VALUE(player, '$.stats.bps') AS INT64) AS bps,
    SAFE_CAST(JSON_VALUE(player, '$.stats.influence') AS FLOAT64) AS influence,
    SAFE_CAST(JSON_VALUE(player, '$.stats.creativity') AS FLOAT64) AS creativity,
    SAFE_CAST(JSON_VALUE(player, '$.stats.threat') AS FLOAT64) AS threat,
    SAFE_CAST(JSON_VALUE(player, '$.stats.ict_index') AS FLOAT64) AS ict_index,
    SAFE_CAST(JSON_VALUE(player, '$.stats.expected_goals') AS FLOAT64) AS expected_goals,
    SAFE_CAST(JSON_VALUE(player, '$.stats.expected_assists') AS FLOAT64) AS expected_assists,
    SAFE_CAST(JSON_VALUE(player, '$.stats.expected_goal_involvements') AS FLOAT64) AS expected_goal_involvements,
    SAFE_CAST(JSON_VALUE(player, '$.stats.expected_goals_conceded') AS FLOAT64) AS expected_goals_conceded,

    -- Defensive contributions (FPL 2025/26+): DEF score 2 pts at 10+ CBIT
    -- (clearances, blocks, interceptions, tackles); MID/FWD at 12+ CBIRT (CBIT + recoveries).
    -- defensive_contribution is FPL's position-specific count.
    SAFE_CAST(JSON_VALUE(player, '$.stats.tackles') AS INT64) AS tackles,
    SAFE_CAST(JSON_VALUE(player, '$.stats.clearances_blocks_interceptions') AS INT64) AS clearances_blocks_interceptions,
    SAFE_CAST(JSON_VALUE(player, '$.stats.recoveries') AS INT64) AS recoveries,
    SAFE_CAST(JSON_VALUE(player, '$.stats.defensive_contribution') AS INT64) AS defensive_contribution,
    -- Points actually awarded, read per fixture from the explain block (correct in double gameweeks)
    COALESCE((
        SELECT SUM(SAFE_CAST(JSON_VALUE(stat, '$.points') AS INT64))
        FROM UNNEST(JSON_EXTRACT_ARRAY(player, '$.explain')) AS fixture_explain,
             UNNEST(JSON_EXTRACT_ARRAY(fixture_explain, '$.stats')) AS stat
        WHERE JSON_VALUE(stat, '$.identifier') = 'defensive_contribution'
    ), 0) AS defensive_contribution_points,
    snapshot_date,
    source_file
FROM unnested_elements
WHERE gameweek IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY CAST(JSON_VALUE(player, '$.id') AS INT64), gameweek
    ORDER BY snapshot_date DESC
) = 1
