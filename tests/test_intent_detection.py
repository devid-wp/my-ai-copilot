from core.router import PromptIntent, detect_intent


def test_intent_distinguishes_action_explanation_and_inspection():
    assert detect_intent("создай файл index.html") is PromptIntent.ACTION
    assert detect_intent("расскажи, как создать файл") is PromptIntent.CHAT
    assert detect_intent("проверь проект") is PromptIntent.READ_ONLY
    assert detect_intent("что делает этот код?") is PromptIntent.READ_ONLY
    assert detect_intent("tell me how to create a file") is PromptIntent.CHAT
    assert detect_intent("review the project") is PromptIntent.READ_ONLY
