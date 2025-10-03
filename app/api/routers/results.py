# app/api/routers/results.py
from fastapi import APIRouter, HTTPException
from app.services.bant_agent import BantAgentService

router = APIRouter(prefix="/results", tags=["results"])

# Инициализация сервиса
svc = BantAgentService()

@router.get("/{session_id}")
def get_result(session_id: str):
    """Получить результат опроса"""
    try:
        st = svc.get_session(session_id)
        return {
            "session_id": st.session_id,
            "deal_id": st.deal_id,
            "record": st.record.model_dump(),
            "filled": st.record.filled,
            "current_slot": st.current_slot
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/export")
def export_result(session_id: str):
    """Экспортировать результат в JSON"""
    try:
        st = svc.get_session(session_id)
        return {
            "session_id": st.session_id,
            "deal_id": st.deal_id,
            "export_data": st.record.model_dump(),
            "export_timestamp": st.record.updated_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
