#!/usr/bin/env python3
"""
Скрипт для запуска тестов
"""
import subprocess
import sys
import os

def main():
    # Устанавливаем PYTHONPATH для корректного импорта модулей
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ["PYTHONPATH"] = current_dir
    
    # Запускаем pytest
    subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/", 
        "-v", 
        "--tb=short"
    ])

if __name__ == "__main__":
    main()
