# app/services/bant_agent.py
import uuid
import json
from app.core.schema import SessionState, BantRecord, CrmDeal
from app.core.flow import BantFlow
from app.core.llm import GigaChatClient
from app.core.prompts import CRM_ANALYSIS_PROMPT

class BantAgentService:
    def __init__(self):
        self.llm = GigaChatClient()
        self.flow = BantFlow(self.llm)
        self.sessions: dict[str, SessionState] = {}

    def start(self, deal_id: str) -> SessionState:
        sid = str(uuid.uuid4())
        state = SessionState(
            session_id=sid, 
            deal_id=deal_id, 
            record=BantRecord(deal_id=deal_id)
        )
        state.current_slot = self.flow.next_slot(state)
        self.sessions[sid] = state
        return state

    def answer(self, session_id: str, text: str) -> tuple[SessionState, str | None, list[str]]:
        if session_id not in self.sessions:
            raise ValueError("Session not found")
        
        st = self.sessions[session_id]
        st.history.append({"role": "user", "content": text})
        st, next_q, followups = self.flow.process_answer(st, text)
        return st, next_q, followups

    def upload_crm_data(self, session_id: str, crm_data: dict) -> SessionState:
        """Загрузить данные из CRM в сессию"""
        if session_id not in self.sessions:
            raise ValueError("Session not found")
        
        st = self.sessions[session_id]
        
        # Маппим русские названия полей на английские
        mapped_data = self._map_crm_fields(crm_data)
        
        # Создаем объект CrmDeal
        try:
            crm_deal = CrmDeal(**mapped_data)
            st.crm_data = crm_deal
            print(f"DEBUG: Created CrmDeal object: {crm_deal}")
            
            # Если есть CRM данные, заполняем BANT поля на основе этих данных
            if crm_deal:
                print(f"DEBUG: Calling _populate_bant_from_crm")
                self._populate_bant_from_crm(st, crm_deal)
                # НЕ устанавливаем флаг подтверждения - используем логику с уверенностью
                st.crm_data_requires_confirmation = False
            else:
                print(f"DEBUG: CrmDeal is falsy, not populating BANT")
                st.crm_data_requires_confirmation = False
        except Exception as e:
            print(f"DEBUG: Failed to create CrmDeal: {e}")
            # Если не удалось создать CrmDeal, сохраняем как есть
            st.crm_data = crm_data
            st.crm_data_requires_confirmation = False
        
        # Рассчитываем скоринг после заполнения данных из CRM
        st.record.score = self.flow.calculate_score(st.record)
        
        # Определяем следующий слот для вопросов (с учетом уверенности)
        st.current_slot = self.flow.next_slot(st)
        
        # Обновляем статус заполнения
        from app.core.validator import validate_record
        st.record.filled = validate_record(st.record)
        
        # Генерируем вопрос для менеджера
        if st.current_slot:
            st.last_question = self.flow.ask_question(st.current_slot, st)
        else:
            # Если все поля заполнены с высокой уверенностью, показываем результат
            st.last_question = self._generate_completion_message(st)
        
        return st
    
    def _generate_completion_message(self, state: SessionState) -> str:
        """Генерирует сообщение о завершении BANT квалификации"""
        if not state.record.score:
            return "BANT квалификация завершена. Все данные собраны."
        
        score = state.record.score
        total_score = score.total
        stage = score.stage
        
        # Определяем рекомендации на основе скоринга
        if stage == "qualified":
            recommendation = "Сделка квалифицирована! Рекомендуется переходить к следующему этапу продаж."
        elif stage == "unqualified":
            recommendation = "Сделка не квалифицирована. Рекомендуется пересмотреть подход или отложить."
        else:
            recommendation = "Сделка частично квалифицирована. Требуется дополнительная работа."
        
        message = f"""BANT квалификация завершена!

Результаты:
• Общий балл: {total_score}/100
• Статус: {stage.upper()}
• Бюджет: {score.budget.value} баллов
• Полномочия: {score.authority.value} баллов  
• Потребность: {score.need.value} баллов
• Время: {score.timing.value} баллов

{recommendation}

Следующие шаги:
1. Проанализируйте слабые стороны
2. Подготовьте предложение с учетом выявленных потребностей
3. Определите стратегию работы с ЛПР"""
        
        return message
    
    def _map_crm_fields(self, crm_data: dict) -> dict:
        """Маппинг русских названий полей на английские"""
        field_mapping = {
            "ID сделки": "deal_id",
            "Название сделки": "deal_name",
            "Официальное наименование компании": "company_official",
            "Краткое наименование компании": "company_short",
            "Конечный заказчик": "end_customer",
            "Ожидаемая дата подписания договора": "expected_contract_date",
            "Ответственный": "responsible",
            "ЦК сделки": "competence_center",
            "Источник лида": "lead_source",
            "Форма сделки": "deal_form",
            "Тип вероятности сделки": "probability_type",
            "Этап": "stage",
            "Дата перехода на этап": "stage_date",
            "Статус сделки": "deal_status",
            "Валюта": "currency",
            "Вероятность сделки от этапа": "stage_probability",
            "Ожидаемая выручка с НДС": "expected_revenue_with_vat",
            "Ожидаемая выручка без НДС": "expected_revenue_without_vat",
            "Оценочная маржинальность GM1, %": "estimated_margin_gm1",
            "Тип сделки": "deal_type",
            "Юридическое лицо": "legal_entity",
            "Направление": "direction",
            "Дата завершения договора": "contract_end_date",
            "Порядок продления": "renewal_order",
            "Сумма продуктов с НДС": "product_amount_with_vat",
            "Ключевая сделка": "key_deal",
            "НДС": "vat_rate",
            "WAR": "war",
            "БЕ": "business_unit",
            "Код этапа проекта": "project_stage_code",
            "Номер заявки клиента": "customer_request_number",
            "Максимальный лимит": "max_limit",
            "Партнёры": "partners",
            "Тендер: Тип запроса": "tender_request_type",
            "Тендер: Дата подачи": "tender_submission_date",
            "Причина проигрыша": "loss_reason",
            "Комментарий при закрытии сделки": "closing_comment",
            "Действия при закрытии сделки": "closing_action",
            "Дата изменения": "change_date",
            "ID лида": "lead_id"
        }
        
        print(f"DEBUG: Input CRM data keys: {list(crm_data.keys())}")
        
        mapped_data = {}
        for russian_key, english_key in field_mapping.items():
            if russian_key in crm_data:
                mapped_data[english_key] = crm_data[russian_key]
                print(f"DEBUG: Mapped {russian_key} -> {english_key} = {crm_data[russian_key]}")
        
        print(f"DEBUG: Mapped data: {mapped_data}")
        return mapped_data
    
    def _populate_bant_from_crm(self, state: SessionState, crm_data: CrmDeal):
        """Заполнить BANT поля на основе CRM данных с помощью LLM"""
        print(f"DEBUG: Starting BANT population from CRM data")
        try:
            # Используем LLM для анализа CRM данных
            crm_dict = crm_data.model_dump()
            print(f"DEBUG: CRM data for LLM: {crm_dict}")
            
            # Форматируем промпт с данными CRM
            prompt = CRM_ANALYSIS_PROMPT.format(**crm_dict)
            print(f"DEBUG: LLM prompt length: {len(prompt)}")
            
            messages = [
                {"role": "system", "content": prompt}
            ]
            
            response = self.llm.chat(messages, json_mode=True)
            print(f"DEBUG: LLM response: {response}")
            bant_data = json.loads(response)
            print(f"DEBUG: Parsed BANT data: {bant_data}")
            
            # Обновляем BANT поля на основе анализа LLM
            for slot in ["budget", "authority", "need", "timing"]:
                if slot in bant_data and isinstance(bant_data[slot], dict):
                    current_data = getattr(state.record, slot).model_dump()
                    current_data.update({
                        k: v for k, v in bant_data[slot].items()
                        if v is not None and v != ""
                    })
                    print(f"DEBUG: Updated {slot} data: {current_data}")
                    
                    # Обновляем поле
                    if slot == "budget":
                        from app.core.schema import Budget
                        setattr(state.record, slot, Budget(**current_data))
                    elif slot == "authority":
                        from app.core.schema import Authority
                        setattr(state.record, slot, Authority(**current_data))
                    elif slot == "need":
                        from app.core.schema import Need
                        setattr(state.record, slot, Need(**current_data))
                    elif slot == "timing":
                        from app.core.schema import Timing
                        setattr(state.record, slot, Timing(**current_data))
                        
        except (json.JSONDecodeError, ValidationError, KeyError) as e:
            print(f"DEBUG: LLM failed, using fallback: {e}")
            # Fallback на простую логику если LLM не сработал
            self._simple_crm_population(state, crm_data)
    
    def _simple_crm_population(self, state: SessionState, crm_data: CrmDeal):
        """Простое заполнение BANT полей на основе CRM данных (fallback)"""
        print(f"DEBUG: Using simple CRM population fallback")
        
        # Budget - используем данные о выручке
        if crm_data.expected_revenue_with_vat:
            print(f"DEBUG: Setting budget from revenue: {crm_data.expected_revenue_with_vat}")
            state.record.budget.have_budget = True
            state.record.budget.amount_min = crm_data.expected_revenue_with_vat * 0.8  # 80% от ожидаемой выручки
            state.record.budget.amount_max = crm_data.expected_revenue_with_vat * 1.2  # 120% от ожидаемой выручки
            state.record.budget.currency = crm_data.currency or "RUB"
            state.record.budget.budget_status = "AVAILABLE"
            print(f"DEBUG: Budget set: have_budget={state.record.budget.have_budget}, amount_min={state.record.budget.amount_min}, amount_max={state.record.budget.amount_max}")
        
        # Authority - используем ответственного
        if crm_data.responsible:
            print(f"DEBUG: Setting authority from responsible: {crm_data.responsible}")
            state.record.authority.decision_maker = crm_data.responsible
            state.record.authority.uncertain = False  # Данные из CRM считаем точными
            print(f"DEBUG: Authority set: decision_maker={state.record.authority.decision_maker}")
        
        # Need - используем название сделки как индикатор потребности
        if crm_data.deal_name:
            print(f"DEBUG: Setting need from deal name: {crm_data.deal_name}")
            state.record.need.pain_points = [f"Потребность в {crm_data.deal_name.lower()}"]
            state.record.need.priority = "high"  # Сделки в CRM обычно имеют высокий приоритет
            print(f"DEBUG: Need set: pain_points={state.record.need.pain_points}, priority={state.record.need.priority}")
        
        # Timing - используем даты из CRM
        if crm_data.expected_contract_date:
            print(f"DEBUG: Setting timing from contract date: {crm_data.expected_contract_date}")
            state.record.timing.timeframe = "this_year"  # По умолчанию текущий год
            state.record.timing.deadline = crm_data.expected_contract_date
            print(f"DEBUG: Timing set: timeframe={state.record.timing.timeframe}, deadline={state.record.timing.deadline}")
        
        print(f"DEBUG: Final BANT record after population: {state.record.model_dump()}")

    def get_session(self, session_id: str) -> SessionState:
        if session_id not in self.sessions:
            raise ValueError("Session not found")
        return self.sessions[session_id]
