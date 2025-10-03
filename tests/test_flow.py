# tests/test_flow.py
import pytest
from unittest.mock import Mock, patch
from app.core.flow import BantFlow
from app.core.schema import SessionState, BantRecord, Budget, Authority, Need, Timing, SlotScore, BantScore

class MockLLM:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
    
    def chat(self, messages, temperature=0.2, json_mode=False):
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return "{}"

def test_next_slot_empty_record():
    """Тест определения следующего слота для пустой записи"""
    llm = MockLLM([])
    flow = BantFlow(llm)
    
    record = BantRecord(deal_id="DEAL-001")
    # Создаем полностью пустую запись
    record.budget = Budget(currency=None)  # Убираем дефолтное значение
    state = SessionState(
        session_id="session-123",
        deal_id="DEAL-001",
        record=record
    )
    
    next_slot = flow.next_slot(state)
    assert next_slot == "budget"  # Первый слот

def test_next_slot_partial_record():
    """Тест определения следующего слота для частично заполненной записи"""
    llm = MockLLM([])
    flow = BantFlow(llm)
    
    record = BantRecord(deal_id="DEAL-001")
    record.budget = Budget(have_budget=True, amount_min=100000)
    
    state = SessionState(
        session_id="session-123",
        deal_id="DEAL-001",
        record=record
    )
    
    next_slot = flow.next_slot(state)
    assert next_slot == "authority"  # Следующий незаполненный слот

def test_next_slot_full_record():
    """Тест определения следующего слота для полностью заполненной записи"""
    llm = MockLLM([])
    flow = BantFlow(llm)
    
    record = BantRecord(deal_id="DEAL-001")
    record.budget = Budget(have_budget=True, amount_min=100000)
    record.authority = Authority(decision_maker="Иван Иванов")
    record.need = Need(pain_points=["Проблема"])
    record.timing = Timing(timeframe="this_month")
    
    state = SessionState(
        session_id="session-123",
        deal_id="DEAL-001",
        record=record
    )
    
    next_slot = flow.next_slot(state)
    assert next_slot is None  # Все слоты заполнены

def test_ask_question():
    """Тест получения вопроса для слота"""
    llm = MockLLM([])
    flow = BantFlow(llm)
    
    question = flow.ask_question("budget")
    assert "бюджет" in question.lower()
    
    question = flow.ask_question("authority")
    assert "лпр" in question.lower() or "согласовани" in question.lower()

@patch('app.core.flow.parse_bant_with_llm')
@patch('app.core.flow.validate_record')
def test_process_answer_success(mock_validate, mock_parse):
    """Тест успешной обработки ответа"""
    # Настройка моков
    mock_parse.return_value = {
        "budget": {"have_budget": True, "amount_min": 100000, "currency": "RUB"}
    }
    mock_validate.return_value = "partial"
    
    llm = MockLLM(['{"budget": {"have_budget": true, "amount_min": 100000, "currency": "RUB"}}'])
    flow = BantFlow(llm)
    
    record = BantRecord(deal_id="DEAL-001")
    state = SessionState(
        session_id="session-123",
        deal_id="DEAL-001",
        record=record
    )
    
    new_state, next_question, followups = flow.process_answer(state, "У нас есть бюджет 100000 рублей")
    
    assert new_state.record.budget.have_budget is True
    assert new_state.record.budget.amount_min == 100000
    assert new_state.record.budget.currency == "RUB"
    assert next_question is not None
    assert isinstance(followups, list)
    
    # Проверяем, что моки были вызваны
    mock_parse.assert_called_once()
    mock_validate.assert_called_once()

@patch('app.core.flow.parse_bant_with_llm')
@patch('app.core.flow.parse_bant_json_text')
@patch('app.core.flow.validate_record')
def test_process_answer_validation_error(mock_validate, mock_parse_json, mock_parse_llm):
    """Тест обработки ошибки валидации"""
    # Настройка моков для ошибки валидации
    mock_parse_llm.side_effect = ValueError("Invalid JSON")  # Первый вызов падает
    mock_parse_json.side_effect = [
        ValueError("Invalid JSON"),
        {"budget": {"have_budget": True}}  # Исправленный JSON
    ]
    mock_validate.return_value = "partial"
    
    llm = MockLLM([
        '{"budget": {"have_budget": true}}',  # Первый ответ
        '{"budget": {"have_budget": true}}'   # Исправленный ответ
    ])
    flow = BantFlow(llm)
    
    record = BantRecord(deal_id="DEAL-001")
    state = SessionState(
        session_id="session-123",
        deal_id="DEAL-001",
        record=record
    )
    
    new_state, next_question, followups = flow.process_answer(state, "У нас есть бюджет")
    
    # Проверяем, что была попытка исправления
    assert mock_parse_json.call_count == 2
    assert new_state.record.budget.have_budget is True
    assert isinstance(followups, list)

def test_process_answer_completion():
    """Тест завершения опроса"""
    llm = MockLLM(['{"budget": {"have_budget": true}}'])
    flow = BantFlow(llm)
    
    # Создаем запись с заполненными всеми слотами кроме budget
    record = BantRecord(deal_id="DEAL-001")
    record.authority = Authority(decision_maker="Иван Иванов")
    record.need = Need(pain_points=["Проблема"])
    record.timing = Timing(timeframe="this_month")
    
    state = SessionState(
        session_id="session-123",
        deal_id="DEAL-001",
        record=record
    )
    
    with patch('app.core.flow.parse_bant_json_text') as mock_parse:
        mock_parse.return_value = {"budget": {"have_budget": True}}
        
        new_state, next_question, followups = flow.process_answer(state, "У нас есть бюджет")
        
        assert new_state.current_slot is None
        assert next_question is None
        assert isinstance(followups, list)

def test_heuristic_score_budget():
    """Тест эвристического скоринга для Budget"""
    llm = MockLLM([])
    flow = BantFlow(llm)
    
    # Пустой бюджет (не упоминался)
    record = BantRecord(deal_id="DEAL-001")
    score = flow._heuristic_score(record)
    assert score.budget.value == 0  # have_budget is None - не заполнено
    
    # Явно указано, что бюджета нет
    record.budget.have_budget = False
    score = flow._heuristic_score(record)
    assert score.budget.value == 2  # have_budget is False - есть информация, но бюджета нет
    
    # Бюджет без суммы
    record.budget.have_budget = True
    score = flow._heuristic_score(record)
    assert score.budget.value == 9
    
    # Бюджет с диапазоном
    record.budget.amount_min = 100000
    record.budget.amount_max = 500000
    record.budget.currency = "RUB"
    score = flow._heuristic_score(record)
    assert score.budget.value == 22

def test_heuristic_score_authority():
    """Тест эвристического скоринга для Authority"""
    llm = MockLLM([])
    flow = BantFlow(llm)
    
    record = BantRecord(deal_id="DEAL-001")
    
    # Пустая авторитетность
    score = flow._heuristic_score(record)
    assert score.authority.value == 0
    
    # Только ЛПР
    record.authority.decision_maker = "Иван Иванов"
    score = flow._heuristic_score(record)
    assert score.authority.value == 5
    
    # ЛПР + стейкхолдеры
    record.authority.stakeholders = ["Петр Петров"]
    score = flow._heuristic_score(record)
    assert score.authority.value == 20
    
    # ЛПР + стейкхолдеры + процесс
    record.authority.decision_process = "Согласование с руководством"
    score = flow._heuristic_score(record)
    assert score.authority.value == 23

def test_heuristic_score_need():
    """Тест эвристического скоринга для Need"""
    llm = MockLLM([])
    flow = BantFlow(llm)
    
    record = BantRecord(deal_id="DEAL-001")
    
    # Пустая потребность
    score = flow._heuristic_score(record)
    assert score.need.value == 0
    
    # Частично заполненная потребность
    record.need.pain_points = ["Проблема"]
    score = flow._heuristic_score(record)
    assert score.need.value == 8
    
    # Полностью заполненная потребность
    record.need.pain_points = ["Проблема 1", "Проблема 2"]
    record.need.success_criteria = ["Критерий 1", "Критерий 2"]
    score = flow._heuristic_score(record)
    assert score.need.value == 22
    
    # С приоритетом и решением
    record.need.current_solution = "Excel"
    record.need.priority = "high"
    score = flow._heuristic_score(record)
    assert score.need.value == 27

def test_heuristic_score_timing():
    """Тест эвристического скоринга для Timing"""
    llm = MockLLM([])
    flow = BantFlow(llm)
    
    record = BantRecord(deal_id="DEAL-001")
    
    # Пустое время
    score = flow._heuristic_score(record)
    assert score.timing.value == 2
    
    # Этот месяц
    record.timing.timeframe = "this_month"
    score = flow._heuristic_score(record)
    assert score.timing.value == 18
    
    # Этот год
    record.timing.timeframe = "this_year"
    score = flow._heuristic_score(record)
    assert score.timing.value == 10

def test_heuristic_followups():
    """Тест эвристической генерации followup вопросов"""
    llm = MockLLM([])
    flow = BantFlow(llm)
    
    # Создаем score с низкими значениями
    budget_score = SlotScore(value=5, confidence=0.3)
    authority_score = SlotScore(value=8, confidence=0.4)
    need_score = SlotScore(value=10, confidence=0.5)
    timing_score = SlotScore(value=3, confidence=0.2)
    
    score = BantScore(
        budget=budget_score,
        authority=authority_score,
        need=need_score,
        timing=timing_score,
        total=26,
        stage="unqualified"
    )
    
    followups = flow._heuristic_followups(score)
    
    # Должны быть followup для слотов с низким score (максимум 2)
    assert len(followups) == 2
    assert any("бюджет" in f.lower() for f in followups)
    assert any("решение" in f.lower() for f in followups)

@patch('app.core.flow.parse_bant_with_llm')
@patch('app.core.flow.validate_record')
def test_process_answer_with_scoring(mock_validate, mock_parse):
    """Тест обработки ответа с скорингом"""
    # Настройка моков
    mock_parse.return_value = {
        "budget": {"have_budget": True, "amount_min": 100000, "currency": "RUB"}
    }
    mock_validate.return_value = "partial"
    
    llm = MockLLM(['{"budget": {"have_budget": true, "amount_min": 100000, "currency": "RUB"}}'])
    flow = BantFlow(llm)
    
    record = BantRecord(deal_id="DEAL-001")
    state = SessionState(
        session_id="session-123",
        deal_id="DEAL-001",
        record=record
    )
    
    new_state, next_question, followups = flow.process_answer(state, "У нас есть бюджет 100000 рублей")
    
    # Проверяем, что скоринг был рассчитан
    assert new_state.record.score is not None
    assert new_state.record.score.total >= 0
    assert new_state.record.score.total <= 100
    
    # Проверяем, что followups были сгенерированы
    assert isinstance(followups, list)
    assert len(followups) <= 2
    
    # Проверяем, что данные были обновлены
    assert new_state.record.budget.have_budget is True
    assert new_state.record.budget.amount_min == 100000
