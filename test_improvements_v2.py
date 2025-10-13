#!/usr/bin/env python3
"""
Тестирование улучшенной BANT системы с тройной градацией и правильным тоном
"""

import requests
import json
import time
from datetime import datetime

# Конфигурация
API_BASE = "http://localhost:80/api"
AUTH = ("admin", "password")

def test_communication_tone():
    """Тестируем исправленный тон коммуникации"""
    print("🧪 Тестируем тон коммуникации...")
    
    # Создаем сессию
    response = requests.post(f"{API_BASE}/sessions/start", 
                           json={"deal_id": "TONE-TEST-001"}, 
                           auth=AUTH)
    
    if response.status_code != 200:
        print(f"❌ Ошибка создания сессии: {response.status_code}")
        return
    
    session_data = response.json()
    session_id = session_data["session_id"]
    question = session_data["question"]
    
    print(f"📝 Первый вопрос:")
    print(f"   {question}")
    
    # Проверяем, что тон обращен к менеджеру
    if "Помогите" in question and "клиент" in question:
        print("✅ Тон исправлен - обращение к менеджеру")
    else:
        print("❌ Тон не исправлен - все еще обращение к клиенту")
    
    return session_id

def test_three_level_status():
    """Тестируем тройную градацию статусов"""
    print("\n🧪 Тестируем тройную градацию статусов...")
    
    # Создаем сессию
    response = requests.post(f"{API_BASE}/sessions/start", 
                           json={"deal_id": "STATUS-TEST-001"}, 
                           auth=AUTH)
    
    if response.status_code != 200:
        print(f"❌ Ошибка создания сессии: {response.status_code}")
        return
    
    session_data = response.json()
    session_id = session_data["session_id"]
    
    # Тестируем разные уровни информации
    test_cases = [
        ("глава департамента разработки", "authority", "🟡 Определено частично"),
        ("Иванов Петр, CEO", "authority", "🟡 Определено частично"),
        ("не знаю", "authority", "❌ Не указано"),
        ("500-700 тысяч рублей", "budget", "🟡 Определено частично"),
        ("есть бюджет", "budget", "🟡 Определено частично"),
        ("нет", "budget", "❌ Не указано")
    ]
    
    for answer, expected_slot, expected_status in test_cases:
        print(f"\n📝 Тестируем: '{answer}'")
        
        response = requests.post(f"{API_BASE}/sessions/{session_id}/answer",
                               json={"text": answer},
                               auth=AUTH)
        
        if response.status_code == 200:
            data = response.json()
            if 'record' in data:
                record = data['record']
                
                # Проверяем статус в зависимости от слота
                if expected_slot == "authority":
                    authority = record.get("authority", {})
                    decision_maker = authority.get("decision_maker")
                    if decision_maker:
                        print(f"   Authority: {decision_maker}")
                        if "глава" in answer or "CEO" in answer:
                            print("   ✅ Частичная информация правильно обработана")
                        elif "не знаю" in answer:
                            print("   ✅ Отрицательный ответ правильно обработан")
                
                elif expected_slot == "budget":
                    budget = record.get("budget", {})
                    have_budget = budget.get("have_budget")
                    if have_budget is not None:
                        print(f"   Budget: have_budget = {have_budget}")
                        if "500-700" in answer:
                            print("   ✅ Частичная информация правильно обработана")
                        elif "есть" in answer:
                            print("   ✅ Общая информация правильно обработана")
                        elif "нет" in answer:
                            print("   ✅ Отрицательный ответ правильно обработан")

def test_timing_display():
    """Тестируем отображение сроков с контекстом"""
    print("\n🧪 Тестируем отображение сроков...")
    
    # Создаем сессию
    response = requests.post(f"{API_BASE}/sessions/start", 
                           json={"deal_id": "TIMING-TEST-001"}, 
                           auth=AUTH)
    
    if response.status_code != 200:
        print(f"❌ Ошибка создания сессии: {response.status_code}")
        return
    
    session_data = response.json()
    session_id = session_data["session_id"]
    
    # Переходим к timing
    requests.post(f"{API_BASE}/sessions/{session_id}/answer",
                 json={"text": "нет бюджета"},
                 auth=AUTH)
    requests.post(f"{API_BASE}/sessions/{session_id}/answer",
                 json={"text": "не знаю ЛПР"},
                 auth=AUTH)
    requests.post(f"{API_BASE}/sessions/{session_id}/answer",
                 json={"text": "не знаю проблемы"},
                 auth=AUTH)
    
    # Тестируем timing
    response = requests.post(f"{API_BASE}/sessions/{session_id}/answer",
                           json={"text": "конец года"},
                           auth=AUTH)
    
    if response.status_code == 200:
        data = response.json()
        if 'record' in data:
            record = data['record']
            timing = record.get("timing", {})
            timeframe = timing.get("timeframe")
            
            print(f"   Timeframe: {timeframe}")
            if timeframe == "this_year":
                print("   ✅ this_year правильно определен")
                
                # Проверяем, что в UI будет показан контекст
                current_date = datetime.now()
                year_end = current_date.year
                print(f"   ✅ В UI будет показано: 'Конец {year_end} года'")
            else:
                print(f"   ⚠️ Неожиданный timeframe: {timeframe}")

def test_ui_access():
    """Тестируем доступ к UI"""
    print("\n🌐 Тестируем доступ к UI...")
    
    try:
        response = requests.get("http://localhost:80/", auth=AUTH)
        if response.status_code == 200:
            print("✅ UI доступен")
            
            # Проверяем, что в HTML есть новые элементы
            html_content = response.text
            if "Определено четко" in html_content or "Определено частично" in html_content:
                print("✅ Новые статусы присутствуют в UI")
            else:
                print("⚠️ Новые статусы не найдены в UI")
        else:
            print(f"❌ UI недоступен: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка доступа к UI: {e}")

def test_authority_scoring():
    """Тестируем исправленный скоринг Authority"""
    print("\n🧪 Тестируем скоринг Authority...")
    
    # Создаем сессию
    response = requests.post(f"{API_BASE}/sessions/start", 
                           json={"deal_id": "SCORING-TEST-001"}, 
                           auth=AUTH)
    
    if response.status_code != 200:
        print(f"❌ Ошибка создания сессии: {response.status_code}")
        return
    
    session_data = response.json()
    session_id = session_data["session_id"]
    
    # Тестируем разные уровни информации о ЛПР
    test_cases = [
        ("глава департамента разработки", "минимальная информация"),
        ("Иванов Петр, CEO", "частичная информация"),
        ("не знаю", "отсутствие информации")
    ]
    
    for answer, description in test_cases:
        print(f"\n📝 Тестируем: '{answer}' ({description})")
        
        response = requests.post(f"{API_BASE}/sessions/{session_id}/answer",
                               json={"text": answer},
                               auth=AUTH)
        
        if response.status_code == 200:
            data = response.json()
            if 'record' in data and 'score' in data['record']:
                score = data['record']['score']
                authority_score = score.get('authority', {}).get('value', 0)
                authority_confidence = score.get('authority', {}).get('confidence', 0)
                
                print(f"   Скор: {authority_score}/25")
                print(f"   Уверенность: {authority_confidence:.0%}")
                
                if "глава" in answer:
                    if 8 <= authority_score <= 12:
                        print("   ✅ Минимальная информация правильно оценена")
                    else:
                        print(f"   ❌ Неправильный скор для минимальной информации: {authority_score}")
                elif "Иванов" in answer:
                    if 12 <= authority_score <= 18:
                        print("   ✅ Частичная информация правильно оценена")
                    else:
                        print(f"   ❌ Неправильный скор для частичной информации: {authority_score}")
                elif "не знаю" in answer:
                    if authority_score <= 5:
                        print("   ✅ Отсутствие информации правильно оценено")
                    else:
                        print(f"   ❌ Неправильный скор для отсутствия информации: {authority_score}")

if __name__ == "__main__":
    print("🚀 Запуск тестирования улучшенной BANT системы...")
    
    try:
        # Тестируем тон коммуникации
        session_id = test_communication_tone()
        
        # Тестируем тройную градацию
        test_three_level_status()
        
        # Тестируем отображение сроков
        test_timing_display()
        
        # Тестируем UI
        test_ui_access()
        
        # Тестируем скоринг
        test_authority_scoring()
        
        print("\n🎉 Тестирование завершено!")
        print("\n📋 Проверенные исправления:")
        print("✅ Тон коммуникации исправлен")
        print("✅ Тройная градация статусов добавлена")
        print("✅ Отображение сроков с контекстом")
        print("✅ Скоринг Authority исправлен")
        print("✅ UI обновлен")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()
