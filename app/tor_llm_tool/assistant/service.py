from __future__ import annotations

from tor_llm_tool.models import AssistantRequest
from tor_llm_tool.providers import LmStudioProvider, LlmProvider
from tor_llm_tool.settings import AppConfig


class AssistantService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.provider = self._create_provider(config)

    def run(self, request: AssistantRequest) -> str:
        return self.provider.complete(request)

    def _create_provider(self, config: AppConfig) -> LlmProvider:
        # Other local OpenAI-compatible providers can reuse this adapter later.
        return LmStudioProvider(config)

