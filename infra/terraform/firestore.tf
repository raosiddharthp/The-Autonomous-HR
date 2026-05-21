resource "google_firestore_database" "main" {
  project     = var.project_id
  name        = "(default)"
  location_id = "asia-south1"
  type        = "FIRESTORE_NATIVE"
}
