import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from core.llm_client import NVIDIAClient
from core.diff_applier import apply_diff
from core.context_manager import get_project_context
from ui.screen import (
    draw_header, draw_prompt, draw_separator,
    update_status, stream_response, show_apply_prompt,
    show_error, show_success, Spinner
)

# Загружаем .env если есть
load_dotenv()

# API ключ из .env или захардкоженный
API_KEY = os.getenv("NVIDIA_API_KEY", "nvapi-...")
MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")

client = NVIDIAClient(API_KEY, model=MODEL)


def main():
    draw_header(model_name=MODEL)

    while True:
        try:
            prompt = draw_prompt()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n  До встречи! 👋\n")
            break

        if prompt.strip().lower() in ("exit", "quit", "q"):
            print(f"\n  До встречи! 👋\n")
            break

        if not prompt.strip():
            continue

        # Контекст проекта
        update_status("Анализ проекта...")
        context = get_project_context()

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
            print(f"\n\n  {chr(0x2716)} Генерация прервана\n")
            continue
        except Exception as e:
            spinner.stop()
            show_error(str(e))
            continue

        # Предложение применить diff
        if show_apply_prompt():
            try:
                apply_diff("../main.py", full_response)
                show_success("Изменения применены!")
            except Exception as e:
                show_error(f"Не удалось применить: {e}")
        else:
            print()

        draw_separator()


if __name__ == "__main__":
    main()