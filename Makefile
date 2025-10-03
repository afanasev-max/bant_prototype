# Makefile для BANT Survey Prototype

.PHONY: help install test run-api run-ui clean docker-build docker-up docker-down docker-logs docker-test

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Локальная разработка
install: ## Установить зависимости
	pip install -r requirements.txt

test: ## Запустить тесты
	python run_tests.py

run-api: ## Запустить API сервер
	python run_api.py

run-ui: ## Запустить Streamlit UI
	python run_ui.py

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf data/sessions.json

dev: ## Запустить в режиме разработки (API + UI)
	@echo "Запуск API сервера в фоне..."
	@python run_api.py &
	@sleep 3
	@echo "Запуск UI..."
	@python run_ui.py

stop: ## Остановить все процессы
	@pkill -f "python.*run_api.py" || true
	@pkill -f "streamlit.*streamlit_app.py" || true

# Docker команды
docker-build: ## Собрать Docker образы
	docker-compose build

docker-up: ## Запустить контейнеры
	docker-compose up -d

docker-down: ## Остановить контейнеры
	docker-compose down

docker-logs: ## Показать логи контейнеров
	docker-compose logs -f

docker-logs-api: ## Показать логи API
	docker-compose logs -f api

docker-logs-ui: ## Показать логи UI
	docker-compose logs -f ui

docker-test: ## Запустить тесты в контейнере
	docker-compose run --rm api python run_tests.py

docker-shell: ## Войти в контейнер API
	docker-compose exec api bash

docker-shell-ui: ## Войти в контейнер UI
	docker-compose exec ui bash

docker-restart: ## Перезапустить контейнеры
	docker-compose restart

docker-clean: ## Очистить Docker ресурсы
	docker-compose down -v
	docker system prune -f

# Полный цикл
docker-dev: docker-build docker-up ## Собрать и запустить в Docker
	@echo "Сервисы запущены:"
	@echo "UI (через nginx): http://localhost"
	@echo "API: http://localhost/api"
	@echo "API Docs: http://localhost/api/docs"
	@echo "Health: http://localhost/health"

# Production команды
prod-up: ## Запустить в production режиме
	docker-compose up -d
	@echo "Приложение доступно по адресу: http://localhost"

prod-down: ## Остановить production
	docker-compose down

prod-restart: ## Перезапустить production
	docker-compose restart

prod-logs: ## Показать логи production
	docker-compose logs -f

get-ip: ## Показать IP адрес для внешнего доступа
	./get_ip.sh

setup-auth: ## Настроить HTTP Basic Authentication
	./setup_auth.sh

remove-auth: ## Удалить аутентификацию
	rm -rf nginx_auth/
	sed -i.bak '/auth_basic/d' nginx.conf
	sed -i.bak '/auth_basic_user_file/d' nginx.conf
	make prod-restart

access-info: ## Показать информацию о доступе
	./get_access_info.sh
