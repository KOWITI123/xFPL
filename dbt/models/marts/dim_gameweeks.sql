SELECT
    gameweek,
    gameweek_name,
    deadline_time,
    is_finished,
    is_current,
    is_next,
    average_score,
    highest_score,
    transfers_made,
    most_selected_player_id,
    most_transferred_in_player_id,
    top_element_player_id,
    snapshot_date AS updated_at
FROM {{ ref('stg_fpl_gameweeks') }}
