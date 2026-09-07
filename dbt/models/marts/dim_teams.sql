SELECT
    team_id,
    team_name,
    short_name,
    team_code,
    strength_overall,
    strength_overall_home,
    strength_overall_away,
    strength_attack_home,
    strength_attack_away,
    strength_defence_home,
    strength_defence_away,
    pulse_id,
    snapshot_date AS updated_at
FROM {{ ref('stg_fpl_teams') }}
