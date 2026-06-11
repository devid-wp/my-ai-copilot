"""tests/test_router.py — Unit tests for core/router.py"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.router import classify_prompt

def test_classify_code_english():
    assert classify_prompt("write a python function") == "code"
    assert classify_prompt("create a new file") == "code"
    assert classify_prompt("refactor main module") == "code"
    assert classify_prompt("fix bugs in executor") == "code"
    assert classify_prompt("implement a list") == "code"
    assert classify_prompt("generate tests") == "code"

def test_classify_code_russian():
    assert classify_prompt("напиши тесты") == "code"
    assert classify_prompt("создай директорию") == "code"
    assert classify_prompt("исправь ошибку в main.py") == "code"
    assert classify_prompt("добавь проверку путей") == "code"

def test_classify_chat():
    assert classify_prompt("what is the capital of France?") == "chat"
    assert classify_prompt("explain how list comprehension works") == "chat"
    assert classify_prompt("how does NVIDIAClient connect?") == "chat"
    assert classify_prompt("hello, who are you?") == "chat"

def test_classify_empty():
    assert classify_prompt("") == "chat"
    assert classify_prompt(None) == "chat"

def test_classify_case_insensitivity():
    assert classify_prompt("WRITE tests") == "code"
    assert classify_prompt("Fix error") == "code"
    assert classify_prompt("СОЗДАЙ файл") == "code"
