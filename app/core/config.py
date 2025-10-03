# app/core/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # GigaChat API Configuration
    gigachat_auth_key: str = ""  # base64(client_id:client_secret)
    gigachat_model: str = "GigaChat-Pro"
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_verify_ssl: bool = False
    gigachat_auth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_api_url: str = "https://gigachat.devices.sberbank.ru/api/v1"
    
    # API Configuration
    api_base: str = "http://localhost:8000"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Storage Configuration
    storage_type: str = "json"
    storage_path: str = "data/sessions.json"
    
    # LLM Configuration
    llm_temperature: float = 0.2
    llm_timeout: int = 60
    llm_max_retries: int = 3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Глобальный экземпляр настроек
settings = Settings()
