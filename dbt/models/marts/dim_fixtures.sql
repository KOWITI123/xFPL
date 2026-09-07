SELECT
    f.fixture_id,
    f.gameweek,
    f.kickoff_time,
    f.match_date,
    f.home_team_id,
    th.team_name AS home_team_name,
    th.short_name AS home_team_short_name,
    f.away_team_id,
    ta.team_name AS away_team_name,
    ta.short_name AS away_team_short_name,
    f.home_team_score,
    f.away_team_score,
    f.home_difficulty,
    f.away_difficulty,
    f.is_finished,
    f.is_started,
    f.minutes_played,
    f.snapshot_date AS updated_at
FROM {{ ref('stg_fpl_fixtures') }} f
LEFT JOIN {{ ref('stg_fpl_teams') }} th ON f.home_team_id = th.team_id
LEFT JOIN {{ ref('stg_fpl_teams') }} ta ON f.away_team_id = ta.team_id
