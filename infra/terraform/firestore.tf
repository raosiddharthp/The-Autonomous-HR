resource "google_firestore_database" "main" {
  project     = var.project_id
  name        = "(default)"
  location_id = "asia-south1"
  type        = "FIRESTORE_NATIVE"
}

resource "google_firestore_ruleset" "main" {
  project = var.project_id

  source {
    files {
      name    = "firestore.rules"
      content = file("${path.root}/../../firestore.rules")
    }
  }

  depends_on = [google_firestore_database.main]
}

resource "google_firestore_security_rules" "main" {
  project  = var.project_id
  ruleset  = google_firestore_ruleset.main.name

  depends_on = [google_firestore_ruleset.main]
}
