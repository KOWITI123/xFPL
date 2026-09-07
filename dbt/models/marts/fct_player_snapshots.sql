{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['player_id', 'snapshot_date'],
    partition_by={
      "field": "snapshot_date",
      "data_type": "date",
      "granularity": "day"
    },
    cluster_by=['player_id', 'team_id']
) }}

SELECT
    player_id,
    snapshot_date,
    team_id,
    position_id,
    position_name,
    cost_million,
    selected_by_percent,
    form,
    points_per_game,
    total_points,
    event_points,
    transfers_in_event,
    transfers_out_event,
    transfers_in_event - transfers_out_event AS net_transfers_event,
    availability_status,
    chance_of_playing_next_round,
    minutes,
    goals_scored,
    assists,
    clean_sheets,
    goals_conceded,
    bonus_points,
    bps,
    influence,
    creativity,
    threat,
    ict_index,
    fpl_expected_goals,
    fpl_expected_assists,
    fpl_expected_goal_involvements,
    fpl_expected_goals_conceded
FROM {{ ref('stg_fpl_players') }}

{% if is_incremental() %}
WHERE snapshot_date >= (SELECT MAX(snapshot_date) FROM {{ this }})
{% endif %}
