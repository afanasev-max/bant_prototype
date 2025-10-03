# tests/test_validator.py
import pytest
import json
from app.core.validator import (
    build_parse_messages, 
    parse_bant_json_text, 
    validate_record, 
    refine_with_errors
)
from app.core.schema import BantRecord, Budget, Authority, Need, Timing

def test_build_parse_messages():
    """Тест создания сообщений для парсинга"""
    answer_text = "У нас есть бюджет 100000 рублей"
    messages = build_parse_messages(answer_text)
    
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == answer_text.strip()

def test_parse_bant_json_text_valid():
    """Тест парсинга валидного JSON"""
    json_text = '{"budget": {"have_budget": true, "amount_min": 100000}}'
    result = parse_bant_json_text(json_text)
    
    assert result["budget"]["have_budget"] is True
    assert result["budget"]["amount_min"] == 100000

def test_parse_bant_json_text_with_extra_text():
    """Тест парсинга JSON с дополнительным текстом"""
    json_text = 'Вот JSON: {"budget": {"have_budget": true}} и еще текст'
    result = parse_bant_json_text(json_text)
    
    assert result["budget"]["have_budget"] is True

def test_parse_bant_json_text_no_json():
    """Тест парсинга текста без JSON"""
    with pytest.raises(ValueError, match="No JSON found"):
        parse_bant_json_text("Просто текст без JSON")

def test_parse_bant_json_text_invalid_json():
    """Тест парсинга невалидного JSON"""
    with pytest.raises(json.JSONDecodeError):
        parse_bant_json_text('{"budget": {"have_budget": true,}}')  # Лишняя запятая

def test_validate_record_none():
    """Тест валидации пустой записи"""
    record = BantRecord(deal_id="DEAL-001")
    # Создаем полностью пустую запись
    record.budget = Budget(currency=None)  # Убираем дефолтное значение
    result = validate_record(record)
    assert result == "none"

def test_validate_record_partial():
    """Тест валидации частично заполненной записи"""
    record = BantRecord(deal_id="DEAL-001")
    record.budget = Budget(have_budget=True, amount_min=100000)
    result = validate_record(record)
    assert result == "partial"

def test_validate_record_full():
    """Тест валидации полностью заполненной записи"""
    record = BantRecord(deal_id="DEAL-001")
    record.budget = Budget(have_budget=True, amount_min=100000, currency="RUB")
    record.authority = Authority(decision_maker="Иван Иванов")
    record.need = Need(pain_points=["Проблема"], priority="high")
    record.timing = Timing(timeframe="this_month")
    result = validate_record(record)
    assert result == "full"

def test_refine_with_errors():
    """Тест добавления сообщения об ошибке"""
    original_messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "User message"}
    ]
    errors_text = "Validation error: field required"
    
    refined_messages = refine_with_errors(original_messages, errors_text)
    
    assert len(refined_messages) == 3
    assert refined_messages[0] == original_messages[0]
    assert refined_messages[1] == original_messages[1]
    assert refined_messages[2]["role"] == "user"
    assert "Validation error: field required" in refined_messages[2]["content"]
    assert "Исправь JSON" in refined_messages[2]["content"]

def test_validate_record_mixed_filling():
    """Тест валидации записи со смешанным заполнением"""
    record = BantRecord(deal_id="DEAL-001")
    # Заполнены budget и authority, need и timing пустые
    record.budget = Budget(have_budget=True, amount_min=100000)
    record.authority = Authority(decision_maker="Иван Иванов")
    
    result = validate_record(record)
    assert result == "partial"

def test_validate_record_empty_but_not_none():
    """Тест валидации записи с пустыми строками"""
    record = BantRecord(deal_id="DEAL-001")
    record.budget = Budget(have_budget=True, amount_min=100000, comment="")
    record.authority = Authority(decision_maker="", stakeholders=[])
    
    result = validate_record(record)
    # Пустые строки и списки не считаются заполненными
    assert result == "partial"
