# app/core/schema.py
from datetime import date, datetime, timezone
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, conlist, confloat, conint

Currency = Literal["RUB", "USD", "EUR", "CNY", "GBP"]

class Budget(BaseModel):
    have_budget: Optional[bool] = None
    amount_min: Optional[confloat(ge=0)] = None
    amount_max: Optional[confloat(ge=0)] = None
    currency: Optional[Currency] = "RUB"
    comment: Optional[str] = None

class Authority(BaseModel):
    decision_maker: Optional[str] = None
    stakeholders: Optional[List[str]] = None
    decision_process: Optional[str] = None
    risks: Optional[List[str]] = None

class Need(BaseModel):
    pain_points: Optional[conlist(str, min_length=1)] = None
    current_solution: Optional[str] = None
    success_criteria: Optional[List[str]] = None
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None

class Timing(BaseModel):
    timeframe: Optional[Literal["this_month", "this_quarter", "this_half", "this_year", "unknown"]] = None
    deadline: Optional[date] = None
    next_step: Optional[str] = None

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

class SessionState(BaseModel):
    session_id: str
    deal_id: str
    history: List[dict] = []
    required_slots: List[str] = ["budget", "authority", "need", "timing"]
    current_slot: Optional[str] = None
    record: BantRecord
