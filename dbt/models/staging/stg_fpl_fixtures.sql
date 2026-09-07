WITH raw_source AS (
    SELECT
        data,
        _file_name AS source_file,
        COALESCE(
            SAFE.PARSE_DATE('%Y-%m-%d', REGEXP_EXTRACT(_file_name, r'fpl_fixtures_(\d{4}-\d{2}-\d{2})')),
            CURRENT_DATE()
        ) AS snapshot_date
    FROM {{ source('fpl_raw', 'raw_fpl_fixtures') }}
),

unnested_fixtures AS (
    SELECT
        snapshot_date,
        source_file,
        fixture
    FROM raw_source,
    UNNEST(JSON_EXTRACT_ARRAY(data, '$')) AS fixture
)

SELECT
    CAST(JSON_VALUE(fixture, '$.id') AS INT64) AS fixture_id,
    CAST(JSON_VALUE(fixture, '$.event') AS INT64) AS gameweek,
    SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', JSON_VALUE(fixture, '$.kickoff_time')) AS kickoff_time,
    DATE(SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', JSON_VALUE(fixture, '$.kickoff_time'))) AS match_date,
    CAST(JSON_VALUE(fixture, '$.team_h') AS INT64) AS home_team_id,
    CAST(JSON_VALUE(fixture, '$.team_a') AS INT64) AS away_team_id,
    CAST(JSON_VALUE(fixture, '$.team_h_score') AS INT64) AS home_team_score,
    CAST(JSON_VALUE(fixture, '$.team_a_score') AS INT64) AS away_team_score,
    CAST(JSON_VALUE(fixture, '$.team_h_difficulty') AS INT64) AS home_difficulty,
    CAST(JSON_VALUE(fixture, '$.team_a_difficulty') AS INT64) AS away_difficulty,
    CAST(JSON_VALUE(fixture, '$.finished') AS BOOL) AS is_finished,
    CAST(JSON_VALUE(fixture, '$.started') AS BOOL) AS is_started,
    CAST(JSON_VALUE(fixture, '$.minutes') AS INT64) AS minutes_played,
    snapshot_date,
    source_file
FROM unnested_fixtures
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY CAST(JSON_VALUE(fixture, '$.id') AS INT64)
    ORDER BY snapshot_date DESC
) = 1
