# ui/screen.py
import sys
import time
import threading
import shutil

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.keys import Keys
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import is_done, is_multiline, has_selection, vi_insert_mode, emacs_insert_mode


# ── Цвета ANSI (оставляем оригинальные) ─────────────────────
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
DIM     = "\033[2m"
BOLD    = "\033[1m"
RESET   = "\033[0m"
WHITE   = "\033[97m"
RED     = "\033[91m"
MAGENTA = "\033[95m"

# ── Символы рамки ────────────────────────────────────────────
BOX_TL = "╭"
BOX_TR = "╮"
BOX_BL = "╰"
BOX_BR = "╯"
BOX_H  = "─"
BOX_V  = "│"


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
        # strip ANSI для подсчёта длины
        import re
        visible = re.sub(r'\033\[[0-9;]*m', '', line)
        pad_right = max(0, inner - len(visible))
        print(f"{color}{BOX_V}{RESET}{' ' * padding}{line}{' ' * (pad_right + padding)}{color}{BOX_V}{RESET}")
    print(f"{color}{BOX_BL}{BOX_H * w}{BOX_BR}{RESET}")


def draw_header(model_name="meta/llama-3.1-8b-instruct"):
    """Заголовок терминала."""
    clear_screen()
    lines = [
        f"{BOLD}{WHITE}NVIDIA VIBE-CODING ENGINE{RESET}",
        f"{DIM}Model: {model_name}{RESET}",
        "",
        f"{DIM}Enter — отправить  |  Alt+Enter — новая строка  |  'exit' — выход{RESET}",
    ]
    draw_box(lines, color=CYAN)
    print()


def draw_separator():
    """Тонкий разделитель между сообщениями."""
    w = get_width() - 4
    print(f"\n  {DIM}{BOX_H * w}{RESET}\n")


def update_status(status):
    """Статус-сообщение."""
    print(f"  {YELLOW}● {status}{RESET}")


# ── Input Bar ────────────────────────────────────────────────

# Стиль для prompt_toolkit
_PT_STYLE = Style.from_dict({
    # Рамка
    "frame-top":    "#61afef",      # голубой (ближайший к CYAN)
    "frame-side":   "#61afef",
    "frame-bottom": "#61afef",
    # Промпт-символ
    "prompt-gt":    "bold #98c379", # зелёный
    # Сам текст ввода
    "":             "#dcdfe4",      # светло-серый (нейтральный)
    # Placeholder
    "placeholder":  "#555555 italic",
})

def _make_keybindings():
    """
    Enter       → отправить (submit)
    Alt+Enter   → новая строка в буфере
    """
    kb = KeyBindings()
    insert_mode = vi_insert_mode | emacs_insert_mode

    # Переопределяем Enter для отправки в многострочном режиме
    @kb.add("enter", filter=is_multiline & ~has_selection & insert_mode)
    def _submit(event):
        event.current_buffer.validate_and_handle()

    # Alt+Enter / Esc+Enter для ввода новой строки
    @kb.add("escape", "enter")
    def _newline(event):
        event.current_buffer.insert_text("\n")

    return kb


def _bottom_toolbar():
    return HTML(
        '<style bg="#1a1a1a" fg="#555555">'
        '  Alt+Enter — новая строка  |  Enter — отправить  |  exit — выход'
        '</style>'
    )


def _create_prompt_session():
    """Create a PromptSession if possible, otherwise return None for fallback."""
    try:
        from prompt_toolkit.output.win32 import NoConsoleScreenBufferError
    except Exception:
        NoConsoleScreenBufferError = Exception
    try:
        return PromptSession(
            style=_PT_STYLE,
            key_bindings=_make_keybindings(),
            multiline=True,
            bottom_toolbar=_bottom_toolbar,
            prompt_continuation=lambda width, line, is_soft_wrap: "  " + f"{BOX_V} ",
        )
    except NoConsoleScreenBufferError:
        return None
    except Exception:
        return None

# Initialize the session (may be None if console unavailable)
_session = _create_prompt_session()


def draw_prompt():
    """Input bar with frame and multiline support.

    Falls back to built‑in input() when PromptSession cannot be used (e.g., missing console).
    """
    w = get_width()

    # Top border with title
    title = " Ask Copilot "
    title_len = len(title)
    bar_len = max(1, w - 2 - title_len - 1)
    top_border = f"{CYAN}{BOX_TL}{BOX_H}{RESET}{BOLD}{WHITE}{title}{RESET}{CYAN}{BOX_H * bar_len}{BOX_TR}{RESET}\n"
    sys.stdout.write(f"\n{top_border}")
    sys.stdout.write(f"{CYAN}{BOX_V}{RESET} ")
    sys.stdout.flush()

    # If PromptSession could not be created, use simple input fallback
    if _session is None:
        try:
            result = input("\n> ")
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write(f"\n{CYAN}{BOX_BL}{BOX_H * (w - 2)}{BOX_BR}{RESET}\n\n")
            sys.stdout.flush()
            raise KeyboardInterrupt
    else:
        try:
            result = _session.prompt(
                "",
                prompt_continuation=lambda w, ln, sw: f"{CYAN}{BOX_V}{RESET} ",
                placeholder="Ask Copilot... (Alt+Enter for newline)",
            )
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write(f"\n{CYAN}{BOX_BL}{BOX_H * (w - 2)}{BOX_BR}{RESET}\n\n")
            sys.stdout.flush()
            raise KeyboardInterrupt

    # Bottom border
    sys.stdout.write(f"{CYAN}{BOX_BL}{BOX_H * (w - 2)}{BOX_BR}{RESET}\n\n")
    sys.stdout.flush()

    return result.strip() if result else ""


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

    print(f"\n  {CYAN}{BOLD}┃{RESET} ", end="")

    for token in token_generator:
        full_response.append(token)

        for char in token:
            if char == "\n":
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

    print(f"\n  {CYAN}{BOLD}┃{RESET}")
    print()

    return "".join(full_response)


# ── Вывод ошибок и успеха ────────────────────────────────────

def show_error(message):
    """Показать ошибку."""
    print(f"\n  {RED}[x] Ошибка: {message}{RESET}\n")


def show_success(message):
    """Показать успех."""
    print(f"  {GREEN}[v] {message}{RESET}\n")

# ── Статус выполнения инструмента ────────────────────────────────────────

def show_tool_status(action: str, path: str = ""):
    """Отображает текущий статус выполнения инструмента.
    Пример: "⏳ Выполняю: create_file для src/main.py"
    """
    status_msg = f"⏳ Выполняю: {action}" + (f" для {path}" if path else "")
    print(f"  {YELLOW}{status_msg}{RESET}")


# ── Вывод файловых операций ──────────────────────────────────

_ACTION_STYLE = {
    'create': (GREEN,  '+', 'Создан'),
    'mkdir':  (CYAN,   'd', 'Папка'),
    'edit':   (YELLOW, '~', 'Изменён'),
    'delete': (RED,    '-', 'Удалён'),
    'execute':(CYAN,   '>', 'Запуск'),
}


def show_file_op(result):
    """Показать результат одной файловой операции или команды."""
    color, icon, label = _ACTION_STYLE.get(
        result.action, (WHITE, '?', result.action)
    )
    if result.success:
        print(f"  {color}[{icon}] {label}: {result.path}{RESET}")
        if result.action == 'execute' and result.message:
            # Выводим результат работы команды тусклым цветом со сдвигом
            lines = result.message.strip().splitlines()
            for line in lines:
                print(f"      {DIM}{line}{RESET}")
    else:
        print(f"  {RED}[x] {label}: {result.path} -- {result.message}{RESET}")


def show_ops_summary(results):
    """Показать сводку всех файловых операций."""
    if not results:
        return

    w = get_width() - 4
    print(f"  {DIM}{BOX_H * w}{RESET}")

    for r in results:
        show_file_op(r)

    ok   = sum(1 for r in results if r.success)
    fail = len(results) - ok
    parts = []
    if ok:
        parts.append(f"{GREEN}{ok} ok{RESET}")
    if fail:
        parts.append(f"{RED}{fail} failed{RESET}")
    print(f"  {DIM}{BOX_H * w}{RESET}")
    print(f"  {', '.join(parts)}")