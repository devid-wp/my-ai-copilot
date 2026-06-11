# core/router.py
"""Classifier to route prompts to chat or code models."""

def classify_prompt(prompt: str) -> str:
    """Classify the prompt as either 'code' (for development tasks) or 'chat' (for Q&A).
    
    Case-insensitive search is performed on keywords and their common Russian equivalents.
    """
    if not prompt:
        return "chat"
        
    p = prompt.lower()
    keywords = [
        "write", "create", "refactor", "fix", "edit", "implement", "generate", "add", "update", "delete", "debug",
        "напиши", "создай", "исправь", "измени", "сделай", "добавь", "удали", "отладь", "поправь", "сгенерируй", "выполни", "запусти"
    ]
    if any(kw in p for kw in keywords):
        return "code"
    return "chat"
