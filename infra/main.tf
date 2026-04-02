data "google_project" "project" {
  project_id = var.project_id
}

# ─── GCS Buckets ──────────────────────────────────────────────────────────────

resource "google_storage_bucket" "photos" {
  name          = "${var.project_id}-camper-hub-photos"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 365 }
  }
}

resource "google_storage_bucket" "data" {
  name                        = "${var.project_id}-camper-hub-data"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
}

# ─── Service Accounts ─────────────────────────────────────────────────────────

resource "google_service_account" "photo_server" {
  account_id   = "camper-hub-photo-server"
  display_name = "Camper Hub Photo Server"
}

resource "google_service_account" "scraper" {
  account_id   = "camper-hub-scraper"
  display_name = "Camper Hub Scraper"
}

resource "google_service_account" "pi_sync" {
  account_id   = "camper-hub-pi-sync"
  display_name = "Camper Hub Pi Sync"
}

resource "google_service_account" "github_deploy" {
  account_id   = "camper-hub-github-deploy"
  display_name = "Camper Hub GitHub Actions Deploy"
}

resource "google_service_account" "scheduler" {
  account_id   = "camper-hub-scheduler"
  display_name = "Camper Hub Scheduler"
}

# ─── IAM — Bucket Access ──────────────────────────────────────────────────────

resource "google_storage_bucket_iam_member" "photo_server_photos_rw" {
  bucket = google_storage_bucket.photos.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.photo_server.email}"
}

resource "google_storage_bucket_iam_member" "scraper_data_rw" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.scraper.email}"
}

resource "google_storage_bucket_iam_member" "pi_photos_ro" {
  bucket = google_storage_bucket.photos.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.pi_sync.email}"
}

resource "google_storage_bucket_iam_member" "pi_data_ro" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.pi_sync.email}"
}

# ─── IAM — GitHub Deploy SA ───────────────────────────────────────────────────

resource "google_project_iam_member" "github_deploy_cloudrun" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_deploy_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

# ─── WIF binding — GitHub Actions → deploy SA ─────────────────────────────────

locals {
  wif_pool_name = "projects/${data.google_project.project.number}/locations/global/workloadIdentityPools/github-actions-pool"
}

resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.github_deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${local.wif_pool_name}/attribute.repository/MNohava1987/camper-hub-scraper"
}

# ─── Artifact Registry ────────────────────────────────────────────────────────

resource "google_artifact_registry_repository" "camper_hub" {
  location      = var.region
  repository_id = "camper-hub"
  format        = "DOCKER"
}

# ─── Secret Manager — Upload Token ────────────────────────────────────────────

resource "google_secret_manager_secret" "upload_token" {
  secret_id = "camper-hub-upload-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "upload_token" {
  secret      = google_secret_manager_secret.upload_token.id
  secret_data = var.upload_token
}

resource "google_secret_manager_secret_iam_member" "photo_server_token_access" {
  secret_id = google_secret_manager_secret.upload_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.photo_server.email}"
}

# ─── Cloud Run — Photo Server ─────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "photo_server" {
  name     = "camper-hub-photo-server"
  location = var.region

  template {
    service_account = google_service_account.photo_server.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/camper-hub/photo-server:latest"

      ports {
        container_port = 3001
      }

      env {
        name  = "GCS_PHOTOS_BUCKET"
        value = google_storage_bucket.photos.name
      }

      env {
        name = "UPLOAD_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.upload_token.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  depends_on = [google_artifact_registry_repository.camper_hub]

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }
}

resource "google_cloud_run_service_iam_member" "photo_server_public" {
  location = google_cloud_run_v2_service.photo_server.location
  service  = google_cloud_run_v2_service.photo_server.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ─── Cloud Run Job — Scraper ──────────────────────────────────────────────────

resource "google_cloud_run_v2_job" "scraper" {
  name     = "camper-hub-scraper"
  location = var.region

  template {
    template {
      service_account = google_service_account.scraper.email

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/camper-hub/scraper:latest"

        env {
          name  = "GCS_DATA_BUCKET"
          value = google_storage_bucket.data.name
        }

        env {
          name  = "OUTPUT_MODE"
          value = "gcs"
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
      }

      max_retries = 2
      timeout     = "600s"
    }
  }

  depends_on = [google_artifact_registry_repository.camper_hub]

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
    ]
  }
}

# ─── Cloud Scheduler ──────────────────────────────────────────────────────────

resource "google_cloud_run_v2_job_iam_member" "scheduler_invoker" {
  location = google_cloud_run_v2_job.scraper.location
  name     = google_cloud_run_v2_job.scraper.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "scraper_trigger" {
  name      = "camper-hub-scraper-trigger"
  region    = var.region
  schedule  = "0 6 * * 1"
  time_zone = "America/Chicago"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.scraper.name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  # Start paused — enabled manually after Step 6 validation
  paused = true
}

# ─── Budget Alert ─────────────────────────────────────────────────────────────

resource "google_monitoring_notification_channel" "email" {
  display_name = "Camper Hub Alert Email"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}

resource "google_billing_budget" "camper_hub" {
  billing_account = var.billing_account_id
  display_name    = "Camper Hub Monthly Budget"

  budget_filter {
    projects = ["projects/${data.google_project.project.number}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.9
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = [
      google_monitoring_notification_channel.email.name
    ]
    disable_default_iam_recipients = false
  }
}
