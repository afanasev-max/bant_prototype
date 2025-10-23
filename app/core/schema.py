# app/core/schema.py
from datetime import date, datetime, timezone
from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field, conlist, confloat, conint

Currency = Literal["RUB", "USD", "EUR", "CNY", "GBP"]
StatusLevel = Literal["CLEAR", "PARTIAL", "MISSING"]

class Budget(BaseModel):
    have_budget: Optional[bool] = None
    amount_min: Optional[confloat(ge=0)] = None
    amount_max: Optional[confloat(ge=0)] = None
    currency: Optional[Currency] = "RUB"
    comment: Optional[str] = None
    budget_status: Optional[Literal["NOT_ASKED", "NO_BUDGET", "AVAILABLE"]] = None

class Authority(BaseModel):
    decision_maker: Optional[str] = None
    stakeholders: Optional[List[str]] = None
    decision_process: Optional[str] = None
    risks: Optional[List[str]] = None
    comment: Optional[str] = None
    uncertain: Optional[bool] = None  # true если "вроде X", false если "точно X"

class Need(BaseModel):
    pain_points: Optional[List[str]] = None
    current_solution: Optional[str] = None
    success_criteria: Optional[List[str]] = None
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None
    comment: Optional[str] = None

class Timing(BaseModel):
    timeframe: Optional[Literal["this_month", "this_quarter", "this_half", "this_year", "next_year", "unknown"]] = None
    deadline: Optional[date] = None
    next_step: Optional[str] = None
    comment: Optional[str] = None
    display_timeframe: Optional[str] = None  # "Конец 2025 года (осталось ~2.5 мес)"

class SlotScore(BaseModel):
    value: conint(ge=0, le=100)
    confidence: confloat(ge=0.0, le=1.0)
    rationale: Optional[str] = None

class BantScore(BaseModel):
    budget: SlotScore
    authority: SlotScore
    need: SlotScore
    timing: SlotScore
    total: conint(ge=0, le=100)
    stage: Literal["unqualified", "qualified", "ready"]

class BantRecord(BaseModel):
    deal_id: str
    budget: Budget = Budget()
    authority: Authority = Authority()
    need: Need = Need()
    timing: Timing = Timing()
    filled: Literal["none", "partial", "full"] = "none"
    score: Optional[BantScore] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# CRM Data Schema
class CrmDeal(BaseModel):
    """Схема для данных сделки из CRM"""
    deal_id: Optional[Union[int, str]] = None
    deal_name: Optional[str] = None
    company_official: Optional[str] = None
    company_short: Optional[str] = None
    end_customer: Optional[str] = None
    expected_contract_date: Optional[str] = None
    responsible: Optional[str] = None
    competence_center: Optional[str] = None
    lead_source: Optional[str] = None
    deal_form: Optional[str] = None
    probability_type: Optional[str] = None
    stage: Optional[str] = None
    stage_date: Optional[str] = None
    deal_status: Optional[str] = None
    currency: Optional[str] = None
    stage_probability: Optional[str] = None
    expected_revenue_with_vat: Optional[float] = None
    expected_revenue_without_vat: Optional[float] = None
    estimated_margin_gm1: Optional[float] = None
    deal_type: Optional[str] = None
    legal_entity: Optional[str] = None
    direction: Optional[str] = None
    contract_end_date: Optional[str] = None
    renewal_order: Optional[str] = None
    product_amount_with_vat: Optional[float] = None
    key_deal: Optional[Union[bool, str]] = None
    vat_rate: Optional[str] = None
    war: Optional[str] = None
    business_unit: Optional[str] = None
    project_stage_code: Optional[str] = None
    customer_request_number: Optional[str] = None
    max_limit: Optional[float] = None
    partners: Optional[str] = None
    tender_request_type: Optional[str] = None
    tender_submission_date: Optional[str] = None
    loss_reason: Optional[str] = None
    closing_comment: Optional[str] = None
    closing_action: Optional[str] = None
    change_date: Optional[str] = None
    lead_id: Optional[Union[int, str]] = None

class SessionState(BaseModel):
    session_id: str
    deal_id: str
    history: List[dict] = []
    required_slots: List[str] = ["budget", "authority", "need", "timing"]
    current_slot: Optional[str] = None
    record: BantRecord
    slot_attempts: dict[str, int] = {}  # Счетчик попыток для каждого слота
    last_question: Optional[str] = None  # Последний заданный вопрос
    crm_data: Optional[CrmDeal] = None  # Данные из CRM
    crm_data_requires_confirmation: bool = False  # Требуется ли подтверждение данных из CRM
