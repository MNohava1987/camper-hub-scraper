output "photo_server_url" {
  description = "Cloud Run photo server URL"
  value       = google_cloud_run_v2_service.photo_server.uri
}

output "photos_bucket" {
  description = "GCS photos bucket name"
  value       = google_storage_bucket.photos.name
}

output "data_bucket" {
  description = "GCS data bucket name"
  value       = google_storage_bucket.data.name
}

output "artifact_registry_repo" {
  description = "Artifact Registry repo hostname"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/camper-hub"
}

output "github_deploy_sa_email" {
  description = "GitHub Actions deploy service account email"
  value       = google_service_account.github_deploy.email
}

output "wif_provider" {
  description = "WIF provider resource name for GitHub Actions"
  value       = "${local.wif_pool_name}/providers/github-actions-provider"
}
