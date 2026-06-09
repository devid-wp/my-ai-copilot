# ui/screen.py
import sys
import time
import threading
import shutil


# ── Цвета (оставляем оригинальные) ──────────────────────────
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
WHITE = "\033[97m"
RED = "\033[91m"
MAGENTA = "\033[95m"

# ── Символы рамки ────────────────────────────────────────────
BOX_TL = "╭"
BOX_TR = "╮"
BOX_BL = "╰"
BOX_BR = "╯"
BOX_H = "─"
BOX_V = "│"


def get_width():
    """Получить ширину терминала."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def clear_screen():
    """Очистить экран."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def draw_box(lines, color=CYAN, padding=2):
    """Рисует текст в рамке."""
    w = get_width() - 2
    inner = w - padding * 2

    print(f"{color}{BOX_TL}{BOX_H * w}{BOX_TR}{RESET}")
    for line in lines:
        text = line[:inner]
        pad_right = inner - len(text)
        print(f"{color}{BOX_V}{RESET}{' ' * padding}{text}{' ' * (pad_right + padding)}{color}{BOX_V}{RESET}")
    print(f"{color}{BOX_BL}{BOX_H * w}{BOX_BR}{RESET}")


def draw_header(model_name="meta/llama-3.1-8b-instruct"):
    """Заголовок в стиле Claude Code."""
    clear_screen()
    lines = [
        f"{BOLD}{WHITE}🚀 NVIDIA VIBE-CODING ENGINE{RESET}",
        f"{DIM}Model: {model_name}{RESET}",
        "",
        f"{DIM}Введи запрос или 'exit' для выхода{RESET}",
    ]
    draw_box(lines, color=CYAN)
    print()


def draw_separator():
    """Тонкий разделитель между сообщениями."""
    w = get_width() - 4
    print(f"\n  {DIM}{BOX_H * w}{RESET}\n")


def draw_prompt():
    """Промпт ввода в стиле Claude Code."""
    return input(f"\n  {GREEN}{BOLD}❯{RESET} ")


def update_status(status):
    """Статус-сообщение."""
    print(f"  {YELLOW}● {status}{RESET}")


# ── Спиннер ──────────────────────────────────────────────────

class Spinner:
    """Анимированный спиннер для ожидания ответа."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, text="Думаю..."):
        self.text = text
        self._stop_event = threading.Event()
        self._thread = None

    def _animate(self):
        i = 0
        while not self._stop_event.is_set():
            frame = self.FRAMES[i % len(self.FRAMES)]
            sys.stdout.write(f"\r  {CYAN}{frame}{RESET} {DIM}{self.text}{RESET}  ")
            sys.stdout.flush()
            i += 1
            time.sleep(0.08)
        # Очистить строку спиннера
        sys.stdout.write(f"\r{' ' * (len(self.text) + 10)}\r")
        sys.stdout.flush()

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)


# ── Стриминговый вывод ───────────────────────────────────────

def stream_response(token_generator):
    """
    Печатает стриминговый ответ токен за токеном.
    Возвращает полный собранный ответ.
    
    Подсвечивает блоки кода и добавляет отступы.
    """
    full_response = []
    in_code_block = False
    line_buffer = ""
    first_token = True

    # Заголовок ответа
    print(f"\n  {CYAN}{BOLD}┃{RESET} ", end="")

    for token in token_generator:
        full_response.append(token)

        # Обработка каждого символа для форматирования
        for char in token:
            if char == "\n":
                # Проверяем не начало/конец блока кода
                if line_buffer.strip().startswith("```"):
                    in_code_block = not in_code_block
                    if in_code_block:
                        lang = line_buffer.strip()[3:]
                        sys.stdout.write(f"\n  {CYAN}{BOLD}┃{RESET}   {DIM}{'─' * 40}{RESET}")
                        if lang:
                            sys.stdout.write(f"  {DIM}[{lang}]{RESET}")
                        sys.stdout.write(f"\n  {CYAN}{BOLD}┃{RESET}   ")
                    else:
                        sys.stdout.write(f"\n  {CYAN}{BOLD}┃{RESET}   {DIM}{'─' * 40}{RESET}")
                        sys.stdout.write(f"\n  {CYAN}{BOLD}┃{RESET} ")
                    line_buffer = ""
                    continue

                sys.stdout.write(f"\n  {CYAN}{BOLD}┃{RESET} ")
                if in_code_block:
                    sys.stdout.write("  ")
                line_buffer = ""
            else:
                line_buffer += char
                if in_code_block:
                    sys.stdout.write(f"{GREEN}{char}{RESET}")
                else:
                    sys.stdout.write(char)

            sys.stdout.flush()

    # Финальная пустая строка
    print(f"\n  {CYAN}{BOLD}┃{RESET}")
    print()

    return "".join(full_response)


def show_apply_prompt():
    """Спрашивает пользователя о применении изменений."""
    w = get_width() - 4
    print(f"  {DIM}{BOX_H * w}{RESET}")
    answer = input(f"  {YELLOW}Применить изменения?{RESET} {DIM}[y/n]{RESET} ")
    return answer.lower() == "y"


def show_error(message):
    """Показать ошибку."""
    print(f"\n  {RED}✖ Ошибка: {message}{RESET}\n")


def show_success(message):
    """Показать успех."""
    print(f"  {GREEN}✔ {message}{RESET}\n")