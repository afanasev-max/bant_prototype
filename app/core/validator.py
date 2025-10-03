# app/core/validator.py
import json
from pydantic import ValidationError
from app.core.schema import BantRecord
from app.core.prompts import SCHEMA_HINT

def build_parse_messages(answer_text: str):
    return [
        {"role": "system", "content": SCHEMA_HINT},
        {"role": "user", "content": answer_text.strip()}
    ]

def parse_bant_with_llm(llm, answer_text: str) -> dict:
    """Парсинг ответа через LLM с json_mode"""
    messages = build_parse_messages(answer_text)
    try:
        # Используем json_mode для строгого JSON
        response = llm.chat(messages, json_mode=True)
        return parse_bant_json_text(response)
    except Exception as e:
        # Fallback на обычный режим
        response = llm.chat(messages)
        return parse_bant_json_text(response)

def parse_bant_json_text(text: str) -> dict:
    # Вырезаем JSON-объект (на случай если модель добавила текст)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON found")
    return json.loads(text[start:end+1])

def validate_record(record: BantRecord) -> str:
    filled_slots = 0
    total_slots = 4
    
    for slot in ["budget", "authority", "need", "timing"]:
        slot_data = record.model_dump()[slot]
        # Проверяем, есть ли хотя бы одно непустое значение (исключаем updated_at)
        if any(v is not None and v != "" and v != [] for k, v in slot_data.items() if k != "updated_at"):
            filled_slots += 1
    
    if filled_slots == 0:
        return "none"
    elif filled_slots == total_slots:
        return "full"
    else:
        return "partial"

def refine_with_errors(messages, errors_text: str):
    messages = list(messages)
    messages.append({
        "role": "user", 
        "content": f"Исправь JSON строго под схему. Ошибки валидатора: {errors_text}. Верни только JSON."
    })
    return messages
