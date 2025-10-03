# app/core/llm.py
from __future__ import annotations
import os
import time
import uuid
from typing import List, Dict, Any, Optional

import requests


def _env_bool(name: str, default: bool = True) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "y", "on")


class GigaChatClient:
    """
    Мин. клиент GigaChat:
      - Получение и кэширование access_token через OAuth v2
      - Вызов /chat/completions
      - Ретрай при 401 (просроченный токен)
    Требуемые ENV:
      GIGACHAT_AUTH_KEY   — base64(client_id:client_secret) без префикса 'Basic'
      GIGACHAT_SCOPE      — напр. GIGACHAT_API_PERS
      GIGACHAT_VERIFY_SSL — true/false
      GIGACHAT_MODEL      — напр. GigaChat-Pro
    Необязательные ENV (дефолты даны):
      GIGACHAT_AUTH_URL   — https://ngw.devices.sberbank.ru:9443/api/v2/oauth
      GIGACHAT_API_URL    — https://gigachat.devices.sberbank.ru/api/v1
    """

    def __init__(
        self,
        model: Optional[str] = None,
        scope: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
        auth_url: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout_sec: int = 60,
    ) -> None:
        self.auth_key = os.getenv("GIGACHAT_AUTH_KEY")  # base64(client:secret)
        if not self.auth_key:
            raise RuntimeError("GIGACHAT_AUTH_KEY is required")

        self.model = model or os.getenv("GIGACHAT_MODEL", "GigaChat-Pro")
        self.scope = scope or os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
        self.verify_ssl = (_env_bool("GIGACHAT_VERIFY_SSL", True)
                           if verify_ssl is None else verify_ssl)

        self.auth_url = auth_url or os.getenv(
            "GIGACHAT_AUTH_URL",
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        )
        self.api_url = api_url or os.getenv(
            "GIGACHAT_API_URL",
            "https://gigachat.devices.sberbank.ru/api/v1",
        )
        self.timeout_sec = timeout_sec

        self._token: Optional[str] = None
        self._exp_ts: float = 0.0  # unix time (seconds)

    # ---------- OAuth ----------
    def _need_refresh(self) -> bool:
        return not self._token or time.time() >= (self._exp_ts - 30)

    def _fetch_token(self) -> str:
        headers = {
            "Authorization": f"Basic {self.auth_key}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "RqUID": str(uuid.uuid4()),
        }
        data = {"scope": self.scope}
        resp = requests.post(
            self.auth_url,
            headers=headers,
            data=data,
            timeout=20,
            verify=self.verify_ssl,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        # expires_in обычно в секундах, иначе держим безопасный дефолт
        expires_in = int(payload.get("expires_in", 1800))
        self._exp_ts = time.time() + expires_in
        return self._token

    def _ensure_token(self) -> str:
        if self._need_refresh():
            return self._fetch_token()
        return self._token  # type: ignore[return-value]

    # ---------- Chat Completions ----------
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        json_mode: bool = False,
        model: Optional[str] = None,
    ) -> str:
        """
        messages: [{"role":"system|user|assistant","content":"..."}]
        json_mode: если True — просит строгий JSON через response_format
        """
        token = self._ensure_token()
        url = f"{self.api_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # один прозрачный ретрай при 401
        for attempt in range(2):
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout_sec,
                verify=self.verify_ssl,
            )
            if resp.status_code == 401 and attempt == 0:
                token = self._fetch_token()
                headers["Authorization"] = f"Bearer {token}"
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

        raise RuntimeError("GigaChat chat failed after retry")
