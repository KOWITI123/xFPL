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

unmatched_fpl AS (
    SELECT fpl.*
    FROM fpl_players fpl
    LEFT JOIN {{ ref('int_player_deterministic') }} det
        ON fpl.fpl_player_id = det.fpl_player_id
    WHERE det.fpl_player_id IS NULL
),

understat_candidates AS (
    SELECT DISTINCT
        understat_player_id,
        understat_player_name,
        understat_team_name,
        {{ normalize_team_name('understat_team_name') }} AS std_team_name,
        {{ normalize_name('understat_player_name') }} AS norm_player_name
    FROM {{ ref('stg_understat_matches') }}
    WHERE understat_player_name NOT IN (
        SELECT understat_player_name FROM {{ ref('int_player_deterministic') }}
        WHERE understat_player_name IS NOT NULL
    )
),

fbref_candidates AS (
    SELECT DISTINCT
        fbref_player_name,
        fbref_team_name,
        {{ normalize_team_name('fbref_team_name') }} AS std_team_name,
        {{ normalize_name('fbref_player_name') }} AS norm_player_name
    FROM {{ ref('stg_fbref_season') }}
    WHERE fbref_player_name NOT IN (
        SELECT fbref_player_name FROM {{ ref('int_player_deterministic') }}
        WHERE fbref_player_name IS NOT NULL
    )
),

fuzzy_understat AS (
    SELECT
        u.fpl_player_id,
        und.understat_player_id,
        und.understat_player_name,
        -- EDIT_DISTANCE caps its result at max_distance, so the cap must sit above the
        -- accept threshold (3) or every pair would look like a match.
        LEAST(
            EDIT_DISTANCE(u.norm_full_name, und.norm_player_name, max_distance => 4),
            EDIT_DISTANCE(u.norm_web_name, und.norm_player_name, max_distance => 4)
        ) AS dist_und,
        CASE WHEN u.std_team_name = und.std_team_name THEN 0 ELSE 1 END AS team_diff
    FROM unmatched_fpl u
    JOIN understat_candidates und
        ON (
            (u.std_team_name = und.std_team_name AND (
                EDIT_DISTANCE(u.norm_full_name, und.norm_player_name, max_distance => 4) <= LEAST(3, DIV(LENGTH(und.norm_player_name), 4))
                OR EDIT_DISTANCE(u.norm_web_name, und.norm_player_name, max_distance => 4) <= LEAST(3, DIV(LENGTH(und.norm_player_name), 4))
            ))
            OR (u.norm_full_name = und.norm_player_name)
        )
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY u.fpl_player_id
        ORDER BY team_diff ASC, dist_und ASC
    ) = 1
    -- Mutual best match: a source player can only be claimed by its closest FPL player
    AND ROW_NUMBER() OVER (
        PARTITION BY und.understat_player_name
        ORDER BY team_diff ASC, dist_und ASC
    ) = 1
),

fuzzy_fbref AS (
    SELECT
        u.fpl_player_id,
        fbr.fbref_player_name,
        LEAST(
            EDIT_DISTANCE(u.norm_full_name, fbr.norm_player_name, max_distance => 4),
            EDIT_DISTANCE(u.norm_web_name, fbr.norm_player_name, max_distance => 4)
        ) AS dist_fbr,
        CASE WHEN u.std_team_name = fbr.std_team_name THEN 0 ELSE 1 END AS team_diff
    FROM unmatched_fpl u
    JOIN fbref_candidates fbr
        ON (
            (u.std_team_name = fbr.std_team_name AND (
                EDIT_DISTANCE(u.norm_full_name, fbr.norm_player_name, max_distance => 4) <= LEAST(3, DIV(LENGTH(fbr.norm_player_name), 4))
                OR EDIT_DISTANCE(u.norm_web_name, fbr.norm_player_name, max_distance => 4) <= LEAST(3, DIV(LENGTH(fbr.norm_player_name), 4))
            ))
            OR (u.norm_full_name = fbr.norm_player_name)
        )
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY u.fpl_player_id
        ORDER BY team_diff ASC, dist_fbr ASC
    ) = 1
    AND ROW_NUMBER() OVER (
        PARTITION BY fbr.fbref_player_name
        ORDER BY team_diff ASC, dist_fbr ASC
    ) = 1
)

SELECT
    u.fpl_player_id,
    u.fpl_full_name,
    u.fpl_team_name,
    fu.understat_player_id,
    fu.understat_player_name,
    ff.fbref_player_name,
    'fuzzy' AS match_method,
    ROUND(GREATEST(0.5, 1.0 - (COALESCE(NULLIF(fu.dist_und, 99), NULLIF(ff.dist_fbr, 99), 2) / 10.0)), 2) AS confidence_score
FROM unmatched_fpl u
LEFT JOIN fuzzy_understat fu ON u.fpl_player_id = fu.fpl_player_id
LEFT JOIN fuzzy_fbref ff ON u.fpl_player_id = ff.fpl_player_id
WHERE fu.understat_player_name IS NOT NULL OR ff.fbref_player_name IS NOT NULL
