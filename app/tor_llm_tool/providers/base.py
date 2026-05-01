from __future__ import annotations

from abc import ABC, abstractmethod

from tor_llm_tool.models import AssistantRequest


class LlmProvider(ABC):
    @abstractmethod
    def complete(self, request: AssistantRequest) -> str:
        raise NotImplementedError

    def complete_stream(self, request: AssistantRequest):
        yield self.complete(request)

    def list_models(self) -> list[str]:
        return []
