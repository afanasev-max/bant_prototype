# Настройка BANT Survey Prototype

## 1. Создание файла .env

Создайте файл `.env` в корне проекта со следующим содержимым:

```bash
# GigaChat API Configuration
GIGACHAT_CLIENT_ID=your_client_id_here
GIGACHAT_CLIENT_SECRET=your_client_secret_here
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_AUTH_URL=https://ngw.devices.sberbank.ru:9443/api/v2/oauth
GIGACHAT_API_URL=https://gigachat.devices.sberbank.ru/api/v1

# API Configuration
API_BASE=http://localhost:8000

# Storage Configuration
STORAGE_TYPE=json
STORAGE_PATH=data/sessions.json
```

## 2. Получение данных GigaChat

1. Зарегистрируйтесь на https://developers.sber.ru/
2. Создайте приложение
3. Получите `CLIENT_ID` и `CLIENT_SECRET`
4. Замените `your_client_id_here` и `your_client_secret_here` в файле .env

## 3. Запуск проекта

### Запуск API сервера:
```bash
source venv/bin/activate
python run_api.py
```

### Запуск UI (в другом терминале):
```bash
source venv/bin/activate
python run_ui.py
```

### Или используйте Makefile:
```bash
make dev  # Запуск API + UI
make run-api  # Только API
make run-ui   # Только UI
make test     # Запуск тестов
```

## 4. Доступ к приложению

- API: http://localhost:8000
- UI: http://localhost:8501
- API документация: http://localhost:8000/docs

## 5. Структура проекта

```
bant_prototype/
├── app/
│   ├── core/           # Основная логика
│   ├── services/       # Бизнес-логика
│   ├── api/           # FastAPI сервер
│   └── ui/            # Streamlit интерфейс
├── tests/             # Тесты
├── data/              # JSON хранилище
├── venv/              # Виртуальное окружение
└── requirements.txt   # Зависимости
```
