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
    """Отобразить статус BANT полей"""
    if not record:
        return
    
    st.subheader("📊 Статус BANT")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💰 Budget (Бюджет)**")
        budget = record.get("budget", {})
        budget_filled = any(v is not None and v != "" for v in budget.values())
        st.write(f"Статус: {'✅ Заполнено' if budget_filled else '❌ Не заполнено'}")
        if budget_filled:
            if budget.get("have_budget"):
                st.write(f"Есть бюджет: {budget.get('amount_min', 'N/A')} - {budget.get('amount_max', 'N/A')} {budget.get('currency', 'RUB')}")
            else:
                st.write("Бюджет: Нет")
        
        st.markdown("**👥 Authority (Полномочия)**")
        authority = record.get("authority", {})
        authority_filled = any(v is not None and v != "" for v in authority.values())
        st.write(f"Статус: {'✅ Заполнено' if authority_filled else '❌ Не заполнено'}")
        if authority_filled and authority.get("decision_maker"):
            st.write(f"ЛПР: {authority.get('decision_maker')}")
    
    with col2:
        st.markdown("**🎯 Need (Потребность)**")
        need = record.get("need", {})
        need_filled = any(v is not None and v != "" for v in need.values())
        st.write(f"Статус: {'✅ Заполнено' if need_filled else '❌ Не заполнено'}")
        if need_filled and need.get("pain_points"):
            st.write(f"Боли: {', '.join(need.get('pain_points', []))}")
        
        st.markdown("**⏰ Timing (Сроки)**")
        timing = record.get("timing", {})
        timing_filled = any(v is not None and v != "" for v in timing.values())
        st.write(f"Статус: {'✅ Заполнено' if timing_filled else '❌ Не заполнено'}")
        if timing_filled and timing.get("timeframe"):
            st.write(f"Срок: {timing.get('timeframe')}")

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
