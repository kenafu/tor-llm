from __future__ import annotations

from abc import ABC, abstractmethod

from tor_llm_tool.models import AssistantRequest


class LlmProvider(ABC):
    @abstractmethod
    def complete(self, request: AssistantRequest) -> str:
        raise NotImplementedError

