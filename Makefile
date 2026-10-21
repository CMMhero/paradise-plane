# Shortcut operasional Paradise Task Tracker. Semua delegasi ke script di
# paradise/bin (yang berisi logika sebenarnya). `make help` untuk daftar.
.DEFAULT_GOAL := help
.PHONY: help dev-up dev-down dev-logs dev-rebuild ps backup health env

help: ## Tampilkan daftar perintah
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	 awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\n", $$1, $$2}'

env: ## Siapkan .env dari template (tidak menimpa yang sudah ada)
	@test -f .env || cp paradise/.env.example .env
	@echo ".env siap, isi nilai <GANTI> (lihat paradise/SECURITY-CHECKLIST.md)"

dev-up: ## Nyalakan dev environment (build dari source)
	@paradise/bin/dev.sh up
dev-down: ## Matikan dev environment
	@paradise/bin/dev.sh down
dev-logs: ## Ikuti log (make dev-logs svc=api)
	@paradise/bin/dev.sh logs $(svc)
dev-rebuild: ## Rebuild paksa (make dev-rebuild svc=web)
	@paradise/bin/dev.sh rebuild $(svc)
ps: ## Status container
	@paradise/bin/dev.sh ps
backup: ## Backup database ke ./backups
	@paradise/bin/backup-db.sh
health: ## Healthcheck seluruh service
	@paradise/bin/healthcheck.sh
