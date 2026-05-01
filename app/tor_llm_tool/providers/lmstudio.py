from __future__ import annotations

from typing import Any

import httpx

from tor_llm_tool.assistant.image import prepare_image_for_llm
from tor_llm_tool.assistant.prompts import SYSTEM_PROMPT, build_user_prompt
from tor_llm_tool.errors import AppError, ErrorCategory
from tor_llm_tool.models import AssistantRequest
from tor_llm_tool.providers.base import LlmProvider
from tor_llm_tool.settings import AppConfig


class LmStudioProvider(LlmProvider):
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def complete(self, request: AssistantRequest) -> str:
        model = self._select_model(request)
        payload = {
            "model": model,
            "messages": self._messages(request),
            "temperature": 0.2,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.config.llm.api_key:
            headers["Authorization"] = f"Bearer {self.config.llm.api_key}"

        url = self.config.llm.base_url.rstrip("/") + "/chat/completions"
        try:
            response = httpx.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.config.llm.timeout_sec,
            )
        except httpx.ConnectError as exc:
            raise AppError(
                code="LMSTUDIO_NOT_RUNNING",
                category=ErrorCategory.PROVIDER,
                message="LM Studio に接続できません。",
                detail=str(exc),
                retryable=True,
                user_action="LM Studio の Local Server を起動してから再試行してください。",
            ) from exc
        except httpx.TimeoutException as exc:
            raise AppError(
                code="REQUEST_TIMEOUT",
                category=ErrorCategory.NETWORK,
                message="応答がタイムアウトしました。",
                detail=str(exc),
                retryable=True,
                user_action="再送信するか、timeout を延長してください。",
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                code="LMSTUDIO_NOT_RUNNING",
                category=ErrorCategory.PROVIDER,
                message="LM Studio への接続でエラーが発生しました。",
                detail=str(exc),
                retryable=True,
            ) from exc

        if response.status_code in {401, 403}:
            raise AppError(
                code="API_KEY_INVALID",
                category=ErrorCategory.PROVIDER,
                message="API key が無効です。",
                detail=response.text[:300],
                retryable=False,
                user_action="LM Studio の API token を確認してください。",
            )
        if response.status_code == 404:
            raise AppError(
                code="MODEL_NOT_LOADED",
                category=ErrorCategory.MODEL,
                message="モデルがロードされていません。",
                detail=response.text[:300],
                retryable=True,
                user_action="LM Studio でモデルをロードしてください。",
            )
        if response.status_code >= 400:
            raise AppError(
                code="PROVIDER_BAD_RESPONSE",
                category=ErrorCategory.PROVIDER,
                message="LLM の応答を解釈できませんでした。",
                detail=response.text[:300],
                retryable=True,
            )

        try:
            data = response.json()
            return str(data["choices"][0]["message"]["content"]).strip()
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                code="PROVIDER_BAD_RESPONSE",
                category=ErrorCategory.PROVIDER,
                message="LLM の応答を解釈できませんでした。",
                detail=str(exc),
                retryable=True,
            ) from exc

    def _select_model(self, request: AssistantRequest) -> str:
        model = self.config.llm.model
        if request.send_image and request.image is not None and self.config.llm.vision_model:
            model = self.config.llm.vision_model
        if not model:
            raise AppError(
                code="MODEL_NOT_SET",
                category=ErrorCategory.SETTINGS,
                message="モデルが設定されていません。",
                retryable=False,
                user_action="設定画面で model を指定してください。",
            )
        return model

    def _messages(self, request: AssistantRequest) -> list[dict[str, Any]]:
        user_prompt = build_user_prompt(request)
        content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        if request.send_image and request.image is not None:
            mime, data = prepare_image_for_llm(
                request.image,
                self.config.capture.max_image_long_edge,
                self.config.capture.image_format,
                self.config.capture.jpeg_quality,
            )
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{data}"},
                }
            )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]

