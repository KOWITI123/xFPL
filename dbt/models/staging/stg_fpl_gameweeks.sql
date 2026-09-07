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

unnested_events AS (
    SELECT
        snapshot_date,
        source_file,
        event
    FROM raw_source,
    UNNEST(JSON_EXTRACT_ARRAY(data, '$.events')) AS event
)

SELECT
    CAST(JSON_VALUE(event, '$.id') AS INT64) AS gameweek,
    JSON_VALUE(event, '$.name') AS gameweek_name,
    SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', JSON_VALUE(event, '$.deadline_time')) AS deadline_time,
    CAST(JSON_VALUE(event, '$.finished') AS BOOL) AS is_finished,
    CAST(JSON_VALUE(event, '$.is_current') AS BOOL) AS is_current,
    CAST(JSON_VALUE(event, '$.is_next') AS BOOL) AS is_next,
    CAST(JSON_VALUE(event, '$.average_entry_score') AS INT64) AS average_score,
    CAST(JSON_VALUE(event, '$.highest_score') AS INT64) AS highest_score,
    CAST(JSON_VALUE(event, '$.transfers_made') AS INT64) AS transfers_made,
    CAST(JSON_VALUE(event, '$.most_selected') AS INT64) AS most_selected_player_id,
    CAST(JSON_VALUE(event, '$.most_transferred_in') AS INT64) AS most_transferred_in_player_id,
    CAST(JSON_VALUE(event, '$.top_element') AS INT64) AS top_element_player_id,
    snapshot_date,
    source_file
FROM unnested_events
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY CAST(JSON_VALUE(event, '$.id') AS INT64)
    ORDER BY snapshot_date DESC
) = 1
