# tests/test_schema.py
import pytest
from datetime import date
from app.core.schema import Budget, Authority, Need, Timing, BantRecord, SessionState, SlotScore, BantScore

def test_budget_creation():
    """Тест создания объекта Budget"""
    budget = Budget()
    assert budget.have_budget is None
    assert budget.amount_min is None
    assert budget.amount_max is None
    assert budget.currency == "RUB"
    assert budget.comment is None

def test_budget_with_data():
    """Тест создания Budget с данными"""
    budget = Budget(
        have_budget=True,
        amount_min=100000,
        amount_max=500000,
        currency="USD",
        comment="Планируемый бюджет"
    )
    assert budget.have_budget is True
    assert budget.amount_min == 100000
    assert budget.amount_max == 500000
    assert budget.currency == "USD"
    assert budget.comment == "Планируемый бюджет"

def test_authority_creation():
    """Тест создания объекта Authority"""
    authority = Authority()
    assert authority.decision_maker is None
    assert authority.stakeholders is None
    assert authority.decision_process is None
    assert authority.risks is None

def test_authority_with_data():
    """Тест создания Authority с данными"""
    authority = Authority(
        decision_maker="Иван Иванов",
        stakeholders=["Петр Петров", "Мария Сидорова"],
        decision_process="Согласование с руководством",
        risks=["Долгое согласование"]
    )
    assert authority.decision_maker == "Иван Иванов"
    assert len(authority.stakeholders) == 2
    assert authority.decision_process == "Согласование с руководством"
    assert len(authority.risks) == 1

def test_need_creation():
    """Тест создания объекта Need"""
    need = Need()
    assert need.pain_points is None
    assert need.current_solution is None
    assert need.success_criteria is None
    assert need.priority is None

def test_need_with_data():
    """Тест создания Need с данными"""
    need = Need(
        pain_points=["Медленная работа системы"],
        current_solution="Excel таблицы",
        success_criteria=["Ускорение в 2 раза"],
        priority="high"
    )
    assert len(need.pain_points) == 1
    assert need.current_solution == "Excel таблицы"
    assert len(need.success_criteria) == 1
    assert need.priority == "high"

def test_timing_creation():
    """Тест создания объекта Timing"""
    timing = Timing()
    assert timing.timeframe is None
    assert timing.deadline is None
    assert timing.next_step is None

def test_timing_with_data():
    """Тест создания Timing с данными"""
    timing = Timing(
        timeframe="this_quarter",
        deadline=date(2024, 3, 31),
        next_step="Техническое задание"
    )
    assert timing.timeframe == "this_quarter"
    assert timing.deadline == date(2024, 3, 31)
    assert timing.next_step == "Техническое задание"

def test_bant_record_creation():
    """Тест создания BantRecord"""
    record = BantRecord(deal_id="DEAL-001")
    assert record.deal_id == "DEAL-001"
    assert record.filled == "none"
    assert isinstance(record.budget, Budget)
    assert isinstance(record.authority, Authority)
    assert isinstance(record.need, Need)
    assert isinstance(record.timing, Timing)

def test_session_state_creation():
    """Тест создания SessionState"""
    record = BantRecord(deal_id="DEAL-001")
    state = SessionState(
        session_id="session-123",
        deal_id="DEAL-001",
        record=record
    )
    assert state.session_id == "session-123"
    assert state.deal_id == "DEAL-001"
    assert state.current_slot is None
    assert state.required_slots == ["budget", "authority", "need", "timing"]
    assert len(state.history) == 0

def test_currency_validation():
    """Тест валидации валют"""
    budget = Budget(currency="USD")
    assert budget.currency == "USD"
    
    budget = Budget(currency="RUB")
    assert budget.currency == "RUB"
    
    # Неверная валюта должна вызвать ошибку
    with pytest.raises((ValueError, TypeError)):
        Budget(currency="INVALID")

def test_priority_validation():
    """Тест валидации приоритета"""
    need = Need(priority="high")
    assert need.priority == "high"
    
    need = Need(priority="critical")
    assert need.priority == "critical"
    
    # Неверный приоритет должен вызвать ошибку
    with pytest.raises((ValueError, TypeError)):
        Need(priority="invalid")

def test_timeframe_validation():
    """Тест валидации временных рамок"""
    timing = Timing(timeframe="this_month")
    assert timing.timeframe == "this_month"
    
    timing = Timing(timeframe="this_year")
    assert timing.timeframe == "this_year"
    
    # Неверная временная рамка должна вызвать ошибку
    with pytest.raises((ValueError, TypeError)):
        Timing(timeframe="invalid")

def test_slot_score_creation():
    """Тест создания SlotScore"""
    slot_score = SlotScore(value=75, confidence=0.8, rationale="Хорошо заполнено")
    assert slot_score.value == 75
    assert slot_score.confidence == 0.8
    assert slot_score.rationale == "Хорошо заполнено"

def test_slot_score_validation():
    """Тест валидации SlotScore"""
    # Корректные значения
    SlotScore(value=0, confidence=0.0)
    SlotScore(value=100, confidence=1.0)
    
    # Граничные значения
    with pytest.raises(ValueError):
        SlotScore(value=-1, confidence=0.5)  # value < 0
    
    with pytest.raises(ValueError):
        SlotScore(value=101, confidence=0.5)  # value > 100
    
    with pytest.raises(ValueError):
        SlotScore(value=50, confidence=-0.1)  # confidence < 0
    
    with pytest.raises(ValueError):
        SlotScore(value=50, confidence=1.1)  # confidence > 1

def test_bant_score_creation():
    """Тест создания BantScore"""
    budget_score = SlotScore(value=20, confidence=0.8)
    authority_score = SlotScore(value=18, confidence=0.7)
    need_score = SlotScore(value=25, confidence=0.9)
    timing_score = SlotScore(value=15, confidence=0.6)
    
    bant_score = BantScore(
        budget=budget_score,
        authority=authority_score,
        need=need_score,
        timing=timing_score,
        total=78,
        stage="qualified"
    )
    
    assert bant_score.total == 78
    assert bant_score.stage == "qualified"
    assert bant_score.budget.value == 20

def test_bant_score_stage_validation():
    """Тест валидации stage в BantScore"""
    budget_score = SlotScore(value=20, confidence=0.8)
    authority_score = SlotScore(value=18, confidence=0.7)
    need_score = SlotScore(value=25, confidence=0.9)
    timing_score = SlotScore(value=15, confidence=0.6)
    
    # Корректные stage
    BantScore(budget=budget_score, authority=authority_score, need=need_score, timing=timing_score, total=78, stage="unqualified")
    BantScore(budget=budget_score, authority=authority_score, need=need_score, timing=timing_score, total=78, stage="qualified")
    BantScore(budget=budget_score, authority=authority_score, need=need_score, timing=timing_score, total=78, stage="ready")
    
    # Неверный stage
    with pytest.raises(ValueError):
        BantScore(budget=budget_score, authority=authority_score, need=need_score, timing=timing_score, total=78, stage="invalid")

def test_bant_record_with_score():
    """Тест BantRecord с score"""
    record = BantRecord(deal_id="DEAL-001")
    assert record.score is None
    
    budget_score = SlotScore(value=20, confidence=0.8)
    authority_score = SlotScore(value=18, confidence=0.7)
    need_score = SlotScore(value=25, confidence=0.9)
    timing_score = SlotScore(value=15, confidence=0.6)
    
    score = BantScore(
        budget=budget_score,
        authority=authority_score,
        need=need_score,
        timing=timing_score,
        total=78,
        stage="qualified"
    )
    
    record.score = score
    assert record.score.total == 78
    assert record.score.stage == "qualified"
