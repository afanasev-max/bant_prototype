# app/api/routers/sessions.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.bant_agent import BantAgentService

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Инициализация сервиса
svc = BantAgentService()

class StartReq(BaseModel):
    deal_id: str

class AnswerReq(BaseModel):
    text: str

@router.post("/start")
def start_session(req: StartReq):
    """Начать новую сессию опроса"""
    try:
        st = svc.start(req.deal_id)
        from app.core.prompts import QUESTIONS
        question_text = QUESTIONS.get(st.current_slot, f"Вопрос по {st.current_slot}") if st.current_slot else "Все поля заполнены!"
        return {
            "session_id": st.session_id,
            "deal_id": st.deal_id,
            "current_slot": st.current_slot,
            "question": f"Начнём с {st.current_slot.upper()}: {question_text}" if st.current_slot else "Все поля заполнены!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/answer")
def answer_question(session_id: str, req: AnswerReq):
    """Ответить на вопрос"""
    try:
        st, next_q, followups = svc.answer(session_id, req.text)
        return {
            "session_id": st.session_id,
            "current_slot": st.current_slot,
            "next_question": next_q,
            "record": st.record.model_dump(),
            "filled": st.record.filled,
            "score": st.record.score.model_dump() if st.record.score else None,
            "followups": followups
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/status")
def get_status(session_id: str):
    """Получить статус сессии"""
    try:
        st = svc.get_session(session_id)
        return {
            "session_id": st.session_id,
            "deal_id": st.deal_id,
            "current_slot": st.current_slot,
            "filled": st.record.filled,
            "required_slots": st.required_slots,
            "score": st.record.score.model_dump() if st.record.score else None
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
