import sys
import os
import argparse

# Windows: принудительно UTF-8 для корректного вывода кириллицы
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from core.llm_client import NVIDIAClient
from core.file_ops import parse_operations, execute_operations
from core.context_manager import get_project_context
from ui.screen import (
    draw_header, draw_prompt, draw_separator,
    update_status, stream_response, show_ops_summary,
    show_error, Spinner
)

# Загружаем .env если есть
load_dotenv()

# API ключ из .env или захардкоженный
API_KEY = os.getenv("NVIDIA_API_KEY", "nvapi-...")
MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")


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


def main():
    parser = argparse.ArgumentParser(description="AI Copilot")
    parser.add_argument(
        "--project", "-p",
        default=os.getcwd(),
        help="Path to the project directory (default: current dir)"
    )
    args = parser.parse_args()

    project_root = os.path.abspath(args.project)

    if not os.path.isdir(project_root):
        print(f"Project directory not found: {project_root}")
        sys.exit(1)

    client = NVIDIAClient(API_KEY, model=MODEL)
    draw_header(model_name=MODEL)
    update_status(f"Project: {project_root}")

    while True:
        try:
            prompt = draw_prompt()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n  До встречи!\n")
            break

        if prompt.strip().lower() in ("exit", "quit", "q"):
            print(f"\n  До встречи!\n")
            break

        if not prompt.strip():
            continue

        # Контекст = инфо о системе + файлы проекта
        update_status("Анализ проекта...")
        system_info = _get_system_info(project_root)
        project_ctx = get_project_context(project_root)
        context = system_info + "\n" + project_ctx

        # Спиннер пока ждём первый токен
        spinner = Spinner("Генерация ответа...")
        spinner.start()

        try:
            # Создаём генератор стрима
            token_gen = client.ask_stream(prompt, context)

            # Получаем первый токен чтобы остановить спиннер
            first_token = next(token_gen)
            spinner.stop()

            # Оборачиваем: сначала первый токен, потом остальные
            def full_stream():
                yield first_token
                yield from token_gen

            # Стриминговый вывод
            full_response = stream_response(full_stream())

        except StopIteration:
            spinner.stop()
            show_error("Пустой ответ от модели")
            continue
        except KeyboardInterrupt:
            spinner.stop()
            print(f"\n\n  Генерация прервана\n")
            continue
        except Exception as e:
            spinner.stop()
            show_error(str(e))
            continue

        # Парсим файловые операции из ответа
        operations = parse_operations(full_response)

        if operations:
            # Автоматически выполняем все операции
            results = execute_operations(operations, project_root)
            show_ops_summary(results)

        draw_separator()


if __name__ == "__main__":
    main()