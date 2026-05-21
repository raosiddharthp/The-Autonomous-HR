resource "google_secret_manager_secret" "whatsapp_token" {
  secret_id = "whatsapp-token"
  project   = var.project_id
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"
  project   = var.project_id
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "twilio_sid" {
  secret_id = "twilio-sid"
  project   = var.project_id
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "twilio_auth_token" {
  secret_id = "twilio-auth-token"
  project   = var.project_id
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "twilio_phone_number" {
  secret_id = "twilio-phone-number"
  project   = var.project_id
  replication {
    auto {}
  }
}
