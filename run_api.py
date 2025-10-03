#!/usr/bin/env python3
"""
Скрипт для запуска API сервера
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

import uvicorn
from app.api.main import app

if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
