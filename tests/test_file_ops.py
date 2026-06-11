"""tests/test_file_ops.py — Unit tests for core/file_ops.py and its safety controls"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.file_ops import parse_operations, execute_operations, FileOperation

@pytest.fixture
def tmp_project(tmp_path):
    """Creates a temporary project directory for isolation."""
    return str(tmp_path)

def test_parse_create_file():
    text = "[CREATE_FILE: hello.py]\nprint('hello')\n[/CREATE_FILE]"
    ops = parse_operations(text)
    assert len(ops) == 1
    assert ops[0].action == 'create'
    assert ops[0].path == 'hello.py'
    assert ops[0].content == "print('hello')"

def test_execute_create_file_safe(tmp_project):
    op = FileOperation('create', 'safe.py')
    op.content = "x = 42"
    results = execute_operations([op], tmp_project)
    assert len(results) == 1
    assert results[0].success is True
    assert os.path.exists(os.path.join(tmp_project, 'safe.py'))

def test_execute_create_file_traversal_blocked(tmp_project):
    op = FileOperation('create', '../unsafe.py')
    op.content = "x = 42"
    results = execute_operations([op], tmp_project)
    assert len(results) == 1
    assert results[0].success is False
    assert "запрещен" in results[0].message
    assert not os.path.exists(os.path.join(tmp_project, '..', 'unsafe.py'))

def test_execute_cmd_allowed(tmp_project):
    op = FileOperation('execute', 'echo test_cmd')
    results = execute_operations([op], tmp_project)
    assert len(results) == 1
    assert results[0].success is True
    assert "test_cmd" in results[0].message

def test_execute_cmd_blocked(tmp_project):
    op = FileOperation('execute', 'rm -rf /')
    results = execute_operations([op], tmp_project)
    assert len(results) == 1
    assert results[0].success is False
    assert "не разрешена" in results[0].message
