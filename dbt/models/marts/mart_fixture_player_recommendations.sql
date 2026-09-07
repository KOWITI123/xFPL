/*
  mart_fixture_player_recommendations.sql
  Decision mart: combines underlying performance edge with upcoming fixture
  difficulty, market arbitrage signals, and a position-conditional composite
  xFPL edge score. Includes position_rank for within-position comparison.
*/

WITH edge_stats AS (
    SELECT * FROM {{ ref('mart_player_performance_edge') }}
),

next_fixtures AS (
    SELECT
        f.gameweek,
        f.fixture_id,
        f.match_date,
        f.home_team_id,
        f.away_team_id,
        f.home_team_name,
        f.away_team_name,
        f.home_difficulty,
        f.away_difficulty
    FROM {{ ref('dim_fixtures') }} f
    WHERE f.is_finished = FALSE
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY f.home_team_id
        ORDER BY f.gameweek ASC, f.kickoff_time ASC
    ) = 1
),

dim_players AS (
    SELECT
        player_id,
        team_id
    FROM {{ ref('dim_players') }}
),

player_upcoming AS (
    SELECT
        e.*,
        dp.team_id,
        CASE
            WHEN dp.team_id = nf_home.home_team_id THEN 'HOME'
            WHEN dp.team_id = nf_away.away_team_id THEN 'AWAY'
            ELSE 'NO_FIXTURE'
        END AS venue,
        CASE
            WHEN dp.team_id = nf_home.home_team_id THEN nf_home.away_team_name
            WHEN dp.team_id = nf_away.away_team_id THEN nf_away.home_team_name
            ELSE 'TBD'
        END AS next_opponent,
        CASE
            WHEN dp.team_id = nf_home.home_team_id THEN nf_home.home_difficulty
            WHEN dp.team_id = nf_away.away_team_id THEN nf_away.away_difficulty
            ELSE 3
        END AS fixture_difficulty_rating
    FROM edge_stats e
    JOIN dim_players dp ON e.player_id = dp.player_id
    LEFT JOIN next_fixtures nf_home ON dp.team_id = nf_home.home_team_id
    LEFT JOIN next_fixtures nf_away ON dp.team_id = nf_away.away_team_id
),

scored AS (
    SELECT
        player_id,
        full_name,
        web_name,
        team_name,
        position_name,
        cost_million,
        selected_by_percent,
        availability_status,
        total_fpl_points,
        matches_played,

        -- Core per-90 stats
        xgi_per_90,
        shots_per_90,
        key_passes_per_90,
        npxg_per_shot,
        bps_per_90,
        team_xgi_share_pct,
        xgi_per_million,
        points_per_million,

        -- Deltas
        xg_delta,
        xa_delta,
        xgi_delta,
        npxg_overperformance,

        -- GKP / DEF metrics
        total_saves,
        total_penalties_saved,
        saves_per_90,
        save_pct,
        clean_sheet_rate,
        goals_conceded_per_90,
        total_xgc_delta,

        -- MID creative metrics
        chance_creation_per_90,
        xa_per_key_pass,

        -- FWD clinical metrics
        conversion_rate,

        -- Rolling form
        rolling_3gw_points,
        rolling_3gw_xgi,
        rolling_5gw_points,
        rolling_5gw_xgi,
        rolling_3gw_saves,
        rolling_3gw_clean_sheets,
        rolling_5gw_saves,
        rolling_5gw_clean_sheets,
        rolling_3gw_saves_per_90,
        rolling_5gw_cs_per_90,

        -- Signals and badges
        regression_signal,
        edge_badge,

        -- Fixture context
        next_opponent,
        venue,
        fixture_difficulty_rating,

        -- FDR multiplier
        CASE fixture_difficulty_rating
            WHEN 1 THEN 1.30
            WHEN 2 THEN 1.15
            WHEN 3 THEN 1.00
            WHEN 4 THEN 0.85
            WHEN 5 THEN 0.70
            ELSE 1.00
        END AS fdr_multiplier,

        -- ═══ Position-Conditional Composite xFPL Edge Score (0–100) ═══
        ROUND(
            LEAST(100.0, GREATEST(0.0,
                CASE
                    -- GKP: weighted toward save %, xGC outperformance, CS rate, FDR
                    WHEN position_name = 'GKP' THEN
                        (COALESCE(save_pct, 0.0) * 0.40) +                           -- save % contributes up to ~40 pts
                        (GREATEST(-5.0, LEAST(5.0, COALESCE(-total_xgc_delta, 0.0))) * 4.0) +  -- xGC outperformance ±20 pts
                        (COALESCE(clean_sheet_rate, 0.0) * 25.0) +                    -- CS rate up to ~12.5 pts
                        ((6 - COALESCE(fixture_difficulty_rating, 3)) * 5.0) +         -- FDR ±15 pts
                        (COALESCE(saves_per_90, 0.0) * 3.0)                           -- saves volume bonus

                    -- DEF: weighted toward CS rate, xGC, attacking upside, FDR
                    WHEN position_name = 'DEF' THEN
                        (COALESCE(clean_sheet_rate, 0.0) * 30.0) +                    -- CS rate up to ~15 pts
                        (GREATEST(-5.0, LEAST(5.0, COALESCE(-total_xgc_delta, 0.0))) * 3.5) +  -- xGC outperformance ±17.5 pts
                        (COALESCE(xgi_per_90, 0.0) * 35.0) +                          -- attacking upside up to ~17.5 pts
                        ((6 - COALESCE(fixture_difficulty_rating, 3)) * 5.0) +         -- FDR ±15 pts
                        (COALESCE(xgi_per_million, 0.0) * 8.0) +                      -- value efficiency
                        (COALESCE(bps_per_90, 0.0) * 0.3)                             -- bonus magnet

                    -- MID: balanced xGI, creative output, team share, value, FDR
                    WHEN position_name = 'MID' THEN
                        (COALESCE(xgi_per_90, 0.0) * 40.0) +                          -- core output up to ~28 pts
                        (COALESCE(chance_creation_per_90, 0.0) * 5.0) +                -- creative volume up to ~12.5 pts
                        (COALESCE(team_xgi_share_pct, 0.0) * 0.6) +                   -- talisman share up to ~12 pts
                        ((6 - COALESCE(fixture_difficulty_rating, 3)) * 5.0) +         -- FDR ±15 pts
                        (COALESCE(xgi_per_million, 0.0) * 8.0)                         -- value efficiency

                    -- FWD: xGI heavy, clinical finishing, shot quality, FDR
                    WHEN position_name = 'FWD' THEN
                        (COALESCE(xgi_per_90, 0.0) * 45.0) +                          -- core output up to ~31.5 pts
                        (COALESCE(conversion_rate, 0.0) * 30.0) +                      -- clinical finishing up to ~6 pts
                        (COALESCE(npxg_per_shot, 0.0) * 20.0) +                        -- shot quality up to ~6 pts
                        (COALESCE(team_xgi_share_pct, 0.0) * 0.8) +                   -- talisman share
                        ((6 - COALESCE(fixture_difficulty_rating, 3)) * 5.0) +         -- FDR ±15 pts
                        (COALESCE(xgi_per_million, 0.0) * 6.0)                         -- value efficiency

                    -- Fallback (should not happen)
                    ELSE
                        (COALESCE(xgi_per_90, 0.0) * 45.0) +
                        (COALESCE(team_xgi_share_pct, 0.0) * 0.8) +
                        ((6 - COALESCE(fixture_difficulty_rating, 3)) * 5.0) +
                        (COALESCE(xgi_per_million, 0.0) * 10.0)
                END
            )), 1
        ) AS xfpl_edge_score,

        -- Fixture-Adjusted Primary Metric (xGI for outfield, save% for GKP)
        ROUND(
            CASE
                WHEN position_name = 'GKP' THEN
                    COALESCE(save_pct, 0.0) * (CASE fixture_difficulty_rating
                        WHEN 1 THEN 1.30 WHEN 2 THEN 1.15 WHEN 3 THEN 1.00
                        WHEN 4 THEN 0.85 WHEN 5 THEN 0.70 ELSE 1.00 END) / 100.0
                ELSE
                    COALESCE(xgi_per_90, 0.0) * (CASE fixture_difficulty_rating
                        WHEN 1 THEN 1.30 WHEN 2 THEN 1.15 WHEN 3 THEN 1.00
                        WHEN 4 THEN 0.85 WHEN 5 THEN 0.70 ELSE 1.00 END)
            END, 2
        ) AS fixture_adjusted_primary,

        -- Market Arbitrage Tag (position-aware)
        CASE
            -- GKP rotation risk
            WHEN position_name = 'GKP'
                 AND selected_by_percent < 3.0
                 AND save_pct > 70.0
            THEN 'HIDDEN_DIFFERENTIAL'
            WHEN position_name = 'GKP'
                 AND selected_by_percent >= 15.0
                 AND save_pct < 60.0
                 AND regression_signal = 'OVERPERFORMING_SELL_RISK'
            THEN 'BANDWAGON_TRAP'
            -- Outfield differentials
            WHEN position_name != 'GKP'
                 AND selected_by_percent < 8.0
                 AND xgi_per_90 >= 0.40
            THEN 'HIDDEN_DIFFERENTIAL'
            WHEN position_name != 'GKP'
                 AND selected_by_percent >= 20.0
                 AND xgi_per_90 <= 0.25
                 AND regression_signal = 'OVERPERFORMING_SELL_RISK'
            THEN 'BANDWAGON_TRAP'
            WHEN selected_by_percent >= 30.0
                 AND (CASE WHEN position_name = 'GKP' THEN save_pct ELSE xgi_per_90 * 100 END) >= 50.0
            THEN 'ESSENTIAL_TEMPLATE'
            ELSE 'STANDARD'
        END AS market_arbitrage_tag

    FROM player_upcoming
)

SELECT
    *,
    -- Position rank by edge score (1 = best in position)
    ROW_NUMBER() OVER (
        PARTITION BY position_name
        ORDER BY xfpl_edge_score DESC
    ) AS position_rank,
    -- Overall rank across all positions
    ROW_NUMBER() OVER (
        ORDER BY xfpl_edge_score DESC
    ) AS overall_rank
FROM scored
