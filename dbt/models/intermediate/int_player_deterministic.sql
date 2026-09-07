WITH fpl_players AS (
    SELECT
        p.player_id AS fpl_player_id,
        p.full_name AS fpl_full_name,
        p.web_name AS fpl_web_name,
        p.team_id AS fpl_team_id,
        t.team_name AS fpl_team_name,
        {{ normalize_team_name('t.team_name') }} AS std_team_name,
        {{ normalize_name('p.full_name') }} AS norm_full_name,
        {{ normalize_name('p.web_name') }} AS norm_web_name
    FROM {{ ref('stg_fpl_players') }} p
    JOIN {{ ref('stg_fpl_teams') }} t ON p.team_id = t.team_id
    QUALIFY ROW_NUMBER() OVER (PARTITION BY p.player_id ORDER BY p.snapshot_date DESC) = 1
),

understat_players AS (
    SELECT DISTINCT
        understat_player_id,
        understat_player_name,
        understat_team_name,
        {{ normalize_team_name('understat_team_name') }} AS std_team_name,
        {{ normalize_name('understat_player_name') }} AS norm_player_name
    FROM {{ ref('stg_understat_matches') }}
),

fbref_players AS (
    SELECT DISTINCT
        fbref_player_name,
        fbref_team_name,
        {{ normalize_team_name('fbref_team_name') }} AS std_team_name,
        {{ normalize_name('fbref_player_name') }} AS norm_player_name
    FROM {{ ref('stg_fbref_season') }}
),

matched_understat AS (
    SELECT
        fpl.fpl_player_id,
        und.understat_player_id,
        und.understat_player_name,
        CASE
            WHEN fpl.norm_full_name = und.norm_player_name THEN 1
            WHEN fpl.norm_web_name = und.norm_player_name THEN 2
            WHEN ARRAY_TO_STRING(ARRAY_REVERSE(SPLIT(fpl.norm_full_name, ' ')), ' ') = und.norm_player_name THEN 3
            WHEN fpl.norm_full_name LIKE CONCAT(und.norm_player_name, ' %') THEN 4
            WHEN fpl.norm_full_name LIKE CONCAT('% ', und.norm_player_name) THEN 5
            WHEN fpl.norm_full_name LIKE CONCAT('% ', und.norm_player_name, ' %') THEN 6
            ELSE 7
        END AS match_rank
    FROM fpl_players fpl
    JOIN understat_players und
        ON fpl.std_team_name = und.std_team_name
        AND (
            fpl.norm_full_name = und.norm_player_name
            OR fpl.norm_web_name = und.norm_player_name
            OR ARRAY_TO_STRING(ARRAY_REVERSE(SPLIT(fpl.norm_full_name, ' ')), ' ') = und.norm_player_name
            OR (LENGTH(und.norm_player_name) >= 4 AND (
                fpl.norm_full_name LIKE CONCAT(und.norm_player_name, ' %')
                OR fpl.norm_full_name LIKE CONCAT('% ', und.norm_player_name)
                OR fpl.norm_full_name LIKE CONCAT('% ', und.norm_player_name, ' %')
            ))
        )
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY fpl.fpl_player_id
        ORDER BY match_rank ASC, LENGTH(und.norm_player_name) DESC
    ) = 1
),

matched_fbref AS (
    SELECT
        fpl.fpl_player_id,
        fbr.fbref_player_name,
        CASE
            WHEN fpl.norm_full_name = fbr.norm_player_name THEN 1
            WHEN fpl.norm_web_name = fbr.norm_player_name THEN 2
            WHEN ARRAY_TO_STRING(ARRAY_REVERSE(SPLIT(fpl.norm_full_name, ' ')), ' ') = fbr.norm_player_name THEN 3
            WHEN fbr.norm_player_name LIKE CONCAT(fpl.norm_full_name, ' %') THEN 4
            WHEN fpl.norm_full_name LIKE CONCAT(fbr.norm_player_name, ' %') THEN 5
            WHEN fpl.norm_full_name LIKE CONCAT('% ', fbr.norm_player_name) THEN 6
            WHEN fpl.norm_full_name LIKE CONCAT('% ', fbr.norm_player_name, ' %') THEN 7
            ELSE 8
        END AS match_rank
    FROM fpl_players fpl
    JOIN fbref_players fbr
        ON fpl.std_team_name = fbr.std_team_name
        AND (
            fpl.norm_full_name = fbr.norm_player_name
            OR fpl.norm_web_name = fbr.norm_player_name
            OR ARRAY_TO_STRING(ARRAY_REVERSE(SPLIT(fpl.norm_full_name, ' ')), ' ') = fbr.norm_player_name
            OR (LENGTH(fbr.norm_player_name) >= 4 AND (
                fbr.norm_player_name LIKE CONCAT(fpl.norm_full_name, ' %')
                OR fpl.norm_full_name LIKE CONCAT(fbr.norm_player_name, ' %')
                OR fpl.norm_full_name LIKE CONCAT('% ', fbr.norm_player_name)
                OR fpl.norm_full_name LIKE CONCAT('% ', fbr.norm_player_name, ' %')
            ))
        )
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY fpl.fpl_player_id
        ORDER BY match_rank ASC, LENGTH(fbr.norm_player_name) DESC
    ) = 1
)

SELECT
    fpl.fpl_player_id,
    fpl.fpl_full_name,
    fpl.fpl_team_name,
    mu.understat_player_id,
    mu.understat_player_name,
    mf.fbref_player_name,
    'deterministic' AS match_method,
    1.0 AS confidence_score
FROM fpl_players fpl
LEFT JOIN matched_understat mu ON fpl.fpl_player_id = mu.fpl_player_id
LEFT JOIN matched_fbref mf ON fpl.fpl_player_id = mf.fpl_player_id
WHERE mu.understat_player_name IS NOT NULL OR mf.fbref_player_name IS NOT NULL
