# app/services/storage.py
import json
import os
from typing import Dict, Any
from app.core.schema import SessionState

class JSONStorage:
    def __init__(self, file_path: str = "data/sessions.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
    def save_session(self, session: SessionState) -> None:
        """Сохранить сессию в JSON файл"""
        sessions = self.load_all_sessions()
        sessions[session.session_id] = session.model_dump()
        
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2, default=str)
    
    def load_session(self, session_id: str) -> Dict[str, Any] | None:
        """Загрузить сессию по ID"""
        sessions = self.load_all_sessions()
        return sessions.get(session_id)
    
    def load_all_sessions(self) -> Dict[str, Any]:
        """Загрузить все сессии"""
        if not os.path.exists(self.file_path):
            return {}
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def delete_session(self, session_id: str) -> bool:
        """Удалить сессию"""
        sessions = self.load_all_sessions()
        if session_id in sessions:
            del sessions[session_id]
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2, default=str)
            return True
        return False
