# app/core/validator.py
import json
from pydantic import ValidationError
from app.core.schema import BantRecord
from app.core.prompts import SCHEMA_HINT

def build_parse_messages(answer_text: str):
    from datetime import datetime
    current_date = datetime.now().strftime('%d %B %Y')
    
    # Создаем промпт без форматирования
    prompt = f"""Проанализируй ответ менеджера и извлеки BANT-информацию. Верни ТОЛЬКО валидный JSON без дополнительного текста.

Контекст времени: {current_date}

Схема ответа:
{{
  "budget": {{
    "have_budget": true|false|null,
    "amount_min": 0|null,
    "amount_max": 0|null,
    "currency": "RUB"|"USD"|"EUR"|"CNY"|"GBP"|null,
    "comment": "string"|null,
    "budget_status": "NOT_ASKED"|"NO_BUDGET"|"AVAILABLE"|null
  }},
  "authority": {{
    "decision_maker": "string"|null,
    "stakeholders": ["string"]|null,
    "decision_process": "string"|null,
    "risks": ["string"]|null,
    "uncertain": true|false|null
  }},
  "need": {{
    "pain_points": ["string"]|null,
    "current_solution": "string"|null,
    "success_criteria": ["string"]|null,
    "priority": "low"|"medium"|"high"|"critical"|null
  }},
  "timing": {{
    "timeframe": "this_month"|"this_quarter"|"this_half"|"this_year"|"next_year"|"unknown"|null,
    "deadline": "YYYY-MM-DD"|null,
    "next_step": "string"|null
  }}
}}

Правила извлечения:

Budget:
- Если указан диапазон (например, "50-100 тысяч") → amount_min=50000, amount_max=100000
- Если одна сумма (например, "около 75 тысяч") → amount_min=amount_max=75000
- Фразы "есть бюджет" без суммы → have_budget=true, суммы null
- КРИТИЧЕСКИ ВАЖНО: Различай отсутствие информации и отсутствие бюджета:
  * "не знаю" / "не имею понятия" / "не спрашивал" / "не обсуждали" → have_budget=null, budget_status="NOT_ASKED"
  * "нет бюджета" / "не заложено" / "нет денег" / "бюджет не выделен" → have_budget=false, budget_status="NO_BUDGET"
  * "есть бюджет" / конкретные суммы → have_budget=true, budget_status="AVAILABLE"
- Конвертируй тысячи/миллионы в полные числа (50к → 50000)

Authority:
- Ищи ФИО, должности (CEO, директор, руководитель отдела)
- stakeholders — все упомянутые роли кроме главного ЛПР
- decision_process — описание этапов согласования, количества согласующих
- КРИТИЧЕСКИ ВАЖНО: Различай неопределенность и конкретную информацию:
  * "не знаю" / "не определились" / "не знаем" / "без понятия" / "не в курсе" → decision_maker="не знаем", uncertain=null
  * "вроде X" / "кажется X" / "может быть X" / "похоже на X" → decision_maker=X, uncertain=true (сохраняй конкретную информацию!)
  * "точно X" / "определенно X" / "X решает" → decision_maker=X, uncertain=false

Need:
- pain_points — конкретные проблемы, не общие фразы
- "Проблем нет" / "все хорошо" / "ничего не беспокоит" / "не знаем" / "не определились" / "без понятия" / "не в курсе" → pain_points=[]
- priority: critical (срочно, горит), high (важно, планируют), medium (рассматривают), low (интересуются)

Timing:
- this_month — в течение месяца
- this_quarter — до конца текущего квартала
- this_half — до конца полугодия
- this_year — до конца года
- next_year — следующий год
- unknown — неопределенные сроки / "не знаем" / "пока не планируем" / "не определились" / "без понятия" / "не в курсе"
- КРИТИЧЕСКИ ВАЖНО: 
  * deadline только для конкретных дат (например, "15 марта 2024"), НЕ для общих периодов
  * "до конца года" → timeframe="this_year", deadline=null
  * "в следующем квартале" → timeframe="next_quarter", deadline=null
  * "в течение месяца" → timeframe="this_month", deadline=null
  * НЕ записывай общие периоды как deadline!

Общие правила:
- Если информация отсутствует или неясна → null
- НЕ додумывай данные, используй только явную информацию
- Все строки на русском языке
- Числа без пробелов и форматирования
- КРИТИЧЕСКИ ВАЖНО: Отрицательные ответы ("не знаю", "нет", "не определились") - это ВАЛИДНЫЕ данные, НЕ игнорируй их!

Примеры:
Вход: "Бюджет примерно 500-700 тысяч рублей. Решает гендиректор Иванов, но нужно согласование с финансовым директором."
Выход: {{"budget": {{"have_budget": true, "amount_min": 500000, "amount_max": 700000, "currency": "RUB", "comment": null}}, "authority": {{"decision_maker": "Гендиректор Иванов", "stakeholders": ["Финансовый директор"], "decision_process": "Требуется согласование с финансовым директором", "risks": null}}, ...}}"""
    
    return [
        {"role": "system", "content": prompt},
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
