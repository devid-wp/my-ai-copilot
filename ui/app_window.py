# ui/app_window.py
"""Главное окно приложения Citadex."""

import customtkinter as ctk
import threading
from ui.style import *
import os
from pathlib import Path


class AppWindow(ctk.CTk):
    def __init__(self, project_root: str = "."):
        super().__init__()

        self._load_icon()

        self.project_root = os.path.abspath(project_root)

        # Тема OpenAI Codex: черный фон
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=BG_WINDOW)

        self.title("Citadex")
        self.geometry("1100x700")
        self.minsize(800, 500)

        # Инициализация провайдера (загрузка контекста в фоне)
        from core.provider_manager import ProviderManager
        self.provider = ProviderManager(system_prompt="Загрузка контекста проекта...")
        self.provider.switch("gemini", "gemini-2.0-flash", "gemini-2.5-pro")

        self._build_ui()

        self.after(100, self._load_project_context_async)

    def _build_ui(self):
        # Верхняя панель (OpenAI Codex style)
        self.top_bar = ctk.CTkFrame(
            self,
            height=TOP_BAR_HEIGHT,
            corner_radius=0,
            fg_color=TOP_BAR_BG,
            border_width=0,
        )
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)
        self._build_top_bar()

        # Основная область чата (занимает весь экран)
        from ui.chat_widget import ChatWidget
        self.chat = ChatWidget(self, self._on_send)
        self.chat.pack(fill="both", expand=True, padx=0, pady=0)

        # Боковая панель
        from ui.side_menu import SideMenu
        self.side_menu = SideMenu(self, self.provider, self._on_model_change)

    def _build_top_bar(self):
        # Настройка сетки для идеального центрирования
        self.top_bar.grid_columnconfigure(0, weight=1, uniform="top_cols")
        self.top_bar.grid_columnconfigure(1, weight=1, uniform="top_cols")
        self.top_bar.grid_columnconfigure(2, weight=1, uniform="top_cols")
        self.top_bar.grid_rowconfigure(0, weight=1)

        # 1. Левая секция (Логотип Citadex)
        left_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w", padx=16)
        
        self.menu_btn = ctk.CTkButton(
            left_frame,
            text="⬡",
            width=40, height=40,
            fg_color="transparent",
            hover_color="#1e1e1e",
            text_color="#7c3aed",
            font=ctk.CTkFont(size=16),
            command=self._toggle_side_menu,
        )
        self.menu_btn.pack(side="left", padx=(8,4))

        ctk.CTkLabel(
            left_frame, text="Citadex",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#ffffff"
        ).pack(side="left", padx=4)

        # 2. Центральная секция (пусто)
        center_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        center_frame.grid(row=0, column=1, sticky="ew")

        # 3. Правая секция (Статус и кнопка New chat)
        right_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        right_frame.grid(row=0, column=2, sticky="e", padx=16)

        # Точка статуса
        self.status_dot = ctk.CTkLabel(
            right_frame, text="●", text_color="#22c55e",
            font=ctk.CTkFont(size=14)
        )
        self.status_dot.pack(side="left", padx=(0, 4))

        # Имя модели
        current_model_display = self.provider.current_model.split('/')[-1]
        self.status_text = ctk.CTkLabel(
            right_frame, text=current_model_display, text_color="#888888",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.status_text.pack(side="left", padx=(0, 16))

        # Кнопка New chat
        ctk.CTkButton(
            right_frame, text="New chat", width=80, height=28,
            fg_color="#1a1a1a", hover_color="#262626", text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._on_clear
        ).pack(side="left")

        # Кнопка настройки API ключей
        ctk.CTkButton(
            self.top_bar, text="⚙", width=36, height=36,
            fg_color="transparent", hover_color="#1e1e1e",
            font=ctk.CTkFont(size=14),
            command=self._open_settings,
        ).pack(side="right", padx=4)

    def _toggle_side_menu(self):
        self.side_menu.toggle()

    def _on_send(self, text: str):
        """Вызывается при отправке сообщения."""
        if not text.strip():
            return
        self.chat.add_message("user", text)
        self.chat.set_input_enabled(False)

        def stream_thread():
            client = self.provider.get_client()
            self.chat.start_ai_message()
            error_occurred = False
            try:
                for token in client.ask_stream(text):
                    self.chat.append_ai_token(token)
            except Exception as e:
                err = str(e)
                if "429" in err or "quota" in err or "RESOURCE_EXHAUSTED" in err:
                    msg = "Лимит Gemini исчерпан. Переключитесь на NVIDIA или подождите 1 минуту."
                else:
                    msg = err.split("\n")[0][:120]
                self.chat.add_error(msg)
                error_occurred = True
            finally:
                if not error_occurred:
                    self.after(0, self.chat.finish_ai_message)
                self.after(0, lambda: self.chat.set_input_enabled(True))

        threading.Thread(target=stream_thread, daemon=True).start()

    def _on_model_change(self, provider: str, model: str):
        """Смена модели через pill selector."""
        ok = self.provider.switch(provider, model)
        display_model = model.split('/')[-1]
        if ok:
            self.status_dot.configure(text_color="#22c55e")
            self.status_text.configure(text=display_model)
        else:
            self.status_dot.configure(text_color="#ef4444")
            self.status_text.configure(text="Ошибка")

    def _on_clear(self):
        self.provider.reset_history()
        self.chat.clear()

    def _load_project_context_async(self):
        """Асинхронная загрузка контекста проекта."""
        def load_thread():
            try:
                from core.prompts import SYSTEM_PROMPT_TEMPLATE
                from core.context_manager import get_project_context, get_git_log

                project_ctx = get_project_context(self.project_root)
                git_log = get_git_log(self.project_root)
                system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                    project_root=self.project_root,
                    project_tree=project_ctx,
                    current_user="dev",
                    team_activity="— нет данных —",
                    git_log=git_log or "— git log недоступен —",
                )
                self.provider.system_prompt = system_prompt
                if self.provider._client:
                    self.provider._client.system_prompt = system_prompt
                print("[AppWindow] Project context loaded asynchronously.")
            except Exception as e:
                print(f"[AppWindow] Failed to load project context asynchronously: {e}")

        threading.Thread(target=load_thread, daemon=True).start()

    def _open_settings(self):
        from ui.settings_window import SettingsWindow
        SettingsWindow(self)

    def _load_icon(self):
        import sys, os
        from PIL import Image, ImageTk
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            if sys.platform == "win32":
                ico = os.path.join(base, "icon.ico")
                if os.path.exists(ico):
                    self.after(200, lambda: self.iconbitmap(ico))
            else:
                # Linux/Mac — использовать PNG через wm_iconphoto
                png = os.path.join(base, "icon.png")
                if os.path.exists(png):
                    img = Image.open(png).resize((32,32))
                    self._icon_photo = ImageTk.PhotoImage(img)
                    self.after(200, lambda: self.wm_iconphoto(True, self._icon_photo))
        except Exception as e:
            print(f"Icon: {e}")

