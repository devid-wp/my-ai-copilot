"""Citadex CLI entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from dotenv import load_dotenv

from core.agent_executor import create_tool_registry, tool_result_payload
from core.agent_loop import (
    AgentLoopGuard,
    pseudo_tool_name,
    recovery_advice,
    require_read_before_edit,
    tool_path_key,
    unresolved_tool_failures,
)
from core.console import Console
from core.context_manager import get_git_log, get_project_context, get_project_instructions
from core.credential_probe import probe_provider_key, validate_provider_model_access
from core.credentials import (
    PROVIDER_API_KEYS,
    credential_status,
    delete_api_key,
    load_credentials,
    save_api_key,
    validate_api_key,
)
from core.diagnostics import SessionDiagnostics
from core.doctor import collect_doctor_checks
from core.local_runtime import LOCAL_MODEL_ID, local_server_online
from core.memory import AgentMemory
from core.preferences import UserPreferences, load_preferences, save_preferences
from core.prompts import SYSTEM_PROMPT_TEMPLATE
from core.provider_runtime import explain_provider_error, provider_name
from core.rate_limits import rate_limit_monitor
from core.tool_compatibility import ToolCompatibility, probe_cloud_tool_support
from core.tool_protocol import normalize_tool_call
from core.tools import AgentLimits, ToolResult, ToolStatus
from core.undo import undo_last_action
from core.verification import verify_agent_changes
from core.version import get_version

PROVIDER_MODELS = {
    "nvidia": ["meta/llama-3.1-8b-instruct"],
    "openai": ["gpt-5.6"],
    "ollama": ["llama3.2", "qwen2.5-coder"],
    "local": [LOCAL_MODEL_ID],
}

CHAT_SYSTEM_PROMPT = (
    "Ты — Citadex, помощник по программированию. Отвечай на языке пользователя кратко и по делу. "
    "Не утверждай, что изменил файлы или выполнил команды: в chat-режиме инструменты недоступны."
)


@dataclass
class SessionSettings:
    provider: str = "nvidia"
    model: str | None = None
    agent: bool = False
    auto_approve: bool = False
    tool_compatibility: str = "unknown"
    project_root: str = ""
    local_only: bool = False

    @property
    def mode(self) -> str:
        return "agent" if self.agent else "chat"

    @property
    def permissions(self) -> str:
        return "auto" if self.auto_approve else "ask"

    @property
    def display_model(self) -> str:
        return self.model or PROVIDER_MODELS[self.provider][0]


load_credentials()
load_dotenv()

if sys.platform == "win32":
    # Python launched from MSYS or an older console may inherit a legacy code page.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def build_system_prompt(project_root: str, username: str, memory: AgentMemory) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        project_root=project_root,
        project_instructions=get_project_instructions(project_root),
        project_tree=get_project_context(project_root),
        team_activity=memory.get_summary() or "— нет данных —",
        git_log=get_git_log(project_root) or "— git log недоступен —",
    )


def build_client_system_prompt(
    project_root: str,
    username: str,
    memory: AgentMemory,
    *,
    agent: bool,
) -> str:
    """Avoid building and sending agent context for ordinary chat requests."""
    if not agent:
        return CHAT_SYSTEM_PROMPT
    return build_system_prompt(project_root, username, memory)


def env(name: str, default: str) -> str:
    return os.getenv(name) or default


def provider_models(provider: str) -> list[str]:
    """Return models managed by a local runtime."""
    if provider == "local":
        if not local_server_online():
            raise RuntimeError("Встроенная локальная модель не запущена.")
        return [LOCAL_MODEL_ID]
    if provider != "ollama":
        raise ValueError(f"Для {provider.upper()} имя модели вводится вручную.")

    from core.ollama_client import OllamaClient

    models = OllamaClient(
        "",
        base_url=env("OLLAMA_BASE_URL", "http://localhost:11434"),
    ).list_models()
    if not models:
        raise RuntimeError("Ollama не вернул ни одной установленной модели.")
    return models


def validate_provider_model(provider: str, model: str) -> list[str]:
    """Reject model IDs that are unavailable through the active provider."""
    if provider in PROVIDER_API_KEYS:
        if not model.strip():
            raise ValueError("Имя модели не может быть пустым.")
        return [model.strip()]
    models = provider_models(provider)
    if model not in models:
        raise ValueError(
            f"Модель '{model}' недоступна для провайдера {provider.upper()}. "
            "Используйте /model без аргумента, чтобы увидеть доступные модели."
        )
    return models


def choose_model(provider: str, console: Console, preferred: str | None = None) -> str:
    """Read cloud model IDs directly; show menus only for locally discoverable models."""
    if provider in PROVIDER_API_KEYS:
        suffix = f" (Enter = {preferred})" if preferred else ""
        model = console.input(f"Имя модели{suffix}").strip() or (preferred or "")
        validate_provider_model(provider, model)
        if provider == "nvidia":
            validate_provider_model_access(provider, model, os.getenv("NVIDIA_API_KEY", ""))
        return model
    models = provider_models(provider)
    return console.choose(
        "Модель",
        models,
        default=preferred if preferred in models else models[0],
    )


def verify_tool_compatibility(settings: SessionSettings, console: Console) -> bool:
    model = settings.display_model
    console.activity(f"Проверка native tools: {model}")
    try:
        if settings.provider == "local":
            from core.local_client import LocalClient

            compatibility = LocalClient("", model=model).check_tool_support(model)
        elif settings.provider == "ollama":
            from core.ollama_client import OllamaClient

            client = OllamaClient(
                "",
                model_chat=model,
                model_code=model,
                base_url=env("OLLAMA_BASE_URL", "http://localhost:11434"),
            )
            compatibility = client.check_tool_support(model)
        else:
            environment_name = PROVIDER_API_KEYS[settings.provider]
            compatibility = probe_cloud_tool_support(
                settings.provider,
                model,
                os.getenv(environment_name, ""),
            )
    except Exception as exc:
        settings.tool_compatibility = "unavailable"
        console.error(explain_provider_error(exc, settings.provider.upper()))
        return False
    settings.tool_compatibility = compatibility.value
    if compatibility is ToolCompatibility.SUPPORTED:
        console.success(f"Native tools поддерживаются: {model}")
        return True
    console.error(
        f"Модель {model} печатает псевдовызовы вместо native tools. Выберите другую модель для agent-режима."
    )
    return False


def configure_provider_key(
    provider: str,
    console: Console,
    *,
    allow_replacement: bool,
) -> bool:
    environment_name = PROVIDER_API_KEYS.get(provider)
    if environment_name is None:
        return True
    saved_key = os.getenv(environment_name, "").strip()
    if saved_key and not allow_replacement:
        return True

    label = f"{provider.upper()} API key"
    if saved_key:
        label += " (Enter = оставить сохранённый)"
    entered_key = console.secret(label).strip()
    if not entered_key and not saved_key:
        console.error("API-ключ не введён.")
        return False
    api_key = entered_key or saved_key
    try:
        validate_api_key(provider, api_key)
        if entered_key:
            save_api_key(provider, api_key)
    except ValueError as exc:
        console.error(str(exc))
        return False
    except OSError as exc:
        console.error(f"Не удалось сохранить API-ключ: {exc}")
        return False
    if entered_key:
        console.success("API-ключ сохранён. Повторно вводить его не потребуется.")
    return True


def run_startup_setup(
    settings: SessionSettings,
    console: Console,
    preferences: UserPreferences,
) -> bool:
    """Guide an interactive user through the minimum startup choices."""
    mode = console.choose(
        "Режим запуска",
        ["agent", "chat"],
        default=preferences.mode,
    )
    if mode == "agent":
        permission_labels = {
            "Спрашивать перед действиями": "ask",
            "Автоподтверждение (полный доступ к рабочей папке)": "auto",
        }
        default_permission = next(
            label
            for label, permission in permission_labels.items()
            if permission == ("auto" if settings.auto_approve else preferences.permissions)
        )
        permission_label = console.choose(
            "Разрешения агента",
            list(permission_labels),
            default=default_permission,
        )
        settings.auto_approve = permission_labels[permission_label] == "auto"
        preferences.permissions = settings.permissions
    else:
        settings.auto_approve = False
    provider = console.choose(
        "Провайдер",
        list(PROVIDER_MODELS),
        default=settings.provider,
    )
    if not configure_provider_key(provider, console, allow_replacement=False):
        return False

    preferred_model = settings.model or preferences.models.get(provider)
    while True:
        try:
            model = choose_model(provider, console, preferred_model)
        except (RuntimeError, ValueError) as exc:
            console.error(str(exc))
            return False
        settings.provider = provider
        settings.model = model
        settings.agent = mode == "agent"
        settings.tool_compatibility = "unknown"
        if not settings.agent or verify_tool_compatibility(settings, console):
            break
        preferred_model = None
        console.warning("Введите другую модель для agent-режима.")

    preferences.provider = settings.provider
    preferences.mode = settings.mode
    preferences.models[settings.provider] = settings.display_model
    try:
        save_preferences(preferences)
    except OSError as exc:
        console.warning(f"Не удалось сохранить настройки запуска: {exc}")
    return True


def choose_recent_project(console: Console, preferences: UserPreferences, current: str) -> str:
    """Offer existing recent directories and fall back to a typed path."""
    recent = [
        current,
        *(path for path in preferences.recent_projects if path != current and Path(path).is_dir()),
    ]
    labels = [f"{Path(path).name} — {path}" for path in recent[:3]]
    other = "Выбрать другую папку"
    selected = console.choose("Рабочая папка", [*labels, other], default=labels[0])
    candidate = console.input("Путь к папке").strip() if selected == other else recent[labels.index(selected)]
    target = Path(candidate).expanduser().resolve()
    if not target.is_dir():
        console.error(f"Папка не найдена: {target}")
        return current
    return str(target)


def session_diagnostics(
    settings: SessionSettings,
    session: AgentMemory,
    client: Any | None,
) -> SessionDiagnostics:
    session.reload()
    provider_state = "configured"
    model_state = "selected"
    tools_state = settings.tool_compatibility
    ollama_state = "unknown"

    if settings.provider == "local":
        provider_state = "online" if local_server_online() else "offline"
        model_state = "available" if provider_state == "online" else "unavailable"
        tools_state = (
            "not checked" if settings.tool_compatibility == "unknown" else settings.tool_compatibility
        )
    elif settings.provider == "ollama":
        try:
            models = provider_models("ollama")
        except RuntimeError:
            provider_state = "offline"
            model_state = "unavailable"
        else:
            provider_state = "online"
            ollama_state = "online"
            model_state = "available" if settings.display_model in models else "missing"
        tools_state = (
            "not checked" if settings.tool_compatibility == "unknown" else settings.tool_compatibility
        )
    else:
        environment_name = PROVIDER_API_KEYS[settings.provider]
        if not os.getenv(environment_name):
            provider_state = "missing key"
        tools_state = "supported"
        try:
            provider_models("ollama")
        except RuntimeError:
            ollama_state = "offline"
        else:
            ollama_state = "online"

    project_root = settings.project_root
    if not project_root:
        session_path = Path(session.session_path).resolve()
        project_root = str(session_path.parent.parent)
    return SessionDiagnostics(
        provider=settings.provider,
        provider_state=provider_state,
        model=settings.display_model,
        model_state=model_state,
        tools_state=tools_state,
        mode=settings.mode,
        permissions=settings.permissions,
        project_root=project_root,
        message_count=len(session.get_history()),
        client_state="initialized" if client is not None else "not started",
        ollama_state=ollama_state if settings.provider != "ollama" else provider_state,
    )


def parse_slash(text: str) -> tuple[str, str] | None:
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None
    command, _, value = stripped[1:].partition(" ")
    return command.casefold(), value.strip()


def handle_slash(
    parsed: tuple[str, str],
    settings: SessionSettings,
    console: Console,
    session: AgentMemory,
    client: Any | None,
) -> tuple[Any | None, bool]:
    command, value = parsed
    if settings.local_only and command in {"keys", "provider", "model"}:
        console.error(f"/{command} недоступна в полностью локальной версии Citadex.")
        return client, False
    if command in {"exit", "quit"}:
        return client, True
    if command == "help":
        console.help()
        return client, False
    if command == "status":
        console.status(session_diagnostics(settings, session, client))
        return client, False
    if command == "doctor":
        if settings.provider in PROVIDER_API_KEYS:
            available_models = [settings.display_model]
        else:
            try:
                available_models = provider_models(settings.provider)
            except Exception as exc:
                available_models = None
                console.warning(f"Каталог моделей недоступен: {exc}")
        try:
            ollama_online = bool(provider_models("ollama"))
        except Exception:
            ollama_online = False
        checks = collect_doctor_checks(
            settings.project_root,
            settings.provider,
            settings.display_model,
            available_models,
            ollama_online=ollama_online,
        )
        for check in checks:
            message = f"{check.name}: {check.detail}"
            (console.success if check.ok else console.warning)(message)
        passed = sum(check.ok for check in checks)
        console.activity(f"Doctor: {passed}/{len(checks)} проверок пройдено")
        return client, False
    if command == "keys":
        statuses = credential_status()
        summary = ", ".join(
            f"{name}: {'настроен' if ready else 'не настроен'}" for name, ready in statuses.items()
        )
        console.activity(f"API-ключи: {summary}")
        provider = console.choose("Провайдер ключа", list(PROVIDER_API_KEYS))
        console.activity(f"Лимиты {provider}: {rate_limit_monitor.describe(provider)}")
        action = console.choose("Действие", ["Проверить", "Заменить", "Удалить", "Отмена"])
        if action == "Заменить":
            if configure_provider_key(provider, console, allow_replacement=True):
                rate_limit_monitor.clear(provider)
                if provider == settings.provider:
                    client = None
        elif action == "Удалить":
            delete_api_key(provider)
            rate_limit_monitor.clear(provider)
            if provider == settings.provider:
                client = None
            console.success(f"Ключ {provider.upper()} удалён")
        elif action == "Проверить":
            if not rate_limit_monitor.can_check(provider):
                console.warning(
                    "Лимиты API обновляются раз в минуту. "
                    f"Следующая проверка через {rate_limit_monitor.seconds_until_refresh(provider)} сек."
                )
                return client, False
            try:
                environment_name = PROVIDER_API_KEYS[provider]
                console.activity(f"Проверка ключа {provider.upper()}…")
                started = perf_counter()
                probe_provider_key(provider, os.getenv(environment_name, ""))
            except Exception as exc:
                snapshot = rate_limit_monitor.record_error(provider, exc)
                if snapshot.limited:
                    console.warning(
                        "Лимит запросов исчерпан. Состояние автоматически станет доступно "
                        "для новой проверки через 60 секунд."
                    )
                else:
                    console.error(
                        "Проверка ключа не пройдена: "
                        + explain_provider_error(exc, provider.upper())
                    )
            else:
                rate_limit_monitor.record_success(provider)
                console.success(
                    f"Ключ {provider.upper()} работает · проверено за "
                    f"{perf_counter() - started:.1f} с"
                )
        return client, False
    if command == "undo":
        try:
            result = undo_last_action(settings.project_root)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            console.error(str(exc))
        else:
            console.success(f"Последнее изменение отменено: {result['path']}")
        return client, False
    if command == "clear":
        session.clear()
        if client is not None:
            client.reset_history()
        console.success("История очищена")
        return client, False
    if command == "project":
        if not value:
            console.error("Укажите папку: /project PATH")
            return client, False
        target = Path(value).expanduser().resolve()
        if not target.is_dir():
            console.error(f"Папка не найдена: {target}")
            return client, False
        settings.project_root = str(target)
        preferences = load_preferences()
        preferences.remember_project(settings.project_root)
        with suppress(OSError):
            save_preferences(preferences)
        console.success(f"Рабочая папка: {target}")
        return None, False
    if command == "provider":
        provider = value.casefold() if value else console.choose("Провайдер", list(PROVIDER_MODELS))
        if provider not in PROVIDER_MODELS:
            console.error(f"Неизвестный провайдер: {provider}")
            return client, False
        if not configure_provider_key(provider, console, allow_replacement=False):
            console.error("Провайдер не изменён.")
            return client, False
        try:
            model = choose_model(provider, console)
        except (RuntimeError, ValueError) as exc:
            console.error(str(exc))
            return client, False
        settings.provider = provider
        settings.model = model
        settings.tool_compatibility = "unknown"
        if settings.agent and not verify_tool_compatibility(settings, console):
            settings.agent = False
            console.warning("Режим переключён на chat.")
        console.success(f"Провайдер: {provider} · Модель: {model}")
        return None, False
    if command == "model":
        if value:
            model = value
            try:
                validate_provider_model(settings.provider, model)
            except (RuntimeError, ValueError) as exc:
                console.error(str(exc))
                return client, False
        else:
            try:
                model = choose_model(settings.provider, console, settings.model)
            except (RuntimeError, ValueError) as exc:
                console.error(str(exc))
                return client, False
        settings.model = model
        settings.tool_compatibility = "unknown"
        if settings.agent and not verify_tool_compatibility(settings, console):
            settings.agent = False
            console.warning("Режим переключён на chat.")
        console.success(f"Модель: {model}")
        return None, False
    if command == "mode":
        mode = value.casefold() if value else console.choose("Режим", ["chat", "agent"])
        if mode not in {"chat", "agent"}:
            console.error("Используйте /mode chat или /mode agent")
            return client, False
        if mode == "agent" and not verify_tool_compatibility(settings, console):
            return client, False
        settings.agent = mode == "agent"
        console.success(f"Режим: {mode}")
        return None, False
    if command == "permissions":
        if value:
            permissions = value.casefold()
        else:
            permission_labels = {
                "Спрашивать перед действиями": "ask",
                "Автоподтверждение (полный доступ к рабочей папке)": "auto",
            }
            selected = console.choose("Разрешения агента", list(permission_labels))
            permissions = permission_labels[selected]
        if permissions not in {"ask", "auto"}:
            console.error("Используйте /permissions ask или /permissions auto")
            return client, False
        settings.auto_approve = permissions == "auto"
        if settings.auto_approve:
            console.warning("Автоподтверждение включено для текущей сессии.")
        else:
            console.success("Опасные действия требуют подтверждения")
        return client, False
    console.error(f"Неизвестная команда: /{command}. Используйте /help")
    return client, False


def create_client(provider: str, model: str | None, system_prompt: str):
    provider = provider.lower()
    if provider == "nvidia":
        from core.llm_client import NVIDIAClient

        key = os.getenv("NVIDIA_API_KEY", "")
        if not key:
            raise ValueError("NVIDIA_API_KEY не задан. Добавьте его в .env или окружение.")
        selected_model = model or env("NVIDIA_MODEL", PROVIDER_MODELS["nvidia"][0])
        return NVIDIAClient(
            key,
            system_prompt,
            model_chat=selected_model,
            model_code=selected_model,
        )
    if provider == "openai":
        from core.llm_client import OpenAIClient

        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise ValueError("OPENAI_API_KEY не задан. Добавьте его в .env или окружение.")
        selected_model = model or env("OPENAI_MODEL", PROVIDER_MODELS["openai"][0])
        return OpenAIClient(
            key,
            system_prompt,
            model_chat=selected_model,
            model_code=selected_model,
        )
    if provider == "ollama":
        from core.ollama_client import OllamaClient

        return OllamaClient(
            system_prompt,
            model_chat=model or env("OLLAMA_MODEL_CHAT", "llama3.2"),
            model_code=model or env("OLLAMA_MODEL_CODE", "qwen2.5-coder"),
            base_url=env("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    if provider == "local":
        from core.local_client import LocalClient

        return LocalClient(system_prompt, model=model or LOCAL_MODEL_ID)
    raise ValueError(f"Неизвестный провайдер: {provider}")


def run_chat(client: Any, prompt: str, console: Console) -> None:
    console.activity(f"Подключение к {provider_name(client)}…")
    started = perf_counter()
    console.stream(client.ask_stream(prompt))
    console.activity(f"Ответ получен за {perf_counter() - started:.1f} с")


def run_agent(
    client: Any,
    prompt: str,
    project_root: str,
    username: str,
    console: Console,
    auto_approve: bool = False,
    max_steps: int = 30,
    max_tool_calls: int = 100,
    max_seconds: int = 300,
    max_estimated_tokens: int = 32_000,
    approved_external_paths: set[str] | None = None,
) -> None:
    memory = AgentMemory(str(Path(project_root) / "logs" / "session.json"), username)
    memory.add("user", prompt)
    limits = AgentLimits(
        max_steps=max_steps,
        max_tool_calls=max_tool_calls,
        max_seconds=max_seconds,
        max_estimated_tokens=max_estimated_tokens,
    )
    guard = AgentLoopGuard(limits)
    guard.count_text(prompt)
    def approve(action: str, detail: str) -> bool:
        return True if auto_approve else console.confirm(action, detail)

    def approve_external(path: str) -> bool:
        return console.confirm(
            "Разрешить доступ вне рабочей папки?",
            f"{path}\nРазрешение запомнится до закрытия Citadex.",
        )

    tool_registry = create_tool_registry(
        project_root,
        approve,
        auto_approve=auto_approve,
        approve_external=approve_external,
        approved_external_paths=approved_external_paths,
    )
    prompt_dirty = False
    inspected_paths: set[str] = set()
    recovery_attempts = 0

    for _step in range(1, limits.max_steps + 1):
        exhausted = guard.budget_error()
        if exhausted is not None:
            console.error(exhausted.message)
            return
        if prompt_dirty:
            client.system_prompt = build_system_prompt(project_root, username, memory) + getattr(
                client,
                "system_prompt_suffix",
                "",
            )
            prompt_dirty = False
        if memory.history and memory.history[0].get("role") == "system":
            memory.history[0]["content"] = client.system_prompt
        else:
            memory.history.insert(0, {"role": "system", "content": client.system_prompt})
        memory.save()

        console.activity(f"Подключение к {provider_name(client)}…")
        started = perf_counter()
        response = "".join(client.ask_stream("", messages=memory.get_history()))
        console.activity(f"Ответ получен за {perf_counter() - started:.1f} с")
        guard.count_text(response)
        tool_calls = client.get_last_tool_calls()
        memory.add("assistant", response, tool_calls=tool_calls or None)

        if not tool_calls:
            pseudo_name = pseudo_tool_name(response)
            if pseudo_name is not None:
                console.error(
                    f"Модель напечатала псевдовызов {pseudo_name} вместо native tool call. "
                    "Выберите модель с надёжной поддержкой tools."
                )
                console.agent_summary(guard.records, project_root)
                return
            unresolved = unresolved_tool_failures(guard.records)
            if unresolved:
                if recovery_attempts < 2 and not guard.error_limit_reached:
                    recovery_attempts += 1
                    memory.add(
                        "user",
                        (
                            "The task is not complete because a tool action failed. "
                            "Recover now: inspect the current state with read_file when relevant, "
                            "change the arguments, and retry the failed action. "
                            "Do not merely explain the error."
                        ),
                    )
                    console.activity("Исправление ошибки инструмента…")
                    memory.trim(50)
                    continue
                console.agent_summary(guard.records, project_root)
                console.error("Задача не завершена: исправить ошибку инструмента автоматически не удалось.")
                return
            console.response(response)
            changed_paths = [
                record.detail
                for record in guard.records
                if record.name in {
                    "create_file",
                    "write_file",
                    "edit_file",
                    "move_file",
                    "copy_file",
                    "format_code",
                }
                and record.status is ToolStatus.SUCCESS
            ]
            if changed_paths:
                console.activity("Проверка изменённых файлов, синтаксиса и тестов")
                verification = verify_agent_changes(changed_paths, project_root)
                if not verification["ok"]:
                    console.agent_summary(guard.records, project_root)
                    console.error("Проверка не пройдена:\n" + "\n".join(verification["errors"]))
                    return
            console.agent_summary(guard.records, project_root)
            console.success("Задача завершена")
            return

        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            name = function.get("name", "")
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError as exc:
                result = {"status": "error", "error": f"Некорректные аргументы инструмента: {exc}"}
                guard.record_invalid_call(name)
            else:
                console.tool(name, arguments)
                call = normalize_tool_call({**tool_call, "function": {**function, "arguments": arguments}})
                guard_error = guard.inspect(call) or require_read_before_edit(
                    call,
                    project_root,
                    inspected_paths,
                )
                typed_result = (
                    ToolResult(
                        call_id=call.id,
                        name=call.name,
                        status=ToolStatus.ERROR,
                        error=guard_error,
                    )
                    if guard_error is not None
                    else tool_registry.execute(call)
                )
                guard.record(
                    call,
                    typed_result,
                    allow_same_retry=(
                        guard_error is not None
                        and guard_error.code == "READ_BEFORE_EDIT_REQUIRED"
                    ),
                )
                if typed_result.status is ToolStatus.SUCCESS and name == "read_file":
                    inspected_paths.add(tool_path_key(project_root, arguments))
                if typed_result.status is ToolStatus.SUCCESS and name in {
                    "create_file",
                    "write_file",
                    "edit_file",
                    "delete_file",
                    "make_directory",
                    "move_file",
                    "copy_file",
                    "format_code",
                }:
                    prompt_dirty = True
                result = tool_result_payload(typed_result)
            memory.add(
                "tool",
                json.dumps(result, ensure_ascii=False),
                tool_call_id=tool_call.get("id", "call_0"),
                name=name,
            )
            console.tool_result(result)
            if result.get("status") == "error":
                console.warning(recovery_advice(str(result.get("code", "")), project_root))
            if result.get("code") in {"TIME_BUDGET", "TOKEN_BUDGET", "TOOL_CALL_LIMIT"}:
                console.error(str(result.get("error")))
                return
            if result.get("code") == "UNKNOWN_TOOL":
                console.agent_summary(guard.records, project_root)
                console.error(f"Модель запросила неизвестный инструмент: {name}. Агент остановлен.")
                return
            if result.get("code") == "PATH_OUTSIDE_PROJECT":
                console.agent_summary(guard.records, project_root)
                console.error(
                    "Путь находится вне рабочей папки. Смените её командой "
                    f"/project <path> (сейчас: {project_root}) и повторите запрос."
                )
                return
        if guard.error_limit_reached:
            console.agent_summary(guard.records, project_root)
            console.error(f"Агент остановлен после {guard.consecutive_errors} последовательных ошибок.")
            return
        memory.trim(50)

    console.agent_summary(guard.records, project_root)
    console.error(f"Достигнут лимит в {limits.max_steps} шагов.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Citadex — CLI AI-ассистент для разработки")
    parser.add_argument("--version", action="version", version=f"%(prog)s {get_version()}")
    parser.add_argument("--project", "-p", default=None, help="Корень проекта")
    parser.add_argument("--provider", choices=["nvidia", "openai", "ollama", "local"], default=None)
    parser.add_argument("--model", "-m", help="Одна модель для чата и кода")
    parser.add_argument("--agent", "-a", action="store_true", help="Разрешить агентные инструменты")
    parser.add_argument("--oneshot", "-o", metavar="PROMPT", help="Выполнить один запрос и выйти")
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Автоматически подтверждать опасные действия"
    )
    parser.add_argument("--user", "-u", default=os.getenv("USER", os.getenv("USERNAME", "dev")))
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--max-tool-calls", type=int, default=100)
    parser.add_argument("--max-seconds", type=int, default=300)
    parser.add_argument("--max-tokens", type=int, default=32_000, dest="max_estimated_tokens")
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Пропустить интерактивный мастер запуска",
    )
    parser.add_argument("--local-only", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    console = Console(local_only=args.local_only)
    preferences = load_preferences()
    project_root = str(Path(args.project or os.getcwd()).resolve())
    if not Path(project_root).is_dir():
        console.error(f"Папка проекта не найдена: {project_root}")
        return 2
    preferences.remember_project(project_root)
    with suppress(OSError):
        save_preferences(preferences)
    session = AgentMemory(str(Path(project_root) / "logs" / "session.json"), args.user)
    provider = args.provider or preferences.provider or os.getenv("LLM_PROVIDER", "nvidia")
    preferred_model = args.model or preferences.models.get(provider)
    settings = SessionSettings(
        provider,
        preferred_model,
        args.agent or preferences.mode == "agent",
        args.yes or preferences.permissions == "auto",
    )
    settings.project_root = project_root
    settings.local_only = args.local_only
    interactive_setup = not args.oneshot and not args.skip_setup
    if interactive_setup:
        try:
            key_name = PROVIDER_API_KEYS.get(settings.provider)
            configured = bool(
                preferences.models.get(settings.provider)
                and (key_name is None or os.getenv(key_name))
            )
            quick = configured and console.quick_start(session_diagnostics(settings, session, None))
            if not quick:
                settings.project_root = choose_recent_project(console, preferences, settings.project_root)
                project_root = settings.project_root
                session = AgentMemory(str(Path(project_root) / "logs" / "session.json"), args.user)
                if not run_startup_setup(settings, console, preferences):
                    return 2
        except (EOFError, KeyboardInterrupt):
            console.goodbye()
            return 0
    else:
        if settings.provider == "ollama" and settings.model is None:
            with suppress(RuntimeError):
                settings.model = provider_models("ollama")[0]
        if settings.agent and not verify_tool_compatibility(settings, console):
            return 2
    client = None
    approved_external_paths: set[str] = set()
    console.header(settings.provider, settings.display_model, project_root, settings.agent)
    if args.local_only:
        console.hint("/project · /mode · /permissions · /undo · /status · /help")
    else:
        console.hint("/project · /provider · /model · /mode · /permissions · /help")
    if settings.auto_approve:
        console.warning("Автоподтверждение включено: агент может изменять файлы и запускать команды.")

    if args.oneshot:
        try:
            console.activity(f"Анализ рабочей папки: {settings.project_root}")
            client = create_client(
                settings.provider,
                settings.model,
                build_client_system_prompt(
                    settings.project_root,
                    args.user,
                    session,
                    agent=settings.agent,
                ),
            )
            if settings.agent:
                run_agent(
                    client,
                    args.oneshot,
                    settings.project_root,
                    args.user,
                    console,
                    settings.auto_approve,
                    args.max_steps,
                    args.max_tool_calls,
                    args.max_seconds,
                    args.max_estimated_tokens,
                    approved_external_paths,
                )
            else:
                run_chat(client, args.oneshot, console)
        except Exception as exc:
            console.error(explain_provider_error(exc, settings.provider.upper()))
            return 2
        return 0

    while True:
        try:
            prompt = console.prompt()
        except (EOFError, KeyboardInterrupt):
            console.goodbye()
            return 0
        if prompt.strip().lower() in {"exit", "quit", "q"}:
            console.goodbye()
            return 0
        slash = parse_slash(prompt)
        if slash is not None:
            client, should_exit = handle_slash(slash, settings, console, session, client)
            if should_exit:
                console.goodbye()
                return 0
            continue
        if not prompt.strip():
            continue
        try:
            if client is None:
                console.activity(f"Анализ рабочей папки: {settings.project_root}")
                client = create_client(
                    settings.provider,
                    settings.model,
                    build_client_system_prompt(
                        settings.project_root,
                        args.user,
                        session,
                        agent=settings.agent,
                    ),
                )
            if settings.agent:
                run_agent(
                    client,
                    prompt,
                    settings.project_root,
                    args.user,
                    console,
                    settings.auto_approve,
                    args.max_steps,
                    args.max_tool_calls,
                    args.max_seconds,
                    args.max_estimated_tokens,
                    approved_external_paths,
                )
            else:
                run_chat(client, prompt, console)
        except KeyboardInterrupt:
            console.warning("Запрос остановлен")
        except Exception as exc:
            console.error(explain_provider_error(exc, settings.provider.upper()))


if __name__ == "__main__":
    raise SystemExit(main())
