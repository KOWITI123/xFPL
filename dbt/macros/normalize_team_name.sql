{% macro normalize_team_name(team_column) %}
  CASE
    WHEN LOWER({{ team_column }}) LIKE '%arsenal%' THEN 'Arsenal'
    WHEN LOWER({{ team_column }}) LIKE '%aston villa%' THEN 'Aston Villa'
    WHEN LOWER({{ team_column }}) LIKE '%bournemouth%' THEN 'Bournemouth'
    WHEN LOWER({{ team_column }}) LIKE '%brentford%' THEN 'Brentford'
    WHEN LOWER({{ team_column }}) LIKE '%brighton%' THEN 'Brighton'
    WHEN LOWER({{ team_column }}) LIKE '%chelsea%' THEN 'Chelsea'
    WHEN LOWER({{ team_column }}) LIKE '%crystal palace%' THEN 'Crystal Palace'
    WHEN LOWER({{ team_column }}) LIKE '%everton%' THEN 'Everton'
    WHEN LOWER({{ team_column }}) LIKE '%fulham%' THEN 'Fulham'
    WHEN LOWER({{ team_column }}) LIKE '%ipswich%' THEN 'Ipswich'
    WHEN LOWER({{ team_column }}) LIKE '%leicester%' THEN 'Leicester'
    WHEN LOWER({{ team_column }}) LIKE '%liverpool%' THEN 'Liverpool'
    WHEN LOWER({{ team_column }}) LIKE '%man%city%' THEN 'Manchester City'
    WHEN LOWER({{ team_column }}) LIKE '%man%utd%' OR LOWER({{ team_column }}) LIKE '%manchester united%' THEN 'Manchester United'
    WHEN LOWER({{ team_column }}) LIKE '%newcastle%' THEN 'Newcastle'
    WHEN LOWER({{ team_column }}) LIKE '%nottingham%' OR LOWER({{ team_column }}) LIKE '%nott%' THEN 'Nottingham Forest'
    WHEN LOWER({{ team_column }}) LIKE '%southampton%' THEN 'Southampton'
    WHEN LOWER({{ team_column }}) LIKE '%tottenham%' OR LOWER({{ team_column }}) LIKE '%spurs%' THEN 'Tottenham'
    WHEN LOWER({{ team_column }}) LIKE '%west ham%' THEN 'West Ham'
    WHEN LOWER({{ team_column }}) LIKE '%wolves%' OR LOWER({{ team_column }}) LIKE '%wolverhampton%' THEN 'Wolves'
    ELSE TRIM({{ team_column }})
  END
{% endmacro %}
