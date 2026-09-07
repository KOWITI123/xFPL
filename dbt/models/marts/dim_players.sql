WITH latest_fpl_players AS (
    SELECT
        p.*
    FROM {{ ref('stg_fpl_players') }} p
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY p.player_id
        ORDER BY p.snapshot_date DESC
    ) = 1
),

teams AS (
    SELECT * FROM {{ ref('stg_fpl_teams') }}
),

crossref AS (
    SELECT * FROM {{ ref('dim_player_crossref') }}
)

SELECT
    p.player_id,
    p.full_name,
    p.first_name,
    p.second_name,
    p.web_name,
    p.team_id,
    t.team_name,
    t.short_name AS team_short_name,
    p.position_id,
    p.position_name,
    p.cost_million,
    p.selected_by_percent,
    p.availability_status,
    p.chance_of_playing_next_round,
    cr.understat_player_id,
    cr.understat_player_name,
    cr.fbref_player_name,
    cr.match_method AS crossref_match_method,
    cr.confidence_score AS crossref_confidence_score,
    p.snapshot_date AS updated_at
FROM latest_fpl_players p
LEFT JOIN teams t ON p.team_id = t.team_id
LEFT JOIN crossref cr ON p.player_id = cr.fpl_player_id
