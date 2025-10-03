# BANT Survey Prototype

Прототип системы опроса BANT (Budget, Authority, Need, Timing) с использованием GigaChat для валидации и нормализации ответов.

## Архитектура

- **Backend**: FastAPI с Pydantic валидацией
- **LLM**: GigaChat для извлечения структурированных данных
- **UI**: Streamlit интерфейс
- **Storage**: JSON файлы (для прототипа)

## Установка

1. Клонируйте репозиторий
2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте переменные окружения:
```bash
cp env.example .env
# Отредактируйте .env файл с вашими данными GigaChat
```

### Настройка GigaChat

1. Зарегистрируйтесь на https://developers.sber.ru/
2. Создайте приложение
3. Получите `CLIENT_ID` и `CLIENT_SECRET`
4. Создайте base64 строку:
```bash
echo -n "CLIENT_ID:CLIENT_SECRET" | base64
```
5. Замените `your_base64_auth_key_here` в файле .env полученной строкой

## Запуск

### Вариант 1: Docker с nginx (Рекомендуется)

1. **Настройте переменные окружения:**
```bash
cp env.docker .env
# Отредактируйте .env файл с вашими данными GigaChat
```

2. **Запустите через Docker Compose:**
```bash
# Собрать и запустить все сервисы с nginx
make prod-up

# Или по отдельности:
make docker-build  # Собрать образы
make docker-up     # Запустить контейнеры
```

3. **Доступ к приложению:**
- **UI (основной интерфейс):** http://localhost или http://YOUR_IP
- **API:** http://localhost/api или http://YOUR_IP/api
- **API документация:** http://localhost/api/docs или http://YOUR_IP/api/docs
- **Health Check:** http://localhost/health или http://YOUR_IP/health

**Для внешнего доступа:**
- Замените `YOUR_IP` на IP адрес вашего компьютера
- Убедитесь, что порт 80 открыт в файрволе
- Другие пользователи смогут получить доступ по адресу: `http://YOUR_IP`

**Настройка аутентификации (опционально):**
```bash
# Настроить HTTP Basic Authentication
make setup-auth

# Удалить аутентификацию
make remove-auth
```

### Вариант 2: Локальная разработка

1. **Создайте виртуальное окружение:**
```bash
python3.12 -m venv venv
source venv/bin/activate
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Настройте переменные окружения:**
```bash
cp env.example .env
# Отредактируйте .env файл с вашими данными GigaChat
```

4. **Запустите сервисы:**
```bash
# API сервер
python run_api.py

# UI (в другом терминале)
python run_ui.py
```

## Использование

1. Откройте браузер по адресу http://localhost:8501
2. Введите ID сделки
3. Нажмите "Начать опрос"
4. Отвечайте на вопросы системы
5. Просматривайте статус заполнения BANT полей
6. Экспортируйте результат в JSON

## Docker команды

```bash
# Production команды (с nginx)
make prod-up         # Запустить все сервисы с nginx
make prod-down       # Остановить все сервисы
make prod-restart    # Перезапустить все сервисы
make prod-logs       # Показать все логи

# Development команды
make docker-dev      # Собрать и запустить все сервисы
make docker-up       # Запустить контейнеры
make docker-down     # Остановить контейнеры
make docker-restart  # Перезапустить контейнеры

# Логи и отладка
make docker-logs     # Показать все логи
make docker-logs-api # Логи API
make docker-logs-ui  # Логи UI
make docker-shell    # Войти в контейнер API
make docker-shell-ui # Войти в контейнер UI

# Тестирование
make docker-test     # Запустить тесты в контейнере

# Очистка
make docker-clean    # Очистить Docker ресурсы
```

## Архитектура Docker

- **nginx** (порт 80) - обратный прокси для UI и API
- **api** (внутренний порт 8000) - FastAPI сервер
- **ui** (внутренний порт 8501) - Streamlit интерфейс

Все сервисы доступны через nginx на порту 80:
- UI: http://localhost/
- API: http://localhost/api/
- Health: http://localhost/health

## API Endpoints

- `POST /sessions/start` - Начать новую сессию
- `POST /sessions/{session_id}/answer` - Ответить на вопрос
- `GET /sessions/{session_id}/status` - Получить статус сессии
- `GET /results/{session_id}` - Получить результат
- `GET /health` - Проверка здоровья сервиса

## Структура проекта

```
bant_prototype/
├── app/
│   ├── core/           # Основная логика
│   ├── services/       # Бизнес-логика
│   ├── api/           # FastAPI сервер
│   └── ui/            # Streamlit интерфейс
├── tests/             # Тесты
├── data/              # JSON хранилище
└── requirements.txt   # Зависимости
```

## Конфигурация

Все настройки находятся в файле `.env`:

- `GIGACHAT_CLIENT_ID` - ID клиента GigaChat
- `GIGACHAT_CLIENT_SECRET` - Секрет клиента GigaChat
- `API_BASE` - Базовый URL API (по умолчанию http://localhost:8000)

## Особенности

- Автоматическая валидация ответов через GigaChat
- Генерация уточняющих вопросов
- Визуализация статуса заполнения BANT
- Экспорт результатов в JSON
- Простой и интуитивный интерфейс
