#!/usr/bin/env python3
"""
Скрипт для запуска Streamlit UI
"""
import subprocess
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def main():
    # Устанавливаем переменную окружения для API (если не задана извне)
    api_base = os.environ.get("API_BASE")
    if not api_base:
        api_base = "http://localhost:8000"
    os.environ["API_BASE"] = api_base
    print(f"[run_ui] Using API_BASE={api_base}")
    
    # Запускаем Streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "app/ui/streamlit_app.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ])

if __name__ == "__main__":
    main()
