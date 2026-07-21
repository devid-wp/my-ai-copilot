from core.router import classify_prompt, should_use_agent


def test_classify_code_english():
    assert classify_prompt("write a python function") == "code"
    assert classify_prompt("refactor main module") == "code"
    assert classify_prompt("generate tests") == "code"


def test_classify_code_russian():
    assert classify_prompt("напиши тесты") == "code"
    assert classify_prompt("создай директорию") == "code"
    assert classify_prompt("исправь ошибку в main.py") == "code"
    assert classify_prompt("добавь проверку путей") == "code"


def test_classify_chat():
    assert classify_prompt("what is the capital of France?") == "chat"
    assert classify_prompt("explain how list comprehension works") == "chat"


def test_classify_empty():
    assert classify_prompt("") == "chat"
    assert classify_prompt(None) == "chat"


def test_classify_case_insensitivity():
    assert classify_prompt("WRITE tests") == "code"
    assert classify_prompt("СОЗДАЙ файл") == "code"


def test_agent_mode_keeps_conversation_in_safe_chat():
    assert should_use_agent(True, "hello") is False
    assert should_use_agent(True, "объясни как работает Python") is False
    assert should_use_agent(True, "создай файл index.html") is True
    assert should_use_agent(False, "создай файл index.html") is False
