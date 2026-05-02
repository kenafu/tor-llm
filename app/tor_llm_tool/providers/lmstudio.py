from __future__ import annotations

import json
from typing import Any

import httpx

from tor_llm_tool.assistant.image import prepare_image_for_llm
from tor_llm_tool.assistant.prompts import build_user_prompt
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

    def complete_stream(self, request: AssistantRequest):
        model = self._select_model(request)
        payload = {
            "model": model,
            "messages": self._messages(request),
            "temperature": 0.2,
            "stream": True,
        }
        headers = self._headers()
        url = self.config.llm.base_url.rstrip("/") + "/chat/completions"
        try:
            with httpx.stream(
                "POST",
                url,
                json=payload,
                headers=headers,
                timeout=self.config.llm.timeout_sec,
            ) as response:
                self._raise_for_response(response)
                for line in response.iter_lines():
                    delta = _extract_stream_delta(line)
                    if delta:
                        yield delta
        except AppError:
            raise
        except httpx.ConnectError as exc:
            raise self._connect_error(exc) from exc
        except httpx.TimeoutException as exc:
            raise self._timeout_error(exc) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                code="LMSTUDIO_NOT_RUNNING",
                category=ErrorCategory.PROVIDER,
                message="LM Studio への接続でエラーが発生しました。",
                detail=str(exc),
                retryable=True,
            ) from exc

    def list_models(self) -> list[str]:
        url = self.config.llm.base_url.rstrip("/") + "/models"
        try:
            response = httpx.get(url, headers=self._headers(), timeout=10)
        except httpx.ConnectError as exc:
            raise self._connect_error(exc) from exc
        except httpx.TimeoutException as exc:
            raise self._timeout_error(exc) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                code="LMSTUDIO_NOT_RUNNING",
                category=ErrorCategory.PROVIDER,
                message="LM Studio への接続でエラーが発生しました。",
                detail=str(exc),
                retryable=True,
            ) from exc

        self._raise_for_response(response)
        try:
            data = response.json()
            models = []
            for item in data.get("data", []):
                model_id = item.get("id")
                if model_id:
                    models.append(str(model_id))
            return models
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                code="PROVIDER_BAD_RESPONSE",
                category=ErrorCategory.PROVIDER,
                message="モデル一覧を解釈できませんでした。",
                detail=str(exc),
                retryable=True,
            ) from exc

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.llm.api_key:
            headers["Authorization"] = f"Bearer {self.config.llm.api_key}"
        return headers

    def _raise_for_response(self, response: httpx.Response) -> None:
        body = _safe_response_text(response)
        if response.status_code in {401, 403}:
            raise AppError(
                code="API_KEY_INVALID",
                category=ErrorCategory.PROVIDER,
                message="API key が無効です。",
                detail=body[:300],
                retryable=False,
                user_action="LM Studio の API token を確認してください。",
            )
        if response.status_code == 404:
            raise AppError(
                code="MODEL_NOT_LOADED",
                category=ErrorCategory.MODEL,
                message="モデルがロードされていません。",
                detail=body[:300],
                retryable=True,
                user_action="LM Studio でモデルをロードしてください。",
            )
        if response.status_code >= 400:
            raise AppError(
                code="PROVIDER_BAD_RESPONSE",
                category=ErrorCategory.PROVIDER,
                message="LLM の応答を解釈できませんでした。",
                detail=body[:300],
                retryable=True,
            )

    def _connect_error(self, exc: Exception) -> AppError:
        return AppError(
            code="LMSTUDIO_NOT_RUNNING",
            category=ErrorCategory.PROVIDER,
            message="LM Studio に接続できません。",
            detail=str(exc),
            retryable=True,
            user_action="LM Studio の Local Server を起動してから再試行してください。",
        )

    def _timeout_error(self, exc: Exception) -> AppError:
        return AppError(
            code="REQUEST_TIMEOUT",
            category=ErrorCategory.NETWORK,
            message="応答がタイムアウトしました。",
            detail=str(exc),
            retryable=True,
            user_action="再送信するか、timeout を延長してください。",
        )

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
        user_prompt = build_user_prompt(request, self.config.prompts)
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
            {"role": "system", "content": self.config.prompts.system},
            {"role": "user", "content": content},
        ]


def _extract_stream_delta(line: str) -> str:
    if not line:
        return ""
    if not line.startswith("data:"):
        return ""
    payload = line.removeprefix("data:").strip()
    if not payload or payload == "[DONE]":
        return ""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return ""
    choices = data.get("choices") or []
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    content = delta.get("content")
    if content:
        return str(content)
    message = choices[0].get("message") or {}
    content = message.get("content")
    return str(content) if content else ""


def _safe_response_text(response: httpx.Response) -> str:
    try:
        if not response.is_closed:
            response.read()
        return response.text
    except Exception:  # noqa: BLE001
        return ""
