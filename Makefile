# ============================================================
#  MAKEFILE - Common development commands
# ============================================================

.PHONY: help install docker-up docker-down docker-logs db-init db-shell clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install Python dependencies"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make docker-logs  - View container logs"
	@echo "  make db-init      - Initialize database"
	@echo "  make db-shell     - Connect to database shell"
	@echo "  make run          - Run the bot"
	@echo "  make clean        - Clean up temporary files"

install:
	pip install -r requirements.txt

docker-up:
	docker-compose up -d
	@echo "✅ Containers started"
	@echo "📊 PGAdmin: http://localhost:5050"
	@echo "🗄️  Database: localhost:5432"

docker-down:
	docker-compose down
	@echo "✅ Containers stopped"

docker-logs:
	docker-compose logs -f

db-init:
	docker-compose exec postgres psql -U crypto_user -d crypto_bot -f /docker-entrypoint-initdb.d/01-init.sql

db-shell:
	docker-compose exec postgres psql -U crypto_user -d crypto_bot

run:
	python src/main.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
	find . -type f -name "*.pyc" -delete
	rm -rf logs/*.log 2>/dev/null
	@echo "✅ Cleaned"