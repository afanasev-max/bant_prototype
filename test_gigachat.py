#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы GigaChat
"""
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.llm import GigaChatClient

def test_gigachat():
    """Тестируем подключение к GigaChat"""
    print("🔍 Тестируем подключение к GigaChat...")
    
    try:
        # Создаем клиент
        client = GigaChatClient()
        print("✅ Клиент GigaChat создан успешно")
        
        # Тестовое сообщение
        messages = [
            {"role": "system", "content": "Ты помощник для извлечения структурированных данных из текста."},
            {"role": "user", "content": "Привет! Как дела?"}
        ]
        
        print("📤 Отправляем тестовое сообщение...")
        response = client.chat(messages, temperature=0.2)
        print(f"📥 Ответ от GigaChat: {response}")
        
        print("✅ GigaChat работает корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при работе с GigaChat: {e}")
        return False

def test_json_mode():
    """Тестируем json_mode"""
    print("\n🔍 Тестируем json_mode...")
    
    try:
        client = GigaChatClient()
        
        messages = [
            {"role": "system", "content": "Верни JSON с полем 'status' и 'message'."},
            {"role": "user", "content": "Скажи что все хорошо"}
        ]
        
        print("📤 Отправляем запрос с json_mode=True...")
        response = client.chat(messages, json_mode=True)
        print(f"📥 JSON ответ: {response}")
        
        # Проверяем, что это валидный JSON
        import json
        parsed = json.loads(response)
        print(f"✅ JSON парсится корректно: {parsed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании json_mode: {e}")
        return False

def test_bant_parsing():
    """Тестируем парсинг BANT данных"""
    print("\n🔍 Тестируем парсинг BANT данных...")
    
    try:
        from app.core.validator import parse_bant_with_llm
        
        client = GigaChatClient()
        
        # Тестовый ответ менеджера
        answer = "У нас есть бюджет 500000 рублей на этот проект. Покупать будем в этом квартале."
        
        print(f"📤 Тестовый ответ: {answer}")
        result = parse_bant_with_llm(client, answer)
        print(f"📥 Распарсенный результат: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге BANT: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск тестов GigaChat\n")
    
    # Проверяем переменные окружения
    auth_key = os.getenv("GIGACHAT_AUTH_KEY")
    if not auth_key:
        print("❌ GIGACHAT_AUTH_KEY не найден в переменных окружения")
        sys.exit(1)
    
    print(f"🔑 AUTH_KEY найден: {auth_key[:20]}...")
    
    # Запускаем тесты
    success = True
    success &= test_gigachat()
    success &= test_json_mode()
    success &= test_bant_parsing()
    
    if success:
        print("\n🎉 Все тесты прошли успешно! GigaChat готов к работе.")
    else:
        print("\n💥 Некоторые тесты не прошли. Проверьте настройки.")
        sys.exit(1)
