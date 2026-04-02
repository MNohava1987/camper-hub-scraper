variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "GCP region for all resources"
}

variable "alert_email" {
  type        = string
  description = "Email address for budget alerts"
}

variable "monthly_budget_usd" {
  type        = number
  default     = 10
  description = "Monthly budget ceiling in USD"
}

variable "billing_account_id" {
  type        = string
  description = "GCP billing account ID for budget alert"
}

variable "upload_token" {
  type        = string
  description = "Shared secret token for photo upload endpoint"
  sensitive   = true
}
