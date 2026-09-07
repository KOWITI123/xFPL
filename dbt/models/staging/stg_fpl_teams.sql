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

unnested_teams AS (
    SELECT
        snapshot_date,
        source_file,
        team
    FROM raw_source,
    UNNEST(JSON_EXTRACT_ARRAY(data, '$.teams')) AS team
)

SELECT
    CAST(JSON_VALUE(team, '$.id') AS INT64) AS team_id,
    JSON_VALUE(team, '$.name') AS team_name,
    JSON_VALUE(team, '$.short_name') AS short_name,
    CAST(JSON_VALUE(team, '$.code') AS INT64) AS team_code,
    CAST(JSON_VALUE(team, '$.strength') AS INT64) AS strength_overall,
    CAST(JSON_VALUE(team, '$.strength_overall_home') AS INT64) AS strength_overall_home,
    CAST(JSON_VALUE(team, '$.strength_overall_away') AS INT64) AS strength_overall_away,
    CAST(JSON_VALUE(team, '$.strength_attack_home') AS INT64) AS strength_attack_home,
    CAST(JSON_VALUE(team, '$.strength_attack_away') AS INT64) AS strength_attack_away,
    CAST(JSON_VALUE(team, '$.strength_defence_home') AS INT64) AS strength_defence_home,
    CAST(JSON_VALUE(team, '$.strength_defence_away') AS INT64) AS strength_defence_away,
    CAST(JSON_VALUE(team, '$.pulse_id') AS INT64) AS pulse_id,
    snapshot_date,
    source_file
FROM unnested_teams
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY CAST(JSON_VALUE(team, '$.id') AS INT64)
    ORDER BY snapshot_date DESC
) = 1
