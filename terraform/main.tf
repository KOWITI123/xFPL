terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# 1. Connect to your specific Google Cloud Project
provider "google" {
  project     = "de-project-allan"
  region      = "us-central1"
  credentials = "${path.module}/../creds/gcp_key.json"
}

# 2. Provision the GCS bucket
resource "google_storage_bucket" "raw_archive" {
  name          = "fpl_raw_archive_de-project-allan"
  location      = "US"
  force_destroy = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "AbortIncompleteMultipartUpload"
    }
  }
}

# 3. Provision the raw BigQuery dataset
resource "google_bigquery_dataset" "fpl_raw" {
  dataset_id = "fpl_raw"
  location   = "US"
}

# 4. Provision the analytics BigQuery dataset
resource "google_bigquery_dataset" "fpl_analytics" {
  dataset_id = "fpl_analytics"
  location   = "US"
}