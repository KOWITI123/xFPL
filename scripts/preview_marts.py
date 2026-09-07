"""
Previews top analytical insights from the Phase 3 marts.
"""
from google.cloud import bigquery

CREDENTIALS_PATH = 'c:/Users/hp/Desktop/xFPL/creds/gcp_key.json'
client = bigquery.Client.from_service_account_json(CREDENTIALS_PATH)

print("=" * 80)
print("1. FUSED FACT LAYER: fct_player_underlying (Sample Players)")
print("=" * 80)
query1 = """
SELECT
    dp.web_name,
    dp.team_short_name,
    f.position_name,
    f.gameweek,
    f.minutes,
    f.fpl_points,
    f.goals_scored,
    f.xg,
    f.xg_delta,
    f.assists,
    f.xa,
    f.xa_delta,
    f.xgi_per_90,
    f.npxg_per_shot
FROM `de-project-allan.fpl_analytics_marts.fct_player_underlying` f
JOIN `de-project-allan.fpl_analytics_marts.dim_players` dp ON f.fpl_player_id = dp.player_id
WHERE f.minutes > 0
ORDER BY f.fpl_points DESC
LIMIT 8
"""
for row in client.query(query1):
    print(f"{row.web_name:<15} | {row.team_short_name} | {row.position_name} | GW{row.gameweek} | Mins: {row.minutes:<2} | Pts: {row.fpl_points:<2} | Goals: {row.goals_scored} (xG: {row.xg:.2f}, delta: {row.xg_delta:+.2f}) | Assists: {row.assists} (xA: {row.xa:.2f}) | xGI90: {row.xgi_per_90:.2f} | npxG/shot: {row.npxg_per_shot:.2f}")

print("\n" + "=" * 80)
print("2. EDGE MART: Top Underperforming Buy Targets & Overperforming Traps")
print("=" * 80)
query2 = """
SELECT
    web_name,
    team_short_name,
    position_name,
    cost_million,
    total_fpl_points,
    actual_goals,
    total_xg,
    xg_delta,
    total_shots,
    npxg_per_shot,
    team_xgi_share_pct,
    regression_signal,
    edge_badge
FROM `de-project-allan.fpl_analytics_marts.mart_player_performance_edge`
WHERE total_minutes >= 60
ORDER BY total_xg DESC
LIMIT 8
"""
for row in client.query(query2):
    print(f"{row.web_name:<15} | £{row.cost_million:.1f}m | {row.position_name} | Pts: {row.total_fpl_points:<2} | G: {row.actual_goals} vs xG: {row.total_xg:<4.2f} (delta: {row.xg_delta:+.2f}) | ShotQual: {row.npxg_per_shot:.2f} | TeamShare: {row.team_xgi_share_pct:.1f}% | Signal: {row.regression_signal:<25} | Badge: {row.edge_badge}")

print("\n" + "=" * 80)
print("3. RECOMMENDATIONS MART: Composite xFPL Edge Score & Differentials")
print("=" * 80)
query3 = """
SELECT
    web_name,
    team_name,
    position_name,
    cost_million,
    selected_by_percent,
    next_opponent,
    venue,
    fixture_difficulty_rating,
    fixture_adjusted_xgi,
    market_arbitrage_tag,
    xfpl_edge_score
FROM `de-project-allan.fpl_analytics_marts.mart_fixture_player_recommendations`
ORDER BY xfpl_edge_score DESC
LIMIT 8
"""
for row in client.query(query3):
    print(f"{row.web_name:<15} | {row.team_name:<16} | £{row.cost_million:.1f}m | Own: {row.selected_by_percent:>4.1f}% | vs {row.next_opponent:<12} ({row.venue:<4}, FDR {row.fixture_difficulty_rating}) | Adj xGI: {row.fixture_adjusted_xgi:.2f} | Tag: {row.market_arbitrage_tag:<19} | Edge Score: {row.xfpl_edge_score}")
