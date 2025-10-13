# app/ui/streamlit_app.py
import streamlit as st
import requests
import json
import os
from datetime import datetime

# Конфигурация
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
print(f"DEBUG: API_BASE = {API_BASE}")
print(f"DEBUG: os.getenv('API_BASE') = {os.getenv('API_BASE')}")

st.set_page_config(
    page_title="BANT Опрос",
    page_icon="📊",
    layout="wide"
)

def init_session_state():
    """Инициализация состояния сессии"""
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "deal_id" not in st.session_state:
        st.session_state.deal_id = None
    if "current_question" not in st.session_state:
        st.session_state.current_question = ""
    if "history" not in st.session_state:
        st.session_state.history = []
    if "record" not in st.session_state:
        st.session_state.record = None
    if "filled" not in st.session_state:
        st.session_state.filled = "none"

def start_session(deal_id: str):
    """Начать новую сессию"""
    try:
        st.write(f"🔍 Отправляю запрос на: {API_BASE}/sessions/start")
        response = requests.post(f"{API_BASE}/sessions/start", json={"deal_id": deal_id})
        if response.status_code == 200:
            data = response.json()
            st.session_state.session_id = data["session_id"]
            st.session_state.deal_id = data["deal_id"]
            st.session_state.current_question = data.get("question", "")
            st.session_state.history = []
            st.session_state.record = None
            st.session_state.filled = "none"
            return True
        else:
            st.error(f"Ошибка при создании сессии: {response.text}")
            return False
    except Exception as e:
        st.error(f"Ошибка подключения к API: {str(e)}")
        return False

def send_answer(text: str):
    """Отправить ответ"""
    try:
        response = requests.post(
            f"{API_BASE}/sessions/{st.session_state.session_id}/answer",
            json={"text": text}
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.current_question = data.get("next_question", "")
            st.session_state.record = data.get("record")
            st.session_state.filled = data.get("filled", "none")
            st.session_state.history.append(("user", text))
            if data.get("next_question"):
                st.session_state.history.append(("assistant", data["next_question"]))
            return True
        else:
            st.error(f"Ошибка при отправке ответа: {response.text}")
            return False
    except Exception as e:
        st.error(f"Ошибка подключения к API: {str(e)}")
        return False

def get_session_status():
    """Получить статус сессии"""
    try:
        response = requests.get(f"{API_BASE}/sessions/{st.session_state.session_id}/status")
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def display_bant_status(record):
    """Отобразить статус BANT полей с разделением на 'Есть' / 'Нужно узнать'"""
    if not record:
        return
    
    st.subheader("📊 Статус BANT")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💰 Budget (Бюджет)**")
        budget = record.get("budget", {})
        budget_status, budget_message = get_budget_status(budget)
        st.write(f"Статус: {budget_status}")
        if budget_message:
            st.write(budget_message)
        
        # Показываем confidence если есть скоринг
        if record.get("score") and record["score"].get("budget"):
            confidence = record["score"]["budget"].get("confidence", 0)
            confidence_icon = "✅" if confidence > 0.75 else "🟡" if confidence > 0.5 else "⚠️"
            confidence_text = "высокая" if confidence > 0.75 else "средняя" if confidence > 0.5 else "низкая"
            st.write(f"Уверенность: {confidence_icon} {confidence:.0%} ({confidence_text})")
        
        # Разделение на "Есть" / "Нужно узнать"
        display_budget_details(budget)
        
        st.markdown("**👥 Authority (Полномочия)**")
        authority = record.get("authority", {})
        authority_status, authority_message = get_authority_status(authority)
        st.write(f"Статус: {authority_status}")
        if authority_message:
            st.write(authority_message)
        
        # Показываем confidence если есть скоринг
        if record.get("score") and record["score"].get("authority"):
            confidence = record["score"]["authority"].get("confidence", 0)
            confidence_icon = "✅" if confidence > 0.75 else "🟡" if confidence > 0.5 else "⚠️"
            confidence_text = "высокая" if confidence > 0.75 else "средняя" if confidence > 0.5 else "низкая"
            st.write(f"Уверенность: {confidence_icon} {confidence:.0%} ({confidence_text})")
        
        # Разделение на "Есть" / "Нужно узнать"
        display_authority_details(authority)
    
    with col2:
        st.markdown("**🎯 Need (Потребность)**")
        need = record.get("need", {})
        need_status, need_message = get_need_status(need)
        st.write(f"Статус: {need_status}")
        if need_message:
            st.write(need_message)
        
        # Показываем confidence если есть скоринг
        if record.get("score") and record["score"].get("need"):
            confidence = record["score"]["need"].get("confidence", 0)
            confidence_icon = "✅" if confidence > 0.75 else "🟡" if confidence > 0.5 else "⚠️"
            confidence_text = "высокая" if confidence > 0.75 else "средняя" if confidence > 0.5 else "низкая"
            st.write(f"Уверенность: {confidence_icon} {confidence:.0%} ({confidence_text})")
        
        # Разделение на "Есть" / "Нужно узнать"
        display_need_details(need)
        
        st.markdown("**⏰ Timing (Сроки)**")
        timing = record.get("timing", {})
        timing_status, timing_message = get_timing_status(timing)
        st.write(f"Статус: {timing_status}")
        if timing_message:
            st.write(timing_message)
        
        # Показываем confidence если есть скоринг
        if record.get("score") and record["score"].get("timing"):
            confidence = record["score"]["timing"].get("confidence", 0)
            confidence_icon = "✅" if confidence > 0.75 else "🟡" if confidence > 0.5 else "⚠️"
            confidence_text = "высокая" if confidence > 0.75 else "средняя" if confidence > 0.5 else "низкая"
            st.write(f"Уверенность: {confidence_icon} {confidence:.0%} ({confidence_text})")
        
        # Разделение на "Есть" / "Нужно узнать"
        display_timing_details(timing)

def display_budget_details(budget):
    """Показать детали бюджета с разделением"""
    budget_status = budget.get("budget_status")
    
    if budget_status == "NOT_ASKED":
        st.markdown("**❓ Что нужно уточнить у клиента:**")
        st.write("• Есть ли выделенный бюджет на проект?")
        st.write("• В каком диапазоне? (например: 200-500 тыс)")
        st.write("• Кто согласовывает выделение средств?")
    elif budget_status == "NO_BUDGET":
        st.markdown("**✅ Что выяснили:**")
        st.write("• Клиент сообщил об отсутствии бюджета")
        
        st.markdown("**❓ Что нужно уточнить у клиента:**")
        st.write("• Возможность выделения бюджета")
        st.write("• Временные рамки для планирования бюджета")
        st.write("• Альтернативные варианты финансирования")
    elif budget_status == "AVAILABLE":
        st.markdown("**✅ Что выяснили:**")
        if budget.get("amount_min") and budget.get("amount_max"):
            st.write(f"• Бюджет: {budget.get('amount_min')} - {budget.get('amount_max')} {budget.get('currency', 'RUB')}")
        else:
            st.write("• Есть бюджет, но суммы не уточнены")
        
        st.markdown("**❓ Что нужно уточнить у клиента:**")
        if not budget.get("amount_min") or not budget.get("amount_max"):
            st.write("• Конкретные суммы бюджета")
        if not budget.get("comment"):
            st.write("• Процесс согласования бюджета")
            st.write("• Сравнение с конкурентами")
    else:
        # Fallback для старых данных
        if budget.get("have_budget") is True:
            st.markdown("**✅ Что выяснили:**")
            if budget.get("amount_min") and budget.get("amount_max"):
                st.write(f"• Бюджет: {budget.get('amount_min')} - {budget.get('amount_max')} {budget.get('currency', 'RUB')}")
            else:
                st.write("• Есть бюджет, но суммы не уточнены")
            
            st.markdown("**❓ Что нужно уточнить у клиента:**")
            if not budget.get("amount_min") or not budget.get("amount_max"):
                st.write("• Конкретные суммы бюджета")
            if not budget.get("comment"):
                st.write("• Процесс согласования бюджета")
                st.write("• Сравнение с конкурентами")
        elif budget.get("have_budget") is False:
            st.markdown("**✅ Что выяснили:**")
            st.write("• Бюджет отсутствует")
            
            st.markdown("**❓ Что нужно уточнить у клиента:**")
            st.write("• Возможность выделения бюджета")
            st.write("• Временные рамки для планирования бюджета")
            st.write("• Альтернативные варианты финансирования")

def display_authority_details(authority):
    """Показать детали полномочий с разделением"""
    decision_maker = authority.get("decision_maker")
    uncertain = authority.get("uncertain")
    
    if decision_maker and decision_maker not in ["не знаем", "не определились", "не знаю", "без понятия", "не в курсе"]:
        st.markdown("**✅ Что выяснили:**")
        uncertainty_text = " (неопределенно)" if uncertain else ""
        st.write(f"• ЛПР: {decision_maker}{uncertainty_text}")
        if authority.get("stakeholders"):
            st.write(f"• Участники: {', '.join(authority['stakeholders'])}")
        if authority.get("decision_process"):
            st.write(f"• Процесс: {authority['decision_process']}")
        
        st.markdown("**❓ Что нужно уточнить у клиента:**")
        if uncertain:
            st.write("• Подтвердить, что именно этот человек принимает решения")
        if len(decision_maker.split()) <= 1:
            st.write("• Полное имя и контакты ЛПР")
        if not authority.get("stakeholders"):
            st.write("• Кто еще участвует в принятии решений")
        if not authority.get("decision_process"):
            st.write("• Детали процесса согласования")
    else:
        st.markdown("**❓ Что нужно уточнить у клиента:**")
        st.write("• Кто принимает финальное решение")
        st.write("• Процесс согласования решений")
        st.write("• Контакты ЛПР для встречи")

def display_need_details(need):
    """Показать детали потребностей с разделением"""
    pain_points = need.get("pain_points", [])
    if pain_points and len(pain_points) > 0:
        st.markdown("**✅ Что выяснили:**")
        for i, pain in enumerate(pain_points[:3], 1):
            st.write(f"• {i}. {pain}")
        if len(pain_points) > 3:
            st.write(f"• ... и еще {len(pain_points) - 3} проблем")
        
        st.markdown("**❓ Что нужно уточнить у клиента:**")
        if not need.get("success_criteria"):
            st.write("• Критерии успеха проекта")
        if not need.get("current_solution"):
            st.write("• Текущее решение проблемы")
        if not need.get("priority"):
            st.write("• Приоритет решения проблемы")
    else:
        st.markdown("**❓ Что нужно уточнить у клиента:**")
        st.write("• Основные проблемы в текущих процессах")
        st.write("• Что беспокоит больше всего")
        st.write("• Желаемый результат от проекта")

def display_timing_details(timing):
    """Показать детали сроков с разделением"""
    timeframe = timing.get("timeframe")
    if timeframe and timeframe != "unknown":
        st.markdown("**✅ Что выяснили:**")
        if timeframe == "this_year":
            from datetime import datetime
            current_date = datetime.now()
            st.write(f"• Срок: Конец {current_date.year} года")
        else:
            timeframe_map = {
                "this_month": "В этом месяце",
                "this_quarter": "В этом квартале",
                "this_half": "В этом полугодии",
                "next_year": "В следующем году"
            }
            st.write(f"• Срок: {timeframe_map.get(timeframe, timeframe)}")
        
        if timing.get("deadline"):
            st.write(f"• Дедлайн: {timing['deadline']}")
        
        st.markdown("**❓ Что нужно уточнить у клиента:**")
        if not timing.get("deadline"):
            st.write("• Жесткость дедлайна")
        if not timing.get("next_step"):
            st.write("• Следующий шаг в процессе")
        st.write("• Причины срочности")
        st.write("• Что будет, если не успеем")
    else:
        st.markdown("**❓ Что нужно уточнить у клиента:**")
        st.write("• Предполагаемые сроки запуска")
        st.write("• Жесткость временных рамок")
        st.write("• Причины срочности проекта")

def get_budget_status(budget):
    """Определить статус бюджета с тройной градацией"""
    budget_status = budget.get("budget_status")
    
    if budget_status == "NOT_ASKED":
        return "❌ Не указано", "Менеджер не обсудил бюджет с клиентом"
    elif budget_status == "NO_BUDGET":
        return "❌ Не указано", "Клиент сообщил об отсутствии бюджета"
    elif budget_status == "AVAILABLE":
        if budget.get("amount_min") and budget.get("amount_max") and budget.get("currency"):
            return "✅ Определено четко", f"Есть бюджет: {budget.get('amount_min', 'N/A')} - {budget.get('amount_max', 'N/A')} {budget.get('currency', 'RUB')}"
        elif budget.get("amount_min") or budget.get("amount_max"):
            return "🟡 Определено частично", f"Есть бюджет: {budget.get('amount_min', 'N/A')} - {budget.get('amount_max', 'N/A')} {budget.get('currency', 'RUB')} (нужны детали)"
        else:
            return "🟡 Определено частично", "Есть бюджет, но суммы не указаны"
    else:
        # Fallback для старых данных
        if budget.get("have_budget") is None:
            return "❌ Не указано", "Информация о бюджете отсутствует"
        elif budget.get("have_budget") is True:
            if budget.get("amount_min") and budget.get("amount_max") and budget.get("currency"):
                return "✅ Определено четко", f"Есть бюджет: {budget.get('amount_min', 'N/A')} - {budget.get('amount_max', 'N/A')} {budget.get('currency', 'RUB')}"
            elif budget.get("amount_min") or budget.get("amount_max"):
                return "🟡 Определено частично", f"Есть бюджет: {budget.get('amount_min', 'N/A')} - {budget.get('amount_max', 'N/A')} {budget.get('currency', 'RUB')} (нужны детали)"
            else:
                return "🟡 Определено частично", "Есть бюджет, но суммы не указаны"
        else:
            return "❌ Не указано", "Бюджет отсутствует"

def get_authority_status(authority):
    """Определить статус полномочий с тройной градацией"""
    decision_maker = authority.get("decision_maker")
    stakeholders = authority.get("stakeholders", [])
    decision_process = authority.get("decision_process")
    uncertain = authority.get("uncertain")
    
    if decision_maker is None:
        return "❌ Не указано", "ЛПР не определен"
    elif decision_maker in ["не знаем", "не определились", "не знаю", "без понятия", "не в курсе"]:
        return "❌ Не указано", f"ЛПР: {decision_maker}"
    else:
        # Проверяем полноту информации
        has_name = len(decision_maker.split()) > 1  # Есть имя и фамилия
        has_stakeholders = stakeholders and len(stakeholders) > 0
        has_process = decision_process and len(decision_process) > 10
        
        # Определяем статус на основе полноты информации
        if has_name and has_stakeholders and has_process:
            status_icon = "✅" if not uncertain else "🟡"
            status_text = "Определено четко" if not uncertain else "Определено частично"
            uncertainty_text = " (неопределенно)" if uncertain else ""
            return f"{status_icon} {status_text}", f"ЛПР: {decision_maker}, процесс: {decision_process}{uncertainty_text}"
        elif has_name or (has_stakeholders and has_process):
            uncertainty_text = " (неопределенно)" if uncertain else ""
            return f"🟡 Определено частично", f"ЛПР: {decision_maker} (нужны детали процесса){uncertainty_text}"
        else:
            uncertainty_text = " (неопределенно)" if uncertain else ""
            return f"🟡 Определено частично", f"ЛПР: {decision_maker} (нужны имя и процесс){uncertainty_text}"

def get_need_status(need):
    """Определить статус потребностей с тройной градацией"""
    pain_points = need.get("pain_points", [])
    success_criteria = need.get("success_criteria", [])
    current_solution = need.get("current_solution")
    priority = need.get("priority")
    
    if pain_points is None:
        return "❌ Не указано", "Проблемы клиента не выявлены"
    elif len(pain_points) == 0:
        return "❌ Не указано", "Проблем нет (требует уточнения)"
    else:
        # Проверяем полноту информации
        has_multiple_pains = len(pain_points) >= 2
        has_criteria = success_criteria and len(success_criteria) >= 2
        has_solution = current_solution and len(current_solution) > 10
        has_priority = priority in ['high', 'critical']
        
        # Логика определения статуса на основе полноты информации
        if has_multiple_pains and has_criteria and has_solution and has_priority:
            return "✅ Определено четко", f"Боли: {', '.join(pain_points[:2])}... (детально проработано)"
        elif has_multiple_pains and has_criteria:
            return "🟡 Определено частично", f"Боли: {', '.join(pain_points[:2])}... (нужны детали решения)"
        elif has_multiple_pains:
            return "🟡 Определено частично", f"Боли: {', '.join(pain_points)} (нужны критерии успеха)"
        else:
            return "🟡 Определено частично", f"Боли: {', '.join(pain_points)} (нужны детали)"

def get_timing_status(timing):
    """Определить статус сроков с контекстом даты"""
    from datetime import datetime, date
    
    timeframe = timing.get("timeframe")
    deadline = timing.get("deadline")
    
    if timeframe is None:
        return "❌ Не указано", "Сроки не определены"
    elif timeframe == "unknown":
        return "❌ Не указано", "Сроки неизвестны"
    else:
        # Конвертируем технические термины в понятные
        timeframe_map = {
            "this_month": "В этом месяце",
            "this_quarter": "В этом квартале", 
            "this_half": "В этом полугодии",
            "this_year": "В этом году",
            "next_year": "В следующем году"
        }
        
        display_timeframe = timeframe_map.get(timeframe, timeframe)
        
        # Добавляем контекст для this_year
        if timeframe == "this_year":
            current_date = datetime.now()
            year_end = date(current_date.year, 12, 31)
            days_left = (year_end - current_date.date()).days
            months_left = max(0, days_left // 30)
            
            if months_left > 0:
                return "🟡 Определено частично", f"Срок: Конец {current_date.year} года (осталось ~{months_left} мес)"
            else:
                return "✅ Определено четко", f"Срок: Конец {current_date.year} года (срочно!)"
        elif timeframe in ["this_month", "this_quarter"]:
            return "✅ Определено четко", f"Срок: {display_timeframe}"
        elif deadline:
            return "✅ Определено четко", f"Дедлайн: {deadline}"
        else:
            return "🟡 Определено частично", f"Срок: {display_timeframe} (нужны детали)"

def display_scoring(score):
    """Отобразить скоринг и объяснения"""
    st.subheader("📈 Скоринг BANT")
    
    # Общий скор
    total = score.get("total", 0)
    stage = score.get("stage", "unqualified")
    
    # Цветовая индикация
    if total >= 80:
        color = "🟢"
        stage_text = "Готов к продаже"
    elif total >= 60:
        color = "🟡"
        stage_text = "Квалифицирован"
    else:
        color = "🔴"
        stage_text = "Не квалифицирован"
    
    st.markdown(f"**Общий скор:** {color} {total}/100 - {stage_text}")
    
    # Детальный скоринг по секциям
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💰 Budget:** {}/25 (уверенность: {:.0%})".format(
            score.get("budget", {}).get("value", 0),
            score.get("budget", {}).get("confidence", 0)
        ))
        if score.get("budget", {}).get("rationale"):
            st.caption(score["budget"]["rationale"])
        
        st.markdown("**👥 Authority:** {}/25 (уверенность: {:.0%})".format(
            score.get("authority", {}).get("value", 0),
            score.get("authority", {}).get("confidence", 0)
        ))
        if score.get("authority", {}).get("rationale"):
            st.caption(score["authority"]["rationale"])
    
    with col2:
        st.markdown("**🎯 Need:** {}/30 (уверенность: {:.0%})".format(
            score.get("need", {}).get("value", 0),
            score.get("need", {}).get("confidence", 0)
        ))
        if score.get("need", {}).get("rationale"):
            st.caption(score["need"]["rationale"])
        
        st.markdown("**⏰ Timing:** {}/20 (уверенность: {:.0%})".format(
            score.get("timing", {}).get("value", 0),
            score.get("timing", {}).get("confidence", 0)
        ))
        if score.get("timing", {}).get("rationale"):
            st.caption(score["timing"]["rationale"])
    
    # Предупреждения при низкой уверенности
    low_confidence_slots = []
    for slot in ["budget", "authority", "need", "timing"]:
        confidence = score.get(slot, {}).get("confidence", 0)
        if confidence < 0.5:
            low_confidence_slots.append(slot)
    
    if low_confidence_slots:
        st.warning(f"⚠️ Низкая уверенность в данных: {', '.join(low_confidence_slots)}. Рекомендуется уточнить информацию.")
    
    # Объяснение для unqualified с учетом тройной градации
    if stage == "unqualified":
        st.error("🚫 Лид не квалифицирован")
        
        # Анализируем каждый компонент
        budget_score = score.get("budget", {}).get("value", 0)
        authority_score = score.get("authority", {}).get("value", 0)
        need_score = score.get("need", {}).get("value", 0)
        timing_score = score.get("timing", {}).get("value", 0)
        
        st.markdown("**Анализ компонентов:**")
        
        # Budget анализ
        if budget_score < 8:
            st.markdown("• 💰 **Бюджет**: ❌ Критический блокер - нет информации о финансах")
        elif budget_score < 15:
            st.markdown("• 💰 **Бюджет**: 🟡 Частично определен - нужны детали")
        else:
            st.markdown("• 💰 **Бюджет**: ✅ Определен четко")
            
        # Authority анализ
        if authority_score < 8:
            st.markdown("• 👥 **ЛПР**: ❌ Критический блокер - не определен")
        elif authority_score < 15:
            st.markdown("• 👥 **ЛПР**: 🟡 Частично определен - нужны детали")
        else:
            st.markdown("• 👥 **ЛПР**: ✅ Определен четко")
            
        # Need анализ
        if need_score < 8:
            st.markdown("• 🎯 **Потребность**: ❌ Критический блокер - не выявлены боли")
        elif need_score < 15:
            st.markdown("• 🎯 **Потребность**: 🟡 Частично определена - нужны детали")
        else:
            st.markdown("• 🎯 **Потребность**: ✅ Определена четко")
            
        # Timing анализ
        if timing_score < 8:
            st.markdown("• ⏰ **Сроки**: ❌ Критический блокер - не определены")
        elif timing_score < 15:
            st.markdown("• ⏰ **Сроки**: 🟡 Частично определены - нужны детали")
        else:
            st.markdown("• ⏰ **Сроки**: ✅ Определены четко")
        
        # Рекомендации для менеджера
        st.markdown("**Что делать дальше:**")
        
        if budget_score < 8:
            st.markdown("1. **Назначьте встречу** для обсуждения бюджета")
            st.markdown("2. **Спросите**: 'Есть ли у вас заложенные средства на этот проект?'")
            st.markdown("3. **Выясните**: 'Сравниваете ли вы с другими подрядчиками?'")
        
        if authority_score < 15:
            st.markdown("1. **Уточните контакты** ЛПР (имя, должность, телефон)")
            st.markdown("2. **Выясните процесс**: кто еще участвует в принятии решений?")
            st.markdown("3. **Спросите**: 'Можете ли вы организовать встречу с ЛПР?'")
        
        if need_score < 15:
            st.markdown("1. **Проведите интервью** для выявления болей")
            st.markdown("2. **Спросите**: 'Что вас больше всего беспокоит в текущих процессах?'")
            st.markdown("3. **Выясните**: 'Как будете измерять успех проекта?'")
        
        if timing_score < 15:
            st.markdown("1. **Уточните жесткость** дедлайна")
            st.markdown("2. **Выясните причины** срочности")
            st.markdown("3. **Спросите**: 'Что будет, если не успеем к этому сроку?'")

def main():
    init_session_state()
    
    st.title("📊 BANT Опрос (Прототип)")
    st.markdown("---")
    
    # Отладочная информация
    st.info(f"🔍 API_BASE: {API_BASE}")
    
    # Если нет активной сессии
    if not st.session_state.session_id:
        st.subheader("🚀 Начать новую сессию")
        deal_id = st.text_input("ID сделки", value="DEAL-001", help="Введите уникальный идентификатор сделки")
        
        if st.button("Начать опрос", type="primary"):
            if start_session(deal_id):
                st.success("Сессия создана! Начинаем опрос.")
                st.rerun()
    
    # Если есть активная сессия
    else:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader(f"💼 Сделка: {st.session_state.deal_id}")
            st.write(f"**Сессия:** {st.session_state.session_id}")
        
        with col2:
            if st.button("🔄 Новая сессия", type="secondary"):
                st.session_state.session_id = None
                st.session_state.deal_id = None
                st.rerun()
        
        # Отображение текущего вопроса
        if st.session_state.current_question:
            st.info(f"**Вопрос:** {st.session_state.current_question}")
        
        # Форма для ответа
        with st.form("answer_form"):
            answer_text = st.text_area(
                "Ваш ответ:",
                placeholder="Введите ответ на вопрос...",
                height=100
            )
            submitted = st.form_submit_button("Отправить ответ", type="primary")
            
            if submitted and answer_text.strip():
                if send_answer(answer_text.strip()):
                    st.success("Ответ отправлен!")
                    st.rerun()
        
        # Отображение истории
        if st.session_state.history:
            st.subheader("💬 История диалога")
            for role, message in st.session_state.history[-10:]:  # Показываем последние 10 сообщений
                if role == "user":
                    st.write(f"**Вы:** {message}")
                else:
                    st.write(f"**Система:** {message}")
        
        # Отображение статуса BANT
        if st.session_state.record:
            display_bant_status(st.session_state.record)
            
            # Отображение скоринга
            if st.session_state.record.get("score"):
                display_scoring(st.session_state.record["score"])
            
            # JSON превью
            st.subheader("📄 JSON данные")
            st.json(st.session_state.record)
            
            # Кнопка экспорта
            json_str = json.dumps(st.session_state.record, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 Скачать JSON",
                data=json_str,
                file_name=f"bant_{st.session_state.deal_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        # Статус заполнения
        if st.session_state.filled:
            status_colors = {
                "full": "🟢",
                "partial": "🟡", 
                "none": "🔴"
            }
            status_text = {
                "full": "Полностью заполнено",
                "partial": "Частично заполнено",
                "none": "Не заполнено"
            }
            
            st.markdown(f"**Общий статус:** {status_colors.get(st.session_state.filled, '⚪')} {status_text.get(st.session_state.filled, 'Неизвестно')}")

if __name__ == "__main__":
    main()
