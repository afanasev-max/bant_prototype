#!/usr/bin/env python3
"""
Тестирование API BANT системы реальными запросами
"""

import requests
import json
import time

# Конфигурация
API_BASE = "http://localhost:80/api"
AUTH = ("admin", "password")

def test_negative_responses():
    """Тестируем обработку отрицательных ответов через API"""
    print("🧪 Тестируем API с отрицательными ответами...")
    
    # 1. Создаем сессию
    print("\n1️⃣ Создаем сессию...")
    response = requests.post(f"{API_BASE}/sessions/start", 
                           json={"deal_id": "API-TEST-001"}, 
                           auth=AUTH)
    
    if response.status_code != 200:
        print(f"❌ Ошибка создания сессии: {response.status_code}")
        return
    
    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"✅ Сессия создана: {session_id}")
    print(f"📝 Первый вопрос: {session_data['question']}")
    
    # 2. Тестируем отрицательные ответы
    test_cases = [
        ("не знаю", "authority"),
        ("нет", "budget"),
        ("не определились", "need"),
        ("unknown", "timing")
    ]
    
    for i, (answer, expected_slot) in enumerate(test_cases, 1):
        print(f"\n{i+1}️⃣ Тестируем ответ: '{answer}'")
        
        # Отправляем ответ
        response = requests.post(f"{API_BASE}/sessions/{session_id}/answer",
                               json={"text": answer},
                               auth=AUTH)
        
        if response.status_code != 200:
            print(f"❌ Ошибка отправки ответа: {response.status_code}")
            continue
        
        data = response.json()
        print(f"   Следующий слот: {data.get('current_slot', 'None')}")
        print(f"   Вопрос: {data.get('question', 'None')[:100]}...")
        print(f"   Followup: {data.get('followups', [])}")
        
        # Проверяем record
        if 'record' in data:
            record = data['record']
            print(f"   Record: {json.dumps(record, ensure_ascii=False, indent=2)}")
            
            # Проверяем скоринг
            if 'score' in record:
                score = record['score']
                print(f"   Скор: {score.get('total', 0)}/100")
                print(f"   Стадия: {score.get('stage', 'unknown')}")
        
        time.sleep(1)  # Небольшая пауза между запросами

def test_ui_access():
    """Тестируем доступ к UI"""
    print("\n🌐 Тестируем доступ к UI...")
    
    try:
        response = requests.get("http://localhost:80/", auth=AUTH)
        if response.status_code == 200:
            print("✅ UI доступен")
            print(f"   Размер ответа: {len(response.text)} байт")
        else:
            print(f"❌ UI недоступен: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка доступа к UI: {e}")

def test_health_check():
    """Тестируем health check"""
    print("\n🏥 Тестируем health check...")
    
    try:
        response = requests.get("http://localhost:80/health", auth=AUTH)
        if response.status_code == 200:
            print("✅ Health check прошел")
            print(f"   Ответ: {response.text}")
        else:
            print(f"❌ Health check не прошел: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка health check: {e}")

if __name__ == "__main__":
    print("🚀 Запуск тестирования API BANT системы...")
    
    try:
        test_health_check()
        test_ui_access()
        test_negative_responses()
        
        print("\n🎉 Тестирование завершено!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()
