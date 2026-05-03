from __future__ import annotations

from tor_llm_tool.models import AssistantRequest
from tor_llm_tool.providers import LmStudioProvider, LlmProvider, OpenAICompatibleProvider
from tor_llm_tool.settings import AppConfig


class AssistantService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.provider = self._create_provider(config)

    def run(self, request: AssistantRequest) -> str:
        return self.provider.complete(request)

    def stream(self, request: AssistantRequest):
        yield from self.provider.complete_stream(request)

    def list_models(self) -> list[str]:
        return self.provider.list_models()

    def _create_provider(self, config: AppConfig) -> LlmProvider:
        if config.llm.provider == "lmstudio":
            return LmStudioProvider(config)
        return OpenAICompatibleProvider(config)
