"""
Provisions all external tables in BigQuery dataset fpl_raw pointing directly to GCS.
Enables dbt models to query raw GCS files transparently.
"""
from google.cloud import bigquery

CREDENTIALS_PATH = 'c:/Users/hp/Desktop/xFPL/creds/gcp_key.json'
PROJECT_ID = 'de-project-allan'
DATASET_ID = 'fpl_raw'
BUCKET_NAME = 'fpl_raw_archive_de-project-allan'

client = bigquery.Client.from_service_account_json(CREDENTIALS_PATH)

# JSON external tables (loaded with field_delimiter \x10 to capture entire JSON into 'data' column)
json_tables = {
    'raw_fpl_bootstrap': f'gs://{BUCKET_NAME}/fpl/snapshots/fpl_snapshot_*.json',
    'raw_fpl_fixtures': f'gs://{BUCKET_NAME}/fpl/fixtures/fpl_fixtures_*.json',
    'raw_fpl_gameweek_live': f'gs://{BUCKET_NAME}/fpl/gameweeks/*.json',
}

# CSV external tables (autodetect schema, skip header row)
csv_tables = {
    'raw_understat_matches': f'gs://{BUCKET_NAME}/understat/understat_player_matches_*.csv',
    'raw_understat_season': f'gs://{BUCKET_NAME}/understat/understat_player_season_*.csv',
    'raw_fbref_standard': f'gs://{BUCKET_NAME}/fbref/fbref_standard_*.csv',
    'raw_fbref_keeper': f'gs://{BUCKET_NAME}/fbref/fbref_keeper_*.csv',
    'raw_fbref_shooting': f'gs://{BUCKET_NAME}/fbref/fbref_shooting_*.csv',
    'raw_fbref_misc': f'gs://{BUCKET_NAME}/fbref/fbref_misc_*.csv',
    'raw_fbref_defense': f'gs://{BUCKET_NAME}/fbref/fbref_defense_*.csv',
    'raw_fbref_passing': f'gs://{BUCKET_NAME}/fbref/fbref_passing_*.csv',
    'raw_fbref_possession': f'gs://{BUCKET_NAME}/fbref/fbref_possession_*.csv',
    'raw_fbref_gca': f'gs://{BUCKET_NAME}/fbref/fbref_gca_*.csv',
}

print("Provisioning JSON external tables in BigQuery fpl_raw...")
for table_name, gcs_uri in json_tables.items():
    table_ref = f'{PROJECT_ID}.{DATASET_ID}.{table_name}'
    client.delete_table(table_ref, not_found_ok=True)
    table = bigquery.Table(table_ref)
    cfg = bigquery.ExternalConfig('CSV')
    cfg.source_uris = [gcs_uri]
    cfg.schema = [bigquery.SchemaField('data', 'STRING')]
    cfg.options.field_delimiter = '\x10'
    cfg.options.quote = ''
    cfg.options.allow_quoted_newlines = True
    table.external_data_configuration = cfg
    client.create_table(table)
    print(f"  [OK] Created external table: {table_name}")

print("\nProvisioning CSV external tables in BigQuery fpl_raw...")
for table_name, gcs_uri in csv_tables.items():
    table_ref = f'{PROJECT_ID}.{DATASET_ID}.{table_name}'
    client.delete_table(table_ref, not_found_ok=True)
    table = bigquery.Table(table_ref)
    cfg = bigquery.ExternalConfig('CSV')
    cfg.source_uris = [gcs_uri]
    cfg.options.skip_leading_rows = 1
    cfg.autodetect = True
    table.external_data_configuration = cfg
    client.create_table(table)
    print(f"  [OK] Created external table: {table_name}")

print("\nAll 9 external tables created successfully in BigQuery fpl_raw!")
