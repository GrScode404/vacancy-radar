.DEFAULT_GOAL := help
SRC := src

.PHONY: help lint fix typecheck check db-up db-down db-ps db-logs db-psql db-apply ollama-restart

help: ## Список команд
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# --- Код ---
lint: ## ruff: проверка и формат (без изменений)
	uv run ruff check $(SRC)
	uv run ruff format --check $(SRC)

fix: ## ruff: автоисправление и форматирование
	uv run ruff check --fix $(SRC)
	uv run ruff format $(SRC)

typecheck: ## mypy --strict
	uv run mypy $(SRC)

check: lint typecheck ## Всё перед коммитом

# --- База ---
db-up: ## Поднять Postgres и дождаться healthy
	docker compose up -d --wait

db-down: ## Остановить контейнеры (данные в томе сохраняются)
	docker compose down

db-ps: ## Статус контейнеров
	docker compose ps

db-logs: ## Логи Postgres (Ctrl+C — выход)
	docker compose logs -f db

db-psql: ## Консоль psql внутри контейнера
	docker compose exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

db-apply: ## Применить SQL-файл: make db-apply F=db/init/002_raw_json.sql
	@test -n "$(F)" || (echo "Укажи файл: make db-apply F=путь/к/файлу.sql"; exit 1)
	docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < $(F)

# --- Ollama ---
ollama-restart: ## Перезапуск Ollama (если ollama ps показывает CPU вместо GPU)
	sudo systemctl restart ollama