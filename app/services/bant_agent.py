# app/services/bant_agent.py
import uuid
from app.core.schema import SessionState, BantRecord
from app.core.flow import BantFlow
from app.core.llm import GigaChatClient

class BantAgentService:
    def __init__(self):
        self.llm = GigaChatClient()
        self.flow = BantFlow(self.llm)
        self.sessions: dict[str, SessionState] = {}

    def start(self, deal_id: str) -> SessionState:
        sid = str(uuid.uuid4())
        state = SessionState(
            session_id=sid, 
            deal_id=deal_id, 
            record=BantRecord(deal_id=deal_id)
        )
        state.current_slot = self.flow.next_slot(state)
        self.sessions[sid] = state
        return state

    def answer(self, session_id: str, text: str) -> tuple[SessionState, str | None, list[str]]:
        if session_id not in self.sessions:
            raise ValueError("Session not found")
        
        st = self.sessions[session_id]
        st.history.append({"role": "user", "content": text})
        st, next_q, followups = self.flow.process_answer(st, text)
        return st, next_q, followups

    def get_session(self, session_id: str) -> SessionState:
        if session_id not in self.sessions:
            raise ValueError("Session not found")
        return self.sessions[session_id]
