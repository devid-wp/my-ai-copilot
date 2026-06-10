import os
import sys
import json
import subprocess

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI

# ANSI-коды для цветного вывода в терминал
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

SYSTEM_PROMPT = """Ты — автономный AI-агент, выполняющий задачи на компьютере пользователя.
Твоя цель — решить поставленную задачу пользователя, используя доступные инструменты.

Ты ОБЯЗАН отвечать ТОЛЬКО валидным JSON-объектом строго по указанной схеме. 
Любой текст, объяснения или комментарии должны быть записаны исключительно в поле "thought" внутри JSON.
НЕ оборачивай ответ в markdown-блоки ```json ... ```. Только чистый JSON.

ФОРМАТ ОТВЕТА (JSON):
{
  "thought": "Краткое описание твоих размышлений и следующего действия на русском языке",
  "tool": "patch" | "execute" | "done",
  "path": "путь к файлу (только для tool = patch)",
  "search": "строка для поиска (только для tool = patch, оставь пустой для перезаписи/создания)",
  "replace": "строка для замены/записи (только для tool = patch)",
  "command": "команда терминала для выполнения (только для tool = execute)"
}

ПРАВИЛА ИНСТРУМЕНТОВ:
1) "patch":
   - Если файл по пути "path" существует и "search" не пустой, то в файле заменится точное совпадение "search" на "replace".
   - Если файл не существует или "search" пустой, то файл создастся или перезапишется целиком содержимым "replace".
2) "execute":
   - Запускает команду терминала. Используй её для запуска тестов, компиляции, создания папок, просмотра содержимого директорий и т.д.
3) "done":
   - Отправь этот инструмент, когда задача пользователя полностью выполнена.

Всегда проверяй результаты своих действий (например, после создания или редактирования файла запусти его или проверь тесты через execute).
"""


def clean_json_string(s):
    """
    Очищает строку от markdown-разметки и извлекает JSON-объект.
    Ищет первую открывающую фигуру скобку { и последнюю закрывающую }.
    """
    s = s.strip()
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start:end+1].strip()
    
    # Резервная очистка от markdown, если фигурные скобки не найдены
    if s.startswith("```"):
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline:].strip()
        else:
            s = s[3:].strip()
    if s.endswith("```"):
        s = s[:-3].strip()
    return s


class CopilotAgent:
    """Агентный цикл выполнения задач пользователя."""

    def __init__(self, api_key, model="meta/llama-3.1-8b-instruct"):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        self.model = model
        self.history = []

    def run_task(self, user_prompt):
        # Начинаем диалог с системной инструкции и задачи
        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        print(f"\n{CYAN}[*] Запуск агента для задачи: {user_prompt}{RESET}\n")

        for iteration in range(1, 16):
            print(f"{YELLOW}[Итерация {iteration}/15] Запрос к модели...{RESET}")
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.history,
                    temperature=0.2,
                )
                raw_content = response.choices[0].message.content
            except Exception as e:
                print(f"{RED}[Ошибка API] {e}{RESET}")
                break

            # Очищаем и пытаемся распарсить JSON
            cleaned_content = clean_json_string(raw_content)
            try:
                action = json.loads(cleaned_content)
            except Exception as e:
                error_msg = f"Ошибка парсинга JSON: {e}. Пожалуйста, убедитесь, что ваш ответ является валидным JSON-объектом согласно схеме."
                print(f"{RED}[Ошибка] Не удалось распарсить JSON. Содержимое ответа:\n{raw_content}\nОтправка ошибки парсинга модели...{RESET}")
                self.history.append({"role": "assistant", "content": raw_content})
                self.history.append({"role": "user", "content": error_msg})
                continue

            thought = action.get("thought", "Без мыслей")
            tool = action.get("tool")

            print(f"{GREEN}[Мысль] {thought}{RESET}")
            
            # Сохраняем решение ассистента в историю
            self.history.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})

            if tool == "done":
                print(f"\n{GREEN}[+] Агент завершил выполнение задачи.{RESET}\n")
                break

            elif tool == "patch":
                path = action.get("path")
                search = action.get("search", "")
                replace = action.get("replace", "")

                if not path:
                    result_msg = "Ошибка: Не указан параметр 'path' для инструмента 'patch'."
                else:
                    result_msg = self.apply_patch(path, search, replace)

                print(f"{CYAN}[Результат patch] {result_msg}{RESET}")
                self.history.append({"role": "user", "content": result_msg})

            elif tool == "execute":
                command = action.get("command")

                if not command:
                    result_msg = "Ошибка: Не указан параметр 'command' для инструмента 'execute'."
                else:
                    result_msg = self.run_command(command)

                print(f"{CYAN}[Результат execute] {result_msg}{RESET}")
                self.history.append({"role": "user", "content": result_msg})

            else:
                result_msg = f"Ошибка: Неизвестный инструмент '{tool}'. Доступны: patch, execute, done."
                print(f"{RED}[Ошибка] {result_msg}{RESET}")
                self.history.append({"role": "user", "content": result_msg})
        else:
            print(f"\n{RED}[!] Достигнут лимит итераций (15). Задача прервана.{RESET}\n")

    def apply_patch(self, path, search, replace):
        """Реализация инструмента patch."""
        try:
            abs_path = os.path.abspath(path)
            
            if os.path.exists(abs_path) and search:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                
                if search in content:
                    new_content = content.replace(search, replace)
                    with open(abs_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    return f"Файл {path} успешно изменен (заменено совпадение)."
                else:
                    return f"Ошибка: Строка поиска не найдена в файле {path}."
            else:
                # Если search пустой или файл не существует — перезаписать/создать
                dir_name = os.path.dirname(abs_path)
                if dir_name:
                    os.makedirs(dir_name, exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(replace)
                return f"Файл {path} успешно создан/перезаписан."
        except Exception as e:
            return f"Ошибка при изменении файла {path}: {str(e)}"

    def run_command(self, command):
        """Реализация инструмента execute."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            if not output:
                output = "Команда выполнена успешно, вывод пуст."
            return f"Код возврата: {result.returncode}\n{output}"
        except subprocess.TimeoutExpired:
            return "Ошибка: Превышен таймаут выполнения команды (30 секунд)."
        except Exception as e:
            return f"Ошибка при выполнении команды: {str(e)}"


if __name__ == "__main__":
    # Активация поддержки ANSI-цветов в консоли Windows
    if sys.platform == "win32":
        os.system("color")

    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        print(f"{RED}[Ошибка] Не найдена переменная окружения NVIDIA_API_KEY.{RESET}")
        print("Пожалуйста, установите её перед запуском скрипта.")
        sys.exit(1)

    model = os.environ.get("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")

    print(f"{CYAN}{BOLD}==================================================")
    print("🚀 AI Copilot (NVIDIA Edition) запущен!")
    print(f"Модель: {model}")
    print(f"Управление: 'exit' / 'quit' для выхода")
    print(f"=================================================={RESET}\n")

    agent = CopilotAgent(api_key=api_key, model=model)

    while True:
        try:
            prompt = input("Prompt > ")
            if prompt.strip().lower() in ("exit", "quit", "q"):
                print(f"\n{CYAN}До встречи!{RESET}")
                break
            if not prompt.strip():
                continue
            
            agent.run_task(prompt)
        except KeyboardInterrupt:
            print(f"\n\n{YELLOW}[!] Задача прервана пользователем.{RESET}\n")
        except Exception as e:
            print(f"\n{RED}[Ошибка] {e}{RESET}\n")
