resource "google_pubsub_topic" "inbound_messages" {
  name    = "inbound-messages"
  project = var.project_id
}

resource "google_pubsub_topic" "hitl_queue" {
  name    = "hitl-queue"
  project = var.project_id
}

resource "google_pubsub_topic" "billing_alerts" {
  name    = "billing-alerts"
  project = var.project_id
}

resource "google_pubsub_subscription" "inbound_messages_sub" {
  name    = "inbound-messages-sub"
  topic   = google_pubsub_topic.inbound_messages.name
  project = var.project_id

  ack_deadline_seconds = 60

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_topic" "dead_letter" {
  name    = "dead-letter"
  project = var.project_id
}

resource "google_pubsub_subscription" "dead_letter_sub" {
  name    = "dead-letter-sub"
  topic   = google_pubsub_topic.dead_letter.name
  project = var.project_id
}
