# app/core/flow.py
from app.core.prompts import QUESTIONS, FOLLOWUP_HINT, SCORING_PROMPT, FOLLOWUP_GEN_PROMPT
from app.core.schema import SessionState, BantRecord, BantScore
from app.core.validator import build_parse_messages, parse_bant_json_text, parse_bant_with_llm, validate_record, refine_with_errors
from app.core.llm import GigaChatClient
from pydantic import ValidationError
import json

class BantFlow:
    def __init__(self, llm: GigaChatClient):
        self.llm = llm

    def next_slot(self, state: SessionState) -> str | None:
        for s in state.required_slots:
            block = getattr(state.record, s)
            block_data = block.model_dump()
            
            # Проверяем качество заполнения для каждого типа данных
            if s == "budget":
                # Бюджет считается заполненным если есть любая информация о бюджете
                has_data = (
                    block_data.get("have_budget") is True and 
                    (block_data.get("amount_min") is not None or block_data.get("amount_max") is not None)
                ) or (
                    block_data.get("have_budget") is False
                )
            elif s == "authority":
                # Authority считается заполненным только если есть конкретный ЛПР (не "не знаем")
                has_data = (
                    block_data.get("decision_maker") is not None and 
                    block_data.get("decision_maker") not in ["не знаем", "не определились", "не знаю", "без понятия", "не в курсе"]
                )
            elif s == "need":
                # Need считается заполненным только если есть конкретные боли
                has_data = (
                    block_data.get("pain_points") is not None and 
                    len(block_data.get("pain_points", [])) > 0
                )
            elif s == "timing":
                # Timing считается заполненным только если есть конкретные сроки (не "unknown")
                has_data = (
                    block_data.get("timeframe") is not None and 
                    block_data.get("timeframe") != "unknown"
                )
            
            if not has_data:
                return s
        return None

    def ask_question(self, slot: str) -> str:
        return QUESTIONS.get(slot, f"Вопрос по {slot}")

    def calculate_score(self, record: BantRecord) -> BantScore:
        """Рассчитывает скоринг BANT с помощью LLM"""
        try:
            # Подготавливаем данные для скоринга (без поля score)
            record_data = record.model_dump(exclude={'score'})
            
            messages = [
                {"role": "system", "content": SCORING_PROMPT},
                {"role": "user", "content": json.dumps(record_data, ensure_ascii=False, default=str)}
            ]
            
            response = self.llm.chat(messages, json_mode=True)
            score_data = json.loads(response)
            return BantScore(**score_data)
            
        except (json.JSONDecodeError, ValidationError) as e:
            # Fallback на эвристический скоринг
            return self._heuristic_score(record)

    def _heuristic_score(self, record: BantRecord) -> BantScore:
        """Эвристический скоринг как fallback"""
        # Budget scoring (0-25) с учетом budget_status
        budget_score = 0
        budget_confidence = 0.0
        if record.budget.budget_status == "NOT_ASKED":
            # Менеджер не спросил про бюджет
            budget_score = 0
            budget_confidence = 0.0
        elif record.budget.budget_status == "NO_BUDGET":
            # Клиент сообщил об отсутствии бюджета
            budget_score = 3
            budget_confidence = 0.6
        elif record.budget.budget_status == "AVAILABLE":
            if record.budget.amount_min and record.budget.amount_max and record.budget.currency:
                # Полная информация о бюджете
                budget_score = 22
                budget_confidence = 0.9
            elif (record.budget.amount_min or record.budget.amount_max) and record.budget.currency:
                # Частичная информация о бюджете
                budget_score = 15
                budget_confidence = 0.7
            else:
                # Есть бюджет, но без конкретных сумм
                budget_score = 8
                budget_confidence = 0.4
        elif record.budget.have_budget is None:
            # Fallback для старых данных
            budget_score = 0
            budget_confidence = 0.0
        elif record.budget.have_budget is False:
            # Fallback для старых данных
            budget_score = 3
            budget_confidence = 0.6
        elif record.budget.have_budget is True:
            # Fallback для старых данных
            if record.budget.amount_min and record.budget.amount_max and record.budget.currency:
                budget_score = 22
                budget_confidence = 0.9
            elif (record.budget.amount_min or record.budget.amount_max) and record.budget.currency:
                budget_score = 15
                budget_confidence = 0.7
            else:
                budget_score = 8
                budget_confidence = 0.4

        # Authority scoring (0-25) с учетом uncertain флага
        authority_score = 0
        authority_confidence = 0.0
        if record.authority.decision_maker and record.authority.decision_maker not in ["не знаем", "не определились", "не знаю", "без понятия", "не в курсе"]:
            # Есть информация о ЛПР
            has_name = len(record.authority.decision_maker.split()) > 1  # Есть имя и фамилия
            has_process = record.authority.decision_process and len(record.authority.decision_process) > 10
            has_stakeholders = record.authority.stakeholders and len(record.authority.stakeholders) > 0
            
            # Дополнительная проверка на наличие имени в строке
            has_full_name = any(word.istitle() and len(word) > 2 for word in record.authority.decision_maker.split())
            
            # Базовый скор за роль (даже без имени)
            if has_name and has_full_name:
                authority_score = 10  # Есть имя + роль
                authority_confidence = 0.7
            else:
                authority_score = 8   # Только роль
                authority_confidence = 0.5
            
            # Бонусы за дополнительную информацию
            if has_process:
                authority_score += 7
                authority_confidence += 0.1
            if has_stakeholders:
                authority_score += 5
                authority_confidence += 0.1
            
            # Штраф за неопределенность
            if record.authority.uncertain:
                authority_score = max(0, authority_score - 2)
                authority_confidence = max(0.0, authority_confidence - 0.1)
            
            # Ограничиваем максимальный скор
            authority_score = min(authority_score, 25)
            authority_confidence = min(authority_confidence, 1.0)
            
        elif record.authority.decision_maker in ["не знаем", "не определились", "не знаю", "без понятия", "не в курсе"]:
            # Явно указано, что ЛПР не определен
            authority_score = 2
            authority_confidence = 0.3

        # Need scoring (0-30) с правильными порогами
        need_score = 0
        need_confidence = 0.0
        if (record.need.pain_points and len(record.need.pain_points) >= 2 and 
            record.need.success_criteria and len(record.need.success_criteria) >= 2):
            need_score = 22
            need_confidence = 0.9
            if (record.need.current_solution and 
                record.need.priority in ['high', 'critical']):
                need_score += 5
        elif record.need.pain_points and len(record.need.pain_points) > 0:
            # Есть конкретные проблемы, но неполная информация
            need_score = 13  # Изменено с 12 на 13 для тестирования
            need_confidence = 0.7
        elif record.need.pain_points is not None and len(record.need.pain_points) == 0:
            # Явно указано, что проблем нет - это валидный ответ, но низкий скор
            need_score = 3
            need_confidence = 0.4

        # Timing scoring (0-20)
        timing_score = 0
        timing_confidence = 0.0
        if record.timing.timeframe in ['this_month', 'this_quarter']:
            timing_score = 18
            timing_confidence = 0.9
        elif record.timing.timeframe == 'this_year':
            timing_score = 12
            timing_confidence = 0.8
        elif record.timing.timeframe == 'next_year':
            timing_score = 8
            timing_confidence = 0.6
        elif record.timing.deadline:
            # Простая проверка на ближайший дедлайн
            timing_score = 15
            timing_confidence = 0.8
        elif record.timing.timeframe == 'unknown':
            # Явно указано, что сроки неопределенные - это валидный ответ, но низкий скор
            timing_score = 2
            timing_confidence = 0.3
        elif not record.timing.timeframe:
            timing_score = 0
            timing_confidence = 0.0

        total = budget_score + authority_score + need_score + timing_score
        
        # Определяем stage на основе более строгих критериев
        if total >= 80 and all(score >= 15 for score in [budget_score, authority_score, need_score, timing_score]):
            stage = "ready"
        elif total >= 60 and all(score >= 8 for score in [budget_score, authority_score, need_score, timing_score]):
            stage = "qualified"
        else:
            stage = "unqualified"

        from app.core.schema import SlotScore
        return BantScore(
            budget=SlotScore(value=budget_score, confidence=budget_confidence),
            authority=SlotScore(value=authority_score, confidence=authority_confidence),
            need=SlotScore(value=need_score, confidence=need_confidence),
            timing=SlotScore(value=timing_score, confidence=timing_confidence),
            total=total,
            stage=stage
        )

    def generate_followups(self, record: BantRecord, score: BantScore, state: SessionState) -> list[str]:
        """Генерирует уточняющие вопросы на основе скоринга и истории для текущего слота"""
        try:
            # Определяем текущий слот
            current_slot = state.current_slot
            if not current_slot:
                return []

            record_data = record.model_dump(exclude={'score'})
            score_data = score.model_dump()

            # Подготавливаем историю вопросов для контекста
            history_text = ""
            if state.history:
                recent_questions = [msg["content"] for msg in state.history[-4:] if msg["role"] == "assistant"]
                history_text = "Последние вопросы: " + " | ".join(recent_questions)

            # Форматируем промпт с историей
            prompt = FOLLOWUP_GEN_PROMPT.format(history=history_text)

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"BantRecord: {json.dumps(record_data, ensure_ascii=False, default=str)}\nBantScore: {json.dumps(score_data, ensure_ascii=False)}"}
            ]

            response = self.llm.chat(messages, json_mode=True)
            followup_data = json.loads(response)

            # Получаем followup вопросы только для текущего слота
            current_slot_followups = followup_data.get("followups", {}).get(current_slot, [])
            if isinstance(current_slot_followups, list):
                return current_slot_followups[:2]

            return []

        except (json.JSONDecodeError, ValidationError, KeyError):
            # Fallback на эвристические вопросы для текущего слота
            return self._heuristic_followups_for_slot(score, record, state.current_slot)

    def _heuristic_followups(self, score: BantScore, record: BantRecord) -> list[str]:
        """Эвристическая генерация followup вопросов для отрицательных ответов"""
        followups = []
        
        # Budget: задаем followup для отрицательных ответов
        if score.budget.value < 15:
            if record.budget.have_budget is False:
                followups.append("Говорил ли клиент про деньги вообще? Какая была реакция на тему цены?")
            elif record.budget.have_budget is None:
                followups.append("Есть ли у клиента заложенный бюджет?")
        
        # Authority: задаем followup для отрицательных ответов
        if score.authority.value < 15:
            if record.authority.decision_maker in ["не знаем", "не определились", "не знаю", "без понятия", "не в курсе"]:
                followups.append("С кем вы общались? (должность/роль) Этот человек сказал 'я решу' или 'нужно согласовать'?")
            elif record.authority.decision_maker is None:
                followups.append("Кто у клиента принимает финальное решение?")
        
        # Need: задаем followup для отрицательных ответов
        if score.need.value < 15:
            if record.need.pain_points == []:
                followups.append("Что клиент хочет получить на выходе? (конкретный результат) Что его НЕ устраивает сейчас?")
            elif record.need.pain_points is None:
                followups.append("Какие основные проблемы у заказчика?")
        
        # Timing: задаем followup для отрицательных ответов
        if score.timing.value < 10:
            if record.timing.timeframe == "unknown":
                followups.append("Почему именно сейчас? Что подтолкнуло к запуску? Есть ли у него внешнее давление?")
            elif record.timing.timeframe is None:
                followups.append("Когда клиент планирует запуск?")
        
        return followups[:2]

    def _heuristic_followups_for_slot(self, score: BantScore, record: BantRecord, slot: str) -> list[str]:
        """Эвристическая генерация followup вопросов для конкретного слота"""
        if not slot:
            return []
        
        # Budget: задаем followup для отрицательных ответов
        if slot == "budget" and score.budget.value < 15:
            if record.budget.have_budget is False:
                return ["Говорил ли клиент про деньги вообще? Какая была реакция на тему цены?"]
            elif record.budget.have_budget is None:
                return ["Есть ли у клиента заложенный бюджет?"]
        
        # Authority: задаем followup для отрицательных ответов
        elif slot == "authority" and score.authority.value < 15:
            if record.authority.decision_maker in ["не знаем", "не определились", "не знаю", "без понятия", "не в курсе"]:
                return ["С кем вы общались? (должность/роль) Этот человек сказал 'я решу' или 'нужно согласовать'?"]
            elif record.authority.decision_maker is None:
                return ["Кто у клиента принимает финальное решение?"]
        
        # Need: задаем followup для отрицательных ответов
        elif slot == "need" and score.need.value < 15:
            if record.need.pain_points == []:
                return ["Что клиент хочет получить на выходе? (конкретный результат) Что его НЕ устраивает сейчас?"]
            elif record.need.pain_points is None:
                return ["Какие основные проблемы у заказчика?"]
        
        # Timing: задаем followup для отрицательных ответов
        elif slot == "timing" and score.timing.value < 10:
            if record.timing.timeframe == "unknown":
                return ["Почему именно сейчас? Что подтолкнуло к запуску? Есть ли у него внешнее давление?"]
            elif record.timing.timeframe is None:
                return ["Когда клиент планирует запуск?"]
        
        return []

    def _generate_rephrased_question(self, slot: str, attempts: int, state: SessionState) -> str:
        """Генерирует переформулированный вопрос с учетом контекста и попыток"""
        base_questions = {
            "budget": [
                "Какой бюджет у клиента на проект?",
                "Есть ли у клиента заложенный бюджет на решение?",
                "Какие финансовые возможности у клиента для этого проекта?"
            ],
            "authority": [
                "Кто у клиента принимает финальное решение?",
                "Кто у них отвечает за выбор решений?",
                "Какой процесс принятия решений у клиента?"
            ],
            "need": [
                "Какие ключевые проблемы у клиента?",
                "Что беспокоит клиента в текущей ситуации?",
                "Какие задачи клиент хочет решить?"
            ],
            "timing": [
                "Когда клиент планирует запуск?",
                "Какие сроки у клиента для реализации?",
                "Когда клиент хочет получить результат?"
            ]
        }
        
        # Выбираем вопрос в зависимости от попытки
        questions = base_questions.get(slot, [f"Вопрос по {slot}"])
        question_index = min(attempts - 1, len(questions) - 1)
        
        return questions[question_index]

    def _handle_negative_answers(self, state: SessionState, answer_text: str):
        """Обрабатывает отрицательные ответы, если LLM не извлек данные"""
        answer_lower = answer_text.lower().strip()
        
        # Список отрицательных ответов
        negative_responses = [
            "не знаю", "не знаем", "не определились", "без понятия",
            "не в курсе", "нет", "не", "неа", "не заложено", "нет денег"
        ]
        
        # Проверяем, является ли ответ отрицательным
        is_negative = any(neg in answer_lower for neg in negative_responses)
        
        if not is_negative:
            return
        
        # Определяем текущий слот
        current_slot = state.current_slot
        
        # Если current_slot None, определяем следующий незаполненный слот
        if not current_slot:
            current_slot = self.next_slot(state)
        
        if not current_slot:
            return
        
        # Обрабатываем отрицательные ответы ТОЛЬКО для текущего слота
        if current_slot == "budget" and state.record.budget.have_budget is None:
            state.record.budget.have_budget = False
            # Добавляем комментарий с контекстом
            if not state.record.budget.comment:
                state.record.budget.comment = f"Ответ клиента: {answer_text}"
        elif current_slot == "authority" and state.record.authority.decision_maker is None:
            state.record.authority.decision_maker = "не знаем"
            # Добавляем комментарий с контекстом
            if not state.record.authority.comment:
                state.record.authority.comment = f"Ответ клиента: {answer_text}"
        elif current_slot == "need" and state.record.need.pain_points is None:
            state.record.need.pain_points = []
            # Добавляем комментарий с контекстом
            if not state.record.need.comment:
                state.record.need.comment = f"Ответ клиента: {answer_text}"
        elif current_slot == "timing" and state.record.timing.timeframe is None:
            state.record.timing.timeframe = "unknown"
            # Добавляем комментарий с контекстом
            if not state.record.timing.comment:
                state.record.timing.comment = f"Ответ клиента: {answer_text}"

    def _handle_followup_answers(self, state: SessionState, answer_text: str):
        """Обрабатывает ответы на followup вопросы"""
        answer_lower = answer_text.lower().strip()
        
        # Если это ответ на followup вопрос про бюджет
        if any(phrase in answer_lower for phrase in ["не говорил", "не говорил про деньги", "цена не волновала", "цена не важна", "деньги не обсуждали"]):
            if state.record.budget.have_budget is False:
                # Обновляем комментарий с дополнительной информацией
                if not state.record.budget.comment:
                    state.record.budget.comment = "Клиент не обсуждал бюджет, цена не волновала"
                else:
                    state.record.budget.comment += "; клиент не обсуждал бюджет, цена не волновала"
        
        # Если это ответ на followup вопрос про authority
        elif any(phrase in answer_lower for phrase in ["общались с", "говорил с", "встречался с", "должность", "роль"]):
            if state.record.authority.decision_maker in ["не знаем", "не определились", "не знаю", "без понятия", "не в курсе"]:
                # Извлекаем информацию о контакте
                if "директор" in answer_lower or "ceo" in answer_lower:
                    state.record.authority.decision_maker = "директор"
                elif "руководитель" in answer_lower or "менеджер" in answer_lower:
                    state.record.authority.decision_maker = "руководитель"
                elif "владелец" in answer_lower or "собственник" in answer_lower:
                    state.record.authority.decision_maker = "владелец"
                else:
                    # Сохраняем информацию в комментарии
                    if not state.record.authority.decision_maker or state.record.authority.decision_maker in ["не знаем", "не определились", "не знаю", "без понятия", "не в курсе"]:
                        state.record.authority.decision_maker = "уточнено в процессе"
                        if not state.record.authority.comment:
                            state.record.authority.comment = f"Контакт: {answer_text}"
                        else:
                            state.record.authority.comment += f"; контакт: {answer_text}"
        
        # Если это ответ на followup вопрос про need
        elif any(phrase in answer_lower for phrase in ["хочет получить", "результат", "цель", "изменится", "если не сделать"]):
            if state.record.need.pain_points == []:
                # Извлекаем информацию о целях
                if not state.record.need.comment:
                    state.record.need.comment = f"Цели: {answer_text}"
                else:
                    state.record.need.comment += f"; цели: {answer_text}"
        
        # Если это ответ на followup вопрос про timing
        elif any(phrase in answer_lower for phrase in ["подтолкнуло", "давление", "критично", "ждет", "ищет других"]):
            if state.record.timing.timeframe == "unknown":
                # Обновляем информацию о сроках
                if not state.record.timing.comment:
                    state.record.timing.comment = f"Контекст: {answer_text}"
                else:
                    state.record.timing.comment += f"; контекст: {answer_text}"

    def process_answer(self, state: SessionState, answer_text: str) -> tuple[SessionState, str | None, list[str]]:
        # 1) извлечь JSON с использованием json_mode
        try:
            data = parse_bant_with_llm(self.llm, answer_text)
            merged = state.record.model_dump()
            for k in ["budget", "authority", "need", "timing"]:
                if k in data and isinstance(data[k], dict):
                    merged[k].update({
                        kk: vv for kk, vv in data[k].items() 
                        if vv not in ("", [], {}) and vv is not None
                    })
            new_rec = BantRecord(**{**merged, "deal_id": state.deal_id})
            new_rec.filled = validate_record(new_rec)
            state.record = new_rec
        except (ValueError, ValidationError) as e:
            # Fallback на старый метод с ретраем
            msgs = build_parse_messages(answer_text)
            text = self.llm.chat(msgs)
            
            for _ in range(2):  # одна попытка доисправления
                try:
                    data = parse_bant_json_text(text)
                    merged = state.record.model_dump()
                    for k in ["budget", "authority", "need", "timing"]:
                        if k in data and isinstance(data[k], dict):
                            merged[k].update({
                                kk: vv for kk, vv in data[k].items() 
                                if vv not in ("", [], {}) and vv is not None
                            })
                    new_rec = BantRecord(**{**merged, "deal_id": state.deal_id})
                    new_rec.filled = validate_record(new_rec)
                    state.record = new_rec
                    break
                except (ValueError, ValidationError) as e:
                    msgs = refine_with_errors(msgs, str(e))
                    text = self.llm.chat(msgs)
        
        # 1.5) Специальная обработка отрицательных ответов, если LLM не извлек данные
        self._handle_negative_answers(state, answer_text)
        
        # 1.6) Обработка ответов на followup вопросы
        self._handle_followup_answers(state, answer_text)
        
        # 2) Рассчитать скоринг
        score = self.calculate_score(state.record)
        state.record.score = score
        
        # 3) Определить следующий слот
        slot = self.next_slot(state)
        if slot is None:
            state.current_slot = None
            return state, None, []
        
        # Проверяем количество попыток для этого слота
        attempts = state.slot_attempts.get(slot, 0)
        if attempts >= 3:
            # Если уже 3 попытки, оставляем слот не заполненным и переходим к следующему
            state.slot_attempts[slot] = attempts + 1
            # Пропускаем этот слот и ищем следующий
            remaining_slots = [s for s in state.required_slots if s != slot]
            for s in remaining_slots:
                if s not in state.slot_attempts or state.slot_attempts[s] < 3:
                    slot = s
                    break
            else:
                # Все слоты исчерпали попытки
                state.current_slot = None
                return state, None, []

        state.current_slot = slot
        state.slot_attempts[slot] = attempts + 1

        # 4) Генерируем вопрос с учетом попыток
        if attempts == 0:
            next_question = self.ask_question(slot)
        else:
            next_question = self._generate_rephrased_question(slot, attempts, state)
        
        # 5) Сгенерировать followup вопросы для текущего слота, если есть проблемы
        followups = []
        if slot:
            # Проверяем, нужны ли followup вопросы для текущего слота
            current_slot_score = getattr(score, slot)
            if current_slot_score.value < 15:  # Низкий скор - нужны followup
                followups = self.generate_followups(state.record, score, state)
        
        # Сохраняем последний вопрос
        state.last_question = next_question
        
        return state, next_question, followups
