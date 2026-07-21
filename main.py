"""Citadex CLI entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from core.agent_executor import create_tool_registry, tool_result_payload
from core.agent_loop import AgentLoopGuard, pseudo_tool_name
from core.console import Console
from core.context_manager import get_git_log, get_project_context
from core.credentials import PROVIDER_API_KEYS, load_credentials, save_api_key, validate_api_key
from core.memory import AgentMemory
from core.prompts import SYSTEM_PROMPT_TEMPLATE
from core.tools import AgentLimits, ToolCall, ToolResult, ToolStatus

PROVIDER_MODELS = {
    "nvidia": ["meta/llama-3.1-8b-instruct", "meta/llama-3.3-70b-instruct"],
    "gemini": ["gemini-2.0-flash", "gemini-2.5-pro"],
    "ollama": ["llama3.2", "qwen2.5-coder"],
}


@dataclass
class SessionSettings:
    provider: str = "nvidia"
    model: str | None = None
    agent: bool = False
    auto_approve: bool = False

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
        project_tree=get_project_context(project_root),
        current_user=username,
        team_activity=memory.get_summary() or "— нет данных —",
        git_log=get_git_log(project_root) or "— git log недоступен —",
    )


def env(name: str, default: str) -> str:
    return os.getenv(name) or default


def provider_models(provider: str) -> list[str]:
    """Return configured cloud models or models installed in local Ollama."""
    if provider != "ollama":
        return PROVIDER_MODELS[provider]

    from core.ollama_client import OllamaClient

    models = OllamaClient(
        "",
        base_url=env("OLLAMA_BASE_URL", "http://localhost:11434"),
    ).list_models()
    if not models:
        raise RuntimeError("Ollama не вернул ни одной установленной модели.")
    return models


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
    if command in {"exit", "quit"}:
        return client, True
    if command == "help":
        console.help()
        return client, False
    if command == "status":
        console.status(settings.provider, settings.display_model, settings.mode, settings.permissions)
        return client, False
    if command == "clear":
        session.clear()
        if client is not None:
            client.reset_history()
        console.success("История очищена")
        return client, False
    if command == "provider":
        provider = value.casefold() if value else console.choose("Провайдер", list(PROVIDER_MODELS))
        if provider not in PROVIDER_MODELS:
            console.error(f"Неизвестный провайдер: {provider}")
            return client, False
        environment_name = PROVIDER_API_KEYS.get(provider)
        if environment_name:
            saved_key = os.getenv(environment_name, "").strip()
            label = f"{provider.upper()} API key"
            if saved_key:
                label += " (Enter = оставить сохранённый)"
            entered_key = console.secret(label).strip()
            if not entered_key and not saved_key:
                console.error("API-ключ не введён. Провайдер не изменён.")
                return client, False
            api_key = entered_key or saved_key
            try:
                validate_api_key(provider, api_key)
                if entered_key:
                    save_api_key(provider, api_key)
            except ValueError as exc:
                console.error(str(exc))
                return client, False
            except OSError as exc:
                console.error(f"Не удалось сохранить API-ключ: {exc}")
                return client, False
            if entered_key:
                console.success("API-ключ сохранён в пользовательской конфигурации Citadex")
        settings.provider = provider
        settings.model = None
        if provider == "ollama":
            try:
                settings.model = provider_models(provider)[0]
            except RuntimeError as exc:
                console.warning(str(exc))
        console.success(f"Провайдер: {provider}")
        return None, False
    if command == "model":
        if value:
            model = value
        else:
            try:
                models = provider_models(settings.provider)
            except RuntimeError as exc:
                console.error(str(exc))
                return client, False
            model = console.choose("Модель", models)
        settings.model = model
        console.success(f"Модель: {model}")
        return None, False
    if command == "mode":
        mode = value.casefold() if value else console.choose("Режим", ["chat", "agent"])
        if mode not in {"chat", "agent"}:
            console.error("Используйте /mode chat или /mode agent")
            return client, False
        settings.agent = mode == "agent"
        console.success(f"Режим: {mode}")
        return client, False
    if command == "permissions":
        permissions = value.casefold() if value else console.choose("Подтверждения", ["ask", "auto"])
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
        return NVIDIAClient(
            key,
            system_prompt,
            model_chat=model or env("NVIDIA_MODEL_CHAT", "meta/llama-3.1-8b-instruct"),
            model_code=model or env("NVIDIA_MODEL_CODE", "meta/llama-3.3-70b-instruct"),
        )
    if provider == "gemini":
        from core.gemini_client import GeminiClient

        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY не задан. Добавьте его в .env или окружение.")
        return GeminiClient(
            key,
            system_prompt,
            model_chat=model or env("GEMINI_MODEL_CHAT", "gemini-2.0-flash"),
            model_code=model or env("GEMINI_MODEL_CODE", "gemini-2.5-pro"),
        )
    if provider == "ollama":
        from core.ollama_client import OllamaClient

        return OllamaClient(
            system_prompt,
            model_chat=model or env("OLLAMA_MODEL_CHAT", "llama3.2"),
            model_code=model or env("OLLAMA_MODEL_CODE", "qwen2.5-coder"),
            base_url=env("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    raise ValueError(f"Неизвестный провайдер: {provider}")


def run_chat(client: Any, prompt: str, console: Console) -> None:
    console.stream(client.ask_stream(prompt))


def run_agent(
    client: Any,
    prompt: str,
    project_root: str,
    username: str,
    console: Console,
    auto_approve: bool = False,
    max_steps: int = 30,
) -> None:
    memory = AgentMemory(str(Path(project_root) / "logs" / "session.json"), username)
    memory.add("user", prompt)
    limits = AgentLimits(max_steps=max_steps)
    guard = AgentLoopGuard(limits)

    def approve(action: str, detail: str) -> bool:
        return True if auto_approve else console.confirm(action, detail)

    tool_registry = create_tool_registry(project_root, approve, auto_approve=auto_approve)

    for step in range(1, limits.max_steps + 1):
        client.system_prompt = build_system_prompt(project_root, username, memory)
        if memory.history and memory.history[0].get("role") == "system":
            memory.history[0]["content"] = client.system_prompt
        else:
            memory.history.insert(0, {"role": "system", "content": client.system_prompt})
        memory.save()

        console.step(step, limits.max_steps, client.select_model(prompt))
        response = console.stream(client.ask_stream("", messages=memory.get_history()))
        tool_calls = client.get_last_tool_calls()
        memory.add("assistant", response, tool_calls=tool_calls or None)

        if not tool_calls:
            pseudo_name = pseudo_tool_name(response)
            if pseudo_name is not None:
                console.error(
                    f"Модель напечатала псевдовызов {pseudo_name} вместо native tool call. "
                    "Выберите модель с надёжной поддержкой tools."
                )
                console.agent_summary(guard.records)
                return
            console.agent_summary(guard.records)
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
                call = ToolCall(
                    id=tool_call.get("id", "call_0"),
                    name=name,
                    arguments=arguments,
                )
                guard_error = guard.inspect(call)
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
                guard.record(call, typed_result)
                result = tool_result_payload(typed_result)
            memory.add(
                "tool",
                json.dumps(result, ensure_ascii=False),
                tool_call_id=tool_call.get("id", "call_0"),
                name=name,
            )
            console.tool_result(result)
        if guard.error_limit_reached:
            console.agent_summary(guard.records)
            console.error(
                f"Агент остановлен после {guard.consecutive_errors} последовательных ошибок."
            )
            return
        memory.trim(50)

    console.agent_summary(guard.records)
    console.error(f"Достигнут лимит в {limits.max_steps} шагов.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Citadex — CLI AI-ассистент для разработки")
    parser.add_argument("--project", "-p", default=os.getcwd(), help="Корень проекта")
    parser.add_argument(
        "--provider", choices=["nvidia", "gemini", "ollama"], default=os.getenv("LLM_PROVIDER", "nvidia")
    )
    parser.add_argument("--model", "-m", help="Одна модель для чата и кода")
    parser.add_argument("--agent", "-a", action="store_true", help="Разрешить агентные инструменты")
    parser.add_argument("--oneshot", "-o", metavar="PROMPT", help="Выполнить один запрос и выйти")
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Автоматически подтверждать опасные действия"
    )
    parser.add_argument("--user", "-u", default=os.getenv("USER", os.getenv("USERNAME", "dev")))
    parser.add_argument("--max-steps", type=int, default=30)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = str(Path(args.project).resolve())
    console = Console()
    if not Path(project_root).is_dir():
        console.error(f"Папка проекта не найдена: {project_root}")
        return 2
    session = AgentMemory(str(Path(project_root) / "logs" / "session.json"), args.user)
    settings = SessionSettings(args.provider, args.model, args.agent, args.yes)
    if settings.provider == "ollama" and settings.model is None:
        with suppress(RuntimeError):
            settings.model = provider_models("ollama")[0]
    client = None
    console.header(settings.provider, settings.display_model, project_root, settings.agent)
    console.hint("/provider · /model · /mode · /permissions · /help")
    if settings.auto_approve:
        console.warning("Автоподтверждение включено: агент может изменять файлы и запускать команды.")

    if args.oneshot:
        try:
            client = create_client(
                settings.provider,
                settings.model,
                build_system_prompt(project_root, args.user, session),
            )
            if settings.agent:
                run_agent(
                    client,
                    args.oneshot,
                    project_root,
                    args.user,
                    console,
                    settings.auto_approve,
                    args.max_steps,
                )
            else:
                run_chat(client, args.oneshot, console)
        except Exception as exc:
            console.error(str(exc))
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
                client = create_client(
                    settings.provider,
                    settings.model,
                    build_system_prompt(project_root, args.user, session),
                )
            if settings.agent:
                run_agent(
                    client,
                    prompt,
                    project_root,
                    args.user,
                    console,
                    settings.auto_approve,
                    args.max_steps,
                )
            else:
                run_chat(client, prompt, console)
        except KeyboardInterrupt:
            console.warning("Запрос остановлен")
        except Exception as exc:
            console.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
