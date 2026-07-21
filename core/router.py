"""Lightweight prompt routing between chat and code models."""

CODE_KEYWORDS = {
    "write",
    "create",
    "refactor",
    "fix",
    "edit",
    "implement",
    "generate",
    "add",
    "update",
    "delete",
    "debug",
    "test",
    "build",
    "run",
    "напиши",
    "создай",
    "исправь",
    "измени",
    "сделай",
    "добавь",
    "удали",
    "отладь",
    "поправь",
    "сгенерируй",
    "выполни",
    "запусти",
    "тест",
}


def classify_prompt(prompt: str | None) -> str:
    if not prompt:
        return "chat"
    lowered = prompt.casefold()
    return "code" if any(keyword in lowered for keyword in CODE_KEYWORDS) else "chat"


def should_use_agent(agent_enabled: bool, prompt: str | None) -> bool:
    """Use tools only for an explicit action request, even when agent mode is enabled."""
    return agent_enabled and classify_prompt(prompt) == "code"


__all__ = ["classify_prompt", "should_use_agent"]
