__all__ = ["AssistantService"]


def __getattr__(name: str):
    if name == "AssistantService":
        from .service import AssistantService

        return AssistantService
    raise AttributeError(name)
