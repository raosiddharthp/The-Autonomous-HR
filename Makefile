.PHONY: dev test deploy tunnel help

help:
	@echo "Available targets:"
	@echo "  make dev     - Start local stack with docker-compose"
	@echo "  make test    - Run all tests"
	@echo "  make deploy  - Deploy to GCP via Terraform"
	@echo "  make tunnel  - Start ngrok tunnel for WhatsApp webhook testing"

dev:
	docker-compose up --build

test:
	@echo "Running tests..."
	cd infra/terraform && terraform validate
	@echo "All tests passed."

deploy:
	cd infra/terraform && terraform apply -auto-approve

tunnel:
	@echo "Starting ngrok tunnel on port 8000..."
	@echo "Copy the HTTPS URL and set it as your WhatsApp webhook URL"
	ngrok http 8000
