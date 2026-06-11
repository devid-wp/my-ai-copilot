import sys
import os
import argparse
import json

# Windows: принудительно UTF-8 для корректного вывода кириллицы
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from core.llm_client import NVIDIAClient
from core.agent_executor import dispatch_function
from core.context_manager import get_project_context
from core.file_ops import parse_operations, execute_operations
from core.prompts import SYSTEM_PROMPT_TEMPLATE
from ui.screen import (
    draw_header, draw_prompt, draw_separator,
    update_status, stream_response, show_ops_summary,
    show_error, show_success, Spinner, show_tool_status,
)

# Загружаем .env если есть
load_dotenv()

# API ключ из .env или захардкоженный
API_KEY = os.getenv("NVIDIA_API_KEY", "nvapi-...")
MODEL_CHAT = os.getenv("NVIDIA_MODEL_CHAT", "meta/llama-3.1-8b-instruct")
MODEL_CODE = os.getenv("NVIDIA_MODEL_CODE", "meta/llama-3.3-70b-instruct")


def _get_system_info(project_root):
    """Информация о системе для передачи модели."""
    home = os.path.expanduser("~")
    desktop = os.path.join(home, "Desktop")
    username = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    return (
        f"OS: Windows\n"
        f"Username: {username}\n"
        f"Home: {home}\n"
        f"Desktop: {desktop}\n"
        f"Current project: {project_root}\n"
    )


def run_agent_loop(client: NVIDIAClient, initial_prompt: str, project_root: str):
    """Autonomous agent loop: up to 40 iterations.

    Each iteration:
    1. Calls the model (streaming).
    2. If tool_calls are returned  → execute them and feed results back.
    3. If legacy file-ops text returned → execute and feed results back.
    4. If no actions at all → agent is done, break.
    """
    from core.memory import AgentMemory
    session_file = os.path.join(project_root, "logs", "session.json")
    memory = AgentMemory(session_file)

    # Append user prompt to memory
    memory.add("user", initial_prompt)

    MAX_ITERATIONS = 40
    iteration = 1
    no_action_streak = 0

    while iteration <= MAX_ITERATIONS:
        update_status(f"Агент — шаг {iteration}/{MAX_ITERATIONS}...")
        selected_model = client.select_model(initial_prompt)
        if selected_model == client.model_code:
            print("  🧠 Модель кода")
        else:
            print("  💬 Модель чата")
        project_ctx = get_project_context(project_root)
        
        # Build system prompt from template
        client.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            project_root=project_root,
            project_tree=project_ctx
        )

        # Ensure system message is the first message in memory
        if memory.history and memory.history[0].get("role") == "system":
            memory.history[0]["content"] = client.system_prompt
            memory._save()
        else:
            memory.history.insert(0, {"role": "system", "content": client.system_prompt})
            memory._save()

        spinner = Spinner(f"Генерация (шаг {iteration}/{MAX_ITERATIONS})...")
        spinner.start()

        try:
            # Pass memory.get_history() as messages to ask_stream
            token_gen = client.ask_stream("", messages=memory.get_history())

            # Получаем первый токен, чтобы остановить спиннер
            try:
                first_token = next(token_gen)
                spinner.stop()
            except StopIteration:
                # Модель вернула только tool_calls без текста — это нормально
                spinner.stop()
                first_token = None

            if first_token is not None:
                def full_stream():
                    yield first_token
                    yield from token_gen
                full_response = stream_response(full_stream())
            else:
                # Дочитываем генератор до конца (нужно для накопления tool_calls)
                for _ in token_gen:
                    pass
                full_response = ""

        except KeyboardInterrupt:
            spinner.stop()
            print("\n\n  Генерация прервана\n")
            break
        except Exception as e:
            spinner.stop()
            show_error(str(e))
            break

        # Check for TASK COMPLETE
        has_task_complete = "ЗАДАЧА ВЫПОЛНЕНА:" in full_response

        # ── 1. Обрабатываем native tool_calls ───────────────────────────
        tool_calls = client.get_last_tool_calls()
        
        # ── 2. Legacy текстовые операции [CREATE_FILE: …] ───────────────
        operations = parse_operations(full_response)
        
        if tool_calls or operations:
            no_action_streak = 0
        else:
            no_action_streak += 1

        if tool_calls:
            # Сохраняем ответ ассистента с вызовами инструментов
            memory.add("assistant", full_response, tool_calls=tool_calls)
            
            tool_results = []
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                raw_args = tc["function"]["arguments"]
                try:
                    args = json.loads(raw_args) if raw_args else {}
                except json.JSONDecodeError:
                    args = {}
                result = dispatch_function(func_name, args, project_root)
                tool_results.append(f"[{func_name}] → {json.dumps(result, ensure_ascii=False)}")
                
                # Добавляем результат работы инструмента в память
                memory.add(
                    "tool",
                    json.dumps(result, ensure_ascii=False),
                    tool_call_id=tc.get("id", "call_0"),
                    name=func_name
                )
            
            memory.trim(50)
            
            if has_task_complete:
                summary = full_response.split("ЗАДАЧА ВЫПОЛНЕНА:", 1)[1].strip()
                show_success(f"ЗАДАЧА ВЫПОЛНЕНА: {summary}")
                break
                
            iteration += 1
            draw_separator()
            continue

        if operations:
            # Сохраняем текстовый ответ ассистента
            memory.add("assistant", full_response)
            
            results = execute_operations(operations, project_root)
            show_ops_summary(results)
            feedback = []
            for r in results:
                status = "Успешно" if r.success else f"Ошибка: {r.message}"
                if r.action == "execute":
                    feedback.append(f"Команда '{r.path}': {status}\n{r.message}")
                else:
                    feedback.append(f"Операция {r.action} над {r.path}: {status}")
            
            user_feedback = "Результаты выполнения операций:\n" + "\n".join(feedback)
            # Добавляем фидбэк в память как сообщение от пользователя
            memory.add("user", user_feedback)
            
            memory.trim(50)
            
            if has_task_complete:
                summary = full_response.split("ЗАДАЧА ВЫПОЛНЕНА:", 1)[1].strip()
                show_success(f"ЗАДАЧА ВЫПОЛНЕНА: {summary}")
                break
                
            iteration += 1
            draw_separator()
            continue

        # ── 3. Нет ни tool_calls, ни операций — задача выполнена ────────
        memory.add("assistant", full_response)
        memory.trim(50)

        if has_task_complete:
            summary = full_response.split("ЗАДАЧА ВЫПОЛНЕНА:", 1)[1].strip()
            show_success(f"ЗАДАЧА ВЫПОЛНЕНА: {summary}")
            break

        if no_action_streak >= 2:
            show_success("Агент завершил задачу (нет действий 2 шага подряд).")
            break

        iteration += 1
        draw_separator()

    draw_separator()


def main():
    parser = argparse.ArgumentParser(description="AI Copilot — автономный агент")
    parser.add_argument(
        "--project", "-p",
        default=os.getcwd(),
        help="Путь к папке проекта (по умолчанию: текущая)",
    )
    parser.add_argument(
        "--agent", action="store_true",
        help="Включить агентный режим (autonomous tool-calling loop)",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Модель NVIDIA LLM (перезаписывает NVIDIA_MODEL из .env)",
    )
    args = parser.parse_args()

    project_root = os.path.abspath(args.project)

    if not os.path.isdir(project_root):
        print(f"Папка проекта не найдена: {project_root}")
        sys.exit(1)

    if args.model:
        selected_model_chat = args.model
        selected_model_code = args.model
    else:
        selected_model_chat = MODEL_CHAT
        selected_model_code = MODEL_CODE

    project_ctx = get_project_context(project_root)
    initial_system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        project_root=project_root,
        project_tree=project_ctx
    )
    client = NVIDIAClient(
        API_KEY,
        system_prompt=initial_system_prompt,
        model_chat=selected_model_chat,
        model_code=selected_model_code
    )
    mode_label = "AGENT" if args.agent else "CHAT"
    model_display = args.model if args.model else f"{selected_model_chat} & {selected_model_code}"
    draw_header(model_name=f"{model_display}  [{mode_label}]")
    update_status(f"Проект: {project_root}")
    if args.agent:
        update_status("Режим: АГЕНТ  (до 15 итераций, tool-calling включён)")

    while True:
        try:
            prompt = draw_prompt()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  До встречи!\n")
            break

        if prompt.strip().lower() in ("exit", "quit", "q"):
            print("\n  До встречи!\n")
            break

        if prompt.strip() == "!clear":
            from core.memory import AgentMemory
            session_file = os.path.join(project_root, "logs", "session.json")
            memory = AgentMemory(session_file)
            memory.clear()
            client.reset_history()
            show_success("История диалога и сессия очищены.")
            continue

        if not prompt.strip():
            continue

        if args.agent:
            run_agent_loop(client, prompt, project_root)
        else:
            # ── Обычный режим (один запрос, стриминг) ───────────────────
            selected_model = client.select_model(prompt)
            if selected_model == client.model_code:
                print("  🧠 Модель кода")
            else:
                print("  💬 Модель чата")

            system_info = _get_system_info(project_root)
            project_ctx = get_project_context(project_root)
            context = system_info + "\n" + project_ctx
            client.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                project_root=project_root,
                project_tree=project_ctx
            )

            spinner = Spinner("Генерация ответа...")
            spinner.start()
            try:
                token_gen = client.ask_stream(prompt, context)
                first_token = next(token_gen)
                spinner.stop()

                def full_stream():
                    yield first_token
                    yield from token_gen

                full_response = stream_response(full_stream())

                # Выполняем файловые операции если модель их написала
                operations = parse_operations(full_response)
                if operations:
                    results = execute_operations(operations, project_root)
                    show_ops_summary(results)

            except StopIteration:
                spinner.stop()
                show_error("Пустой ответ от модели")
            except KeyboardInterrupt:
                spinner.stop()
                print("\n\n  Генерация прервана\n")
            except Exception as e:
                spinner.stop()
                show_error(str(e))

            draw_separator()


if __name__ == "__main__":
    main()