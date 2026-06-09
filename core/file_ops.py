# core/file_ops.py
"""
Парсер и исполнитель файловых операций.
Работает с любым путём на файловой системе.

Форматы:
  [CREATE_FILE: path]...[/CREATE_FILE]
  [CREATE_DIR: path]
  [EDIT_FILE: path] <<<<<<< SEARCH...=======...>>>>>>> REPLACE [/EDIT_FILE]
  [DELETE_FILE: path]
"""

import os
import re
import shutil


class FileOperation:
    """Одна файловая операция."""

    def __init__(self, action, path):
        self.action = action        # 'create', 'mkdir', 'edit', 'delete'
        self.path = path
        self.content = None          # для create — полное содержимое
        self.search_replace = []     # для edit — список (search, replace)


class OperationResult:
    """Результат выполнения операции."""

    def __init__(self, action, path, success, message=""):
        self.action = action
        self.path = path
        self.success = success
        self.message = message


# ── Разрешение пути ──────────────────────────────────────────

def _resolve_path(raw_path, project_root):
    """
    Принимает путь от модели (абсолютный или относительный).
    - Абсолютный путь  →  используется как есть
    - Относительный    →  разрешается относительно project_root
    Возвращает (display_path, full_path).
    full_path == None только если путь пустой или невалидный.
    """
    raw_path = raw_path.strip().strip('"').strip("'")

    # Нормализуем слэши под ОС
    raw_path = raw_path.replace('/', os.sep).replace('\\', os.sep)

    # Убираем ./ в начале
    if raw_path in ('.', ''):
        return None, None
    if raw_path.startswith('.' + os.sep):
        raw_path = raw_path[2:]

    if os.path.isabs(raw_path):
        full = os.path.normpath(raw_path)
        display = full
    else:
        full = os.path.normpath(os.path.join(project_root, raw_path))
        display = raw_path

    return display, full


# ── Парсер ───────────────────────────────────────────────────

def parse_operations(text):
    """
    Парсит ответ модели и извлекает файловые операции.
    Возвращает список FileOperation.
    """
    operations = []

    # 1) CREATE_FILE
    for m in re.finditer(
        r'\[CREATE_FILE:\s*(.+?)\]\s*\n(.*?)\[/CREATE_FILE\]',
        text, re.DOTALL
    ):
        op = FileOperation('create', m.group(1).strip())
        content = m.group(2)
        if content.startswith('\n'):
            content = content[1:]
        if content.endswith('\n'):
            content = content[:-1]
        op.content = content
        operations.append(op)

    # 2) CREATE_DIR (одна строка)
    for m in re.finditer(
        r'^\[CREATE_DIR:\s*(.+?)\]\s*$',
        text, re.MULTILINE
    ):
        operations.append(FileOperation('mkdir', m.group(1).strip()))

    # 3) EDIT_FILE с SEARCH/REPLACE парами внутри
    for m in re.finditer(
        r'\[EDIT_FILE:\s*(.+?)\]\s*\n(.*?)\[/EDIT_FILE\]',
        text, re.DOTALL
    ):
        op = FileOperation('edit', m.group(1).strip())
        block = m.group(2)

        for sr in re.finditer(
            r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE',
            block, re.DOTALL
        ):
            op.search_replace.append((sr.group(1), sr.group(2)))

        if op.search_replace:
            operations.append(op)

    # 4) DELETE_FILE (одна строка)
    for m in re.finditer(
        r'^\[DELETE_FILE:\s*(.+?)\]\s*$',
        text, re.MULTILINE
    ):
        operations.append(FileOperation('delete', m.group(1).strip()))

    return operations


# ── Исполнитель ──────────────────────────────────────────────

def execute_operations(operations, project_root):
    """
    Выполняет файловые операции на диске.
    Возвращает список OperationResult.
    """
    results = []
    project_root = os.path.normpath(os.path.abspath(project_root))

    for op in operations:
        try:
            display, full_path = _resolve_path(op.path, project_root)

            if full_path is None:
                results.append(OperationResult(
                    op.action, op.path, False, "Empty or invalid path"
                ))
                continue

            # Используем display path в результатах (короче для относительных)
            op.path = display

            if op.action == 'create':
                _do_create(full_path, op, results)
            elif op.action == 'mkdir':
                _do_mkdir(full_path, op, results)
            elif op.action == 'edit':
                _do_edit(full_path, op, results)
            elif op.action == 'delete':
                _do_delete(full_path, op, results)

        except Exception as e:
            results.append(OperationResult(op.action, op.path, False, str(e)))

    return results


def _do_create(full_path, op, results):
    """Создать (или перезаписать) файл."""
    dir_path = os.path.dirname(full_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    with open(full_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(op.content)

    results.append(OperationResult('create', op.path, True))


def _do_mkdir(full_path, op, results):
    """Создать папку (и все промежуточные)."""
    os.makedirs(full_path, exist_ok=True)
    results.append(OperationResult('mkdir', op.path, True))


def _do_edit(full_path, op, results):
    """Редактировать файл через SEARCH/REPLACE."""
    if not os.path.exists(full_path):
        results.append(OperationResult('edit', op.path, False, "File not found"))
        return

    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    original = content
    failed = []

    for i, (search, replace) in enumerate(op.search_replace):
        applied = False

        # 1) Точное совпадение
        if search in content:
            content = content.replace(search, replace, 1)
            applied = True

        # 2) Нормализация переносов строк (\r\n -> \n)
        if not applied:
            s_norm = search.replace('\r\n', '\n')
            c_norm = content.replace('\r\n', '\n')
            if s_norm in c_norm:
                content = c_norm.replace(s_norm, replace.replace('\r\n', '\n'), 1)
                applied = True

        # 3) Сравнение с обрезкой trailing whitespace на каждой строке
        if not applied:
            s_stripped = '\n'.join(l.rstrip() for l in search.splitlines())
            c_stripped = '\n'.join(l.rstrip() for l in content.splitlines())
            if s_stripped in c_stripped:
                idx = c_stripped.index(s_stripped)
                start_line = c_stripped[:idx].count('\n')
                num_lines = s_stripped.count('\n') + 1

                lines = content.splitlines(keepends=True)
                repl_lines = replace.splitlines(keepends=True)
                if repl_lines and not repl_lines[-1].endswith('\n'):
                    repl_lines[-1] += '\n'

                content = ''.join(
                    lines[:start_line] + repl_lines + lines[start_line + num_lines:]
                )
                applied = True

        if not applied:
            failed.append(i + 1)

    if content != original:
        with open(full_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)

        if failed:
            results.append(OperationResult(
                'edit', op.path, True,
                f"Partial: blocks {failed} not found"
            ))
        else:
            results.append(OperationResult('edit', op.path, True))
    else:
        results.append(OperationResult(
            'edit', op.path, False,
            "Search blocks not found in file"
        ))


def _do_delete(full_path, op, results):
    """Удалить файл или папку."""
    if os.path.isdir(full_path):
        shutil.rmtree(full_path)
        results.append(OperationResult('delete', op.path, True))
    elif os.path.exists(full_path):
        os.remove(full_path)
        results.append(OperationResult('delete', op.path, True))
    else:
        results.append(OperationResult('delete', op.path, False, "Not found"))
