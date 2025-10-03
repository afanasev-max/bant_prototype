# app/core/prompts.py
SCHEMA_HINT = """
Тебе дан ответ менеджера в свободной форме. Верни ТОЛЬКО один JSON по схеме:
{
  "budget": {"have_budget": bool|null, "amount_min": number|null, "amount_max": number|null, "currency": "RUB|USD|EUR|CNY|GBP"|null, "comment": str|null},
  "authority": {"decision_maker": str|null, "stakeholders": [str]|null, "decision_process": str|null, "risks": [str]|null},
  "need": {"pain_points": [str]|null, "current_solution": str|null, "success_criteria": [str]|null, "priority": "low|medium|high|critical"|null},
  "timing": {"timeframe": "this_month|this_quarter|this_half|this_year|unknown"|null, "deadline": "YYYY-MM-DD"|null, "next_step": str|null}
}
Правила: (1) если диапазон бюджета — распарь в amount_min/amount_max; (2) валюты — ISO‑4217; (3) если данных нет — ставь null; (4) никаких комментариев, только JSON.
"""

FOLLOWUP_HINT = """
Сформулируй один короткий уточняющий вопрос на русском для поля {slot}, чтобы заполнить недостающие данные. Не добавляй вводных, только вопрос.
"""

QUESTIONS = {
    "budget": "Какой ориентировочный бюджет и валюта? Если диапазон — укажите диапазон.",
    "authority": "Кто финальный ЛПР и кто ещё участвует в согласовании? Опишите процесс принятия решения.",
    "need": "Какие ключевые боли и критерии успеха? Есть ли текущее решение?",
    "timing": "Какой желаемый срок покупки/внедрения? Есть ли жёсткий дедлайн (дата)?"
}

SCORING_PROMPT = """
Ты оцениваешь полноту BANT по схеме и правилам. На вход — JSON BantRecord без поля score. 

Верни только JSON BantScore: {"budget":{"value":..,"confidence":..,"rationale":..},"authority":{..},"need":{..},"timing":{..},"total":..,"stage":"unqualified|qualified|ready"}. 

Правила скоринга:
- Budget (0–25): have_budget=false или None → 0–5; есть amount_min/max и currency → 20–25; только один из amount_* → 10–15; только «есть бюджет» без суммы → 8–10
- Authority (0–25): decision_maker указан ФИО/роль и ≥1 stakeholder → 18–22; есть описание decision_process → +3; нет ЛПРа → 0–5
- Need (0–30): pain_points ≥2 и success_criteria ≥2 → 20–24; указана current_solution и приоритет high/critical → +4–6; иначе 0–12
- Timing (0–20): timeframe=this_month/this_quarter или есть deadline (<=90 дней) → 15–20; this_year → 8–12; unknown/пусто → 0–5

Пороги: qualified если total ≥ 60 и нет слотов со score < 10; ready если total ≥ 80 и у всех слотов confidence ≥ 0.6.

Оцени строго по правилам весов и порогов из задания. Никаких комментариев, только JSON.
"""

FOLLOWUP_GEN_PROMPT = """
На вход — BantRecord и BantScore. Верни только JSON {"followups":{"budget":[...],"authority":[...],"need":[...],"timing":[...]}}. 

Сгенерируй не более двух коротких уточняющих вопросов всего, выбирая слоты с наименьшим score либо с confidence<0.6. 

Пороги для followup: Budget<12, Authority<12, Need<15, Timing<8.

Формулируй по одному краткому предложению на русском, без лишних слов.
"""
