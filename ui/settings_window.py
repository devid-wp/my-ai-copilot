# ui/settings_window.py
import customtkinter as ctk
import os
from pathlib import Path


class SettingsWindow(ctk.CTkToplevel):
    """Окно настроек API ключей — открывается поверх главного окна."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Citadex — Настройки")
        self.geometry("500x420")
        self.resizable(False, False)
        self.configure(fg_color="#111111")

        # Модальное окно
        self.transient(parent)
        self.grab_set()
        self.focus_set()

        self._env_path = Path(__file__).parent.parent / ".env"
        self._vars = {}
        self._build()
        self._load_values()

    def _build(self):
        # Заголовок
        ctk.CTkLabel(
            self,
            text="⚙ Настройки API ключей",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(padx=24, pady=(20, 4), anchor="w")

        ctk.CTkLabel(
            self,
            text="Ключи сохраняются в файл .env в папке проекта",
            font=ctk.CTkFont(size=11),
            text_color="#555",
        ).pack(padx=24, anchor="w")

        ctk.CTkFrame(self, height=1, fg_color="#222").pack(
            fill="x", padx=24, pady=12
        )

        # Поля ввода
        fields = [
            ("GEMINI_API_KEY", "Gemini API Key",
             "aistudio.google.com/apikey — бесплатно"),
            ("NVIDIA_API_KEY", "NVIDIA API Key",
             "build.nvidia.com — бесплатно"),
            ("GEMINI_MODEL_CHAT", "Gemini модель (чат)",
             "gemini-2.0-flash"),
            ("GEMINI_MODEL_CODE", "Gemini модель (код)",
             "gemini-2.5-pro"),
        ]

        for key, label, hint in fields:
            frame = ctk.CTkFrame(self, fg_color="transparent")
            frame.pack(fill="x", padx=24, pady=4)

            ctk.CTkLabel(
                frame, text=label,
                font=ctk.CTkFont(size=12),
                text_color="#ccc",
                width=160, anchor="w",
            ).pack(side="left")

            var = ctk.StringVar()
            self._vars[key] = var

            show = "*" if "KEY" in key else ""
            entry = ctk.CTkEntry(
                frame,
                textvariable=var,
                show=show,
                placeholder_text=hint,
                fg_color="#1a1a1a",
                border_color="#2a2a2a",
                font=ctk.CTkFont(size=12),
            )
            entry.pack(side="left", fill="x", expand=True)

            # Кнопка показать/скрыть для ключей
            if "KEY" in key:
                def make_toggle(e=entry):
                    def toggle():
                        e.configure(show="" if e.cget("show") == "*" else "*")
                    return toggle
                ctk.CTkButton(
                    frame, text="👁", width=32, height=28,
                    fg_color="transparent", hover_color="#222",
                    command=make_toggle(),
                ).pack(side="left", padx=(4,0))

        # Ollama URL
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=24, pady=4)
        ctk.CTkLabel(
            frame, text="Ollama URL",
            font=ctk.CTkFont(size=12), text_color="#ccc",
            width=160, anchor="w",
        ).pack(side="left")
        var = ctk.StringVar(value="http://localhost:11434")
        self._vars["OLLAMA_BASE_URL"] = var
        ctk.CTkEntry(
            frame, textvariable=var,
            fg_color="#1a1a1a", border_color="#2a2a2a",
            font=ctk.CTkFont(size=12),
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkFrame(self, height=1, fg_color="#222").pack(
            fill="x", padx=24, pady=12
        )

        # Кнопки
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0,20))

        ctk.CTkButton(
            btn_frame, text="Отмена",
            fg_color="#1a1a1a", hover_color="#222",
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame, text="💾 Сохранить",
            fg_color="#7c3aed", hover_color="#6d28d9",
            command=self._save,
        ).pack(side="right")

        # Статус
        self._status = ctk.CTkLabel(
            btn_frame, text="",
            font=ctk.CTkFont(size=11),
            text_color="#4CAF50",
        )
        self._status.pack(side="right", padx=12)

    def _load_values(self):
        """Загрузить текущие значения из .env"""
        if not self._env_path.exists():
            return
        for line in self._env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                key = key.strip()
                if key in self._vars:
                    self._vars[key].set(val.strip())

    def _save(self):
        """Сохранить в .env и применить в os.environ"""
        try:
            # Читаем текущий .env
            lines = []
            existing_keys = set()
            if self._env_path.exists():
                for line in self._env_path.read_text(encoding="utf-8").splitlines():
                    stripped = line.strip()
                    if "=" in stripped and not stripped.startswith("#"):
                        key = stripped.split("=")[0].strip()
                        if key in self._vars:
                            new_val = self._vars[key].get().strip()
                            lines.append(f"{key}={new_val}")
                            existing_keys.add(key)
                            os.environ[key] = new_val
                            continue
                    lines.append(line)

            # Добавить новые ключи которых не было
            for key, var in self._vars.items():
                if key not in existing_keys:
                    val = var.get().strip()
                    if val:
                        lines.append(f"{key}={val}")
                        os.environ[key] = val

            self._env_path.write_text(
                "\n".join(lines), encoding="utf-8"
            )
            self._status.configure(text="✓ Сохранено")
            self.after(2000, lambda: self._status.configure(text=""))

        except Exception as e:
            self._status.configure(
                text=f"Ошибка: {e}", text_color="#f87171"
            )
