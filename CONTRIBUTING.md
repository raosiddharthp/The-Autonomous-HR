# Local Development Setup

## Prerequisites
- Docker & Docker Compose
- ngrok
- gcloud CLI
- Terraform >= 1.0

## Getting Started

1. Clone the repo
2. Run `make dev` to start the local stack
3. Run `make tunnel` in a separate terminal to expose the webhook
4. Copy the ngrok HTTPS URL and configure it as your WhatsApp webhook

## Commands
- `make dev` — start full local stack
- `make test` — run tests
- `make deploy` — deploy to GCP
- `make tunnel` — start ngrok tunnel
