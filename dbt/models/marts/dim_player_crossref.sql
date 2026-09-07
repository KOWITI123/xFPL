WITH all_fpl_players AS (
    SELECT
        p.player_id AS fpl_player_id,
        p.full_name AS fpl_full_name,
        p.web_name AS fpl_web_name,
        t.team_name AS fpl_team_name,
        {{ normalize_name('p.full_name') }} AS norm_full_name
    FROM {{ ref('stg_fpl_players') }} p
    JOIN {{ ref('stg_fpl_teams') }} t ON p.team_id = t.team_id
    QUALIFY ROW_NUMBER() OVER (PARTITION BY p.player_id ORDER BY p.snapshot_date DESC) = 1
),

overrides AS (
    SELECT
        SAFE_CAST(fpl_player_id AS INT64) AS fpl_player_id,
        fpl_full_name,
        {{ normalize_name('fpl_full_name') }} AS norm_override_name,
        TRIM(understat_name) AS understat_player_name,
        TRIM(fbref_name) AS fbref_player_name,
        'manual_override' AS match_method,
        1.0 AS confidence_score
    FROM {{ ref('player_overrides') }}
),

deterministic AS (
    SELECT * FROM {{ ref('int_player_deterministic') }}
),

fuzzy AS (
    SELECT * FROM {{ ref('int_player_fuzzy') }}
)

SELECT
    fpl.fpl_player_id,
    fpl.fpl_full_name,
    fpl.fpl_web_name,
    fpl.fpl_team_name,
    COALESCE(ovr.understat_player_name, det.understat_player_name, fuz.understat_player_name) AS understat_player_name,
    COALESCE(det.understat_player_id, fuz.understat_player_id) AS understat_player_id,
    COALESCE(ovr.fbref_player_name, det.fbref_player_name, fuz.fbref_player_name) AS fbref_player_name,
    CASE
        WHEN (ovr.understat_player_name IS NOT NULL OR ovr.fbref_player_name IS NOT NULL) THEN 'manual_override'
        WHEN det.fpl_player_id IS NOT NULL THEN 'deterministic'
        WHEN fuz.fpl_player_id IS NOT NULL THEN 'fuzzy'
        ELSE 'unmatched'
    END AS match_method,
    COALESCE(
        CASE WHEN (ovr.understat_player_name IS NOT NULL OR ovr.fbref_player_name IS NOT NULL) THEN 1.0 END,
        det.confidence_score,
        fuz.confidence_score,
        0.0
    ) AS confidence_score
FROM all_fpl_players fpl
LEFT JOIN overrides ovr
    ON (fpl.fpl_player_id = ovr.fpl_player_id OR fpl.norm_full_name = ovr.norm_override_name)
LEFT JOIN deterministic det
    ON fpl.fpl_player_id = det.fpl_player_id
    AND ovr.understat_player_name IS NULL AND ovr.fbref_player_name IS NULL
LEFT JOIN fuzzy fuz
    ON fpl.fpl_player_id = fuz.fpl_player_id
    AND ovr.understat_player_name IS NULL AND ovr.fbref_player_name IS NULL
    AND det.fpl_player_id IS NULL
