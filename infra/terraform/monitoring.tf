# Enable monitoring API
resource "google_project_service" "monitoring" {
  service            = "monitoring.googleapis.com"
  project            = var.project_id
  disable_on_destroy = false
}

resource "google_project_service" "logging" {
  service            = "logging.googleapis.com"
  project            = var.project_id
  disable_on_destroy = false
}

# Log-based metric: error rate
resource "google_logging_metric" "error_rate" {
  name    = "webhook-error-rate"
  project = var.project_id
  filter  = "resource.type=\"cloud_run_revision\" AND severity>=ERROR"
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

# Log-based metric: conversation count
resource "google_logging_metric" "conversation_count" {
  name    = "conversation-count"
  project = var.project_id
  filter  = "resource.type=\"cloud_run_revision\" AND jsonPayload.event=\"new_conversation\""
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

# Notification channel: email
resource "google_monitoring_notification_channel" "email" {
  display_name = "Admin Email"
  type         = "email"
  project      = var.project_id
  labels = {
    email_address = var.alert_email
  }
}

# Alert: error rate > 5%
resource "google_monitoring_alert_policy" "error_rate_alert" {
  display_name = "High Error Rate"
  project      = var.project_id
  combiner     = "OR"
  conditions {
    display_name = "Error rate > 5%"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/webhook-error-rate\" AND resource.type=\"cloud_run_revision\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  notification_channels = [google_monitoring_notification_channel.email.id]
  depends_on            = [google_project_service.monitoring]
}

# Alert: conversation count > 800/month
resource "google_monitoring_alert_policy" "conversation_count_alert" {
  display_name = "Conversation Count Near Limit"
  project      = var.project_id
  combiner     = "OR"
  conditions {
    display_name = "Conversations > 800"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/conversation-count\" AND resource.type=\"cloud_run_revision\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 800
      aggregations {
        alignment_period   = "86400s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
  notification_channels = [google_monitoring_notification_channel.email.id]
  depends_on            = [google_project_service.monitoring]
}
