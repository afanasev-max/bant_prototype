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
            
            # Проверяем, есть ли хотя бы одно непустое значение
            has_data = any(v is not None and v != "" and v != [] for v in block_data.values())
            
            # Дополнительная проверка для каждого типа данных
            if s == "budget":
                # Для бюджета считаем заполненным если have_budget не None (даже если false)
                has_data = block_data.get("have_budget") is not None
            elif s == "authority":
                # Для authority считаем заполненным если есть decision_maker (даже если "не знаем")
                has_data = block_data.get("decision_maker") is not None
            elif s == "need":
                # Для need считаем заполненным если есть pain_points (даже если пустой список)
                has_data = block_data.get("pain_points") is not None
            elif s == "timing":
                # Для timing считаем заполненным если есть timeframe (даже если "unknown")
                has_data = block_data.get("timeframe") is not None
            
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
        # Budget scoring (0-25)
        budget_score = 0
        if record.budget.have_budget is None:
            # Бюджет не упоминался вообще - не заполнено
            budget_score = 0
        elif record.budget.have_budget is False:
            # Явно указано, что бюджета нет - это валидный ответ
            budget_score = 8
        elif record.budget.amount_min and record.budget.amount_max and record.budget.currency:
            # Полная информация о бюджете
            budget_score = 22
        elif (record.budget.amount_min or record.budget.amount_max) and record.budget.currency:
            # Частичная информация о бюджете
            budget_score = 12
        elif record.budget.have_budget is True:
            # Есть бюджет, но без конкретных сумм
            budget_score = 9

        # Authority scoring (0-25)
        authority_score = 0
        if record.authority.decision_maker and record.authority.stakeholders:
            authority_score = 20
            if record.authority.decision_process:
                authority_score += 3
        elif record.authority.decision_maker:
            # Есть ЛПР, но нет stakeholders
            authority_score = 12
        elif record.authority.decision_maker == "не знаем" or record.authority.decision_maker == "не определились":
            # Явно указано, что ЛПР не определен - это валидный ответ
            authority_score = 6

        # Need scoring (0-30)
        need_score = 0
        if (record.need.pain_points and len(record.need.pain_points) >= 2 and 
            record.need.success_criteria and len(record.need.success_criteria) >= 2):
            need_score = 22
            if (record.need.current_solution and 
                record.need.priority in ['high', 'critical']):
                need_score += 5
        elif record.need.pain_points and len(record.need.pain_points) > 0:
            # Есть конкретные проблемы
            need_score = 12
        elif record.need.pain_points is not None and len(record.need.pain_points) == 0:
            # Явно указано, что проблем нет - это валидный ответ
            need_score = 8

        # Timing scoring (0-20)
        timing_score = 0
        if record.timing.timeframe in ['this_month', 'this_quarter']:
            timing_score = 18
        elif record.timing.timeframe == 'this_year':
            timing_score = 10
        elif record.timing.deadline:
            # Простая проверка на ближайший дедлайн
            timing_score = 15
        elif record.timing.timeframe == 'unknown':
            # Явно указано, что сроки неопределенные - это валидный ответ
            timing_score = 6
        elif not record.timing.timeframe:
            timing_score = 2

        total = budget_score + authority_score + need_score + timing_score
        
        # Определяем stage
        if total >= 80 and all(score >= 0.6 for score in [0.8, 0.8, 0.8, 0.8]):  # placeholder confidence
            stage = "ready"
        elif total >= 60 and all(score >= 10 for score in [budget_score, authority_score, need_score, timing_score]):
            stage = "qualified"
        else:
            stage = "unqualified"

        from app.core.schema import SlotScore
        return BantScore(
            budget=SlotScore(value=budget_score, confidence=0.8),
            authority=SlotScore(value=authority_score, confidence=0.8),
            need=SlotScore(value=need_score, confidence=0.8),
            timing=SlotScore(value=timing_score, confidence=0.8),
            total=total,
            stage=stage
        )

    def generate_followups(self, record: BantRecord, score: BantScore) -> list[str]:
        """Генерирует уточняющие вопросы на основе скоринга"""
        try:
            record_data = record.model_dump(exclude={'score'})
            score_data = score.model_dump()
            
            messages = [
                {"role": "system", "content": FOLLOWUP_GEN_PROMPT},
                {"role": "user", "content": f"BantRecord: {json.dumps(record_data, ensure_ascii=False, default=str)}\nBantScore: {json.dumps(score_data, ensure_ascii=False)}"}
            ]
            
            response = self.llm.chat(messages, json_mode=True)
            followup_data = json.loads(response)
            
            # Собираем все followup вопросы в один список
            all_followups = []
            for slot_followups in followup_data.get("followups", {}).values():
                if isinstance(slot_followups, list):
                    all_followups.extend(slot_followups)
            
            # Возвращаем максимум 2 вопроса
            return all_followups[:2]
            
        except (json.JSONDecodeError, ValidationError, KeyError):
            # Fallback на эвристические вопросы
            return self._heuristic_followups(score, record)

    def _heuristic_followups(self, score: BantScore, record: BantRecord) -> list[str]:
        """Эвристическая генерация followup вопросов с проверкой на повторные вопросы"""
        followups = []
        
        # Budget: задаем вопрос только если have_budget=null (неопределенно)
        if score.budget.value < 12 and record.budget.have_budget is None:
            followups.append("Какой бюджет у клиента на проект?")
        
        # Authority: задаем вопрос только если decision_maker=null
        if score.authority.value < 12 and record.authority.decision_maker is None:
            followups.append("Кто у клиента принимает финальное решение?")
        
        # Need: задаем вопрос только если pain_points=null (неопределенно)
        if score.need.value < 15 and record.need.pain_points is None:
            followups.append("Какие основные проблемы у заказчика?")
        
        # Timing: задаем вопрос только если timeframe=null
        if score.timing.value < 8 and record.timing.timeframe is None:
            followups.append("Когда клиент планирует запуск?")
        
        return followups[:2]

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
        
        # 2) Рассчитать скоринг
        score = self.calculate_score(state.record)
        state.record.score = score
        
        # 3) Сгенерировать followup вопросы
        followups = self.generate_followups(state.record, score)
        
        # 4) Определить следующий вопрос
        if followups:
            # Если есть followup вопросы, используем первый
            next_question = followups[0]
            state.current_slot = None  # followup не привязан к конкретному слоту
        else:
            # Иначе определяем следующий слот
            slot = self.next_slot(state)
            if slot is None:
                state.current_slot = None
                return state, None, followups
            
            state.current_slot = slot
            next_question = self.ask_question(slot)
        
        return state, next_question, followups
