"""Citadex CLI entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from core.agent_executor import dispatch_function
from core.console import Console
from core.context_manager import get_git_log, get_project_context
from core.memory import AgentMemory
from core.prompts import SYSTEM_PROMPT_TEMPLATE

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

    def approve(action: str, detail: str) -> bool:
        return True if auto_approve else console.confirm(action, detail)

    for step in range(1, max_steps + 1):
        client.system_prompt = build_system_prompt(project_root, username, memory)
        if memory.history and memory.history[0].get("role") == "system":
            memory.history[0]["content"] = client.system_prompt
        else:
            memory.history.insert(0, {"role": "system", "content": client.system_prompt})
        memory.save()

        console.step(step, max_steps, client.select_model(prompt))
        response = console.stream(client.ask_stream("", messages=memory.get_history()))
        tool_calls = client.get_last_tool_calls()
        memory.add("assistant", response, tool_calls=tool_calls or None)

        if not tool_calls:
            console.success("Задача завершена")
            return

        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            name = function.get("name", "")
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError as exc:
                result = {"status": "error", "error": f"Некорректные аргументы инструмента: {exc}"}
            else:
                console.tool(name, arguments.get("path") or arguments.get("command") or "")
                result = dispatch_function(name, arguments, project_root, approve=approve)
            memory.add(
                "tool",
                json.dumps(result, ensure_ascii=False),
                tool_call_id=tool_call.get("id", "call_0"),
                name=name,
            )
            console.tool_result(result)
        memory.trim(50)

    console.error(f"Достигнут лимит в {max_steps} шагов.")


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
    if args.agent and args.provider == "ollama":
        console.error("Ollama пока поддерживает только chat-режим: native tool calls недоступны.")
        return 2

    session = AgentMemory(str(Path(project_root) / "logs" / "session.json"), args.user)
    system_prompt = build_system_prompt(project_root, args.user, session)
    try:
        client = create_client(args.provider, args.model, system_prompt)
    except Exception as exc:
        console.error(str(exc))
        return 2

    console.header(args.provider, client.model_chat, project_root, args.agent or bool(args.oneshot))
    if args.yes:
        console.warning("Автоподтверждение включено: агент может изменять файлы и запускать команды.")

    if args.oneshot:
        if args.agent:
            run_agent(client, args.oneshot, project_root, args.user, console, args.yes, args.max_steps)
        else:
            run_chat(client, args.oneshot, console)
        return 0

    while True:
        try:
            prompt = console.prompt()
        except (EOFError, KeyboardInterrupt):
            console.goodbye()
            return 0
        command = prompt.strip().lower()
        if command in {"exit", "quit", "q"}:
            console.goodbye()
            return 0
        if command == "!clear":
            session.clear()
            client.reset_history()
            console.success("История очищена")
            continue
        if command == "!help":
            console.help()
            continue
        if not prompt.strip():
            continue
        try:
            if args.agent:
                run_agent(client, prompt, project_root, args.user, console, args.yes, args.max_steps)
            else:
                run_chat(client, prompt, console)
        except KeyboardInterrupt:
            console.warning("Запрос остановлен")
        except Exception as exc:
            console.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
