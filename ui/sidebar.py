# ui/sidebar.py
"""Левая панель с файловым деревом проекта."""

import customtkinter as ctk
import os


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, project_root: str, on_file_click):
        super().__init__(parent, width=220, corner_radius=8)
        self.pack_propagate(False)
        self.project_root = project_root
        self.on_file_click = on_file_click
        self._build()

    def _build(self):
        # Заголовок
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=6, pady=(6, 0))

        ctk.CTkLabel(
            header, text="📁 Проект",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header, text="↻", width=28, height=28,
            command=self.refresh,
        ).pack(side="right")

        # Поиск
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *_: self.refresh())
        ctk.CTkEntry(
            self, placeholder_text="Поиск...",
            textvariable=self.search_var,
            height=28,
        ).pack(fill="x", padx=6, pady=4)

        # Список файлов
        self.scrollframe = ctk.CTkScrollableFrame(self, corner_radius=6)
        self.scrollframe.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.refresh()

    def refresh(self):
        # Очистить
        for w in self.scrollframe.winfo_children():
            w.destroy()

        query = self.search_var.get().lower()
        skip = {'.git', '__pycache__', 'node_modules', 'venv', 'logs', '~', '.pytest_cache'}

        files = []
        for root, dirs, filenames in os.walk(self.project_root):
            dirs[:] = sorted([d for d in dirs if d not in skip and not d.startswith('.')])
            rel_root = os.path.relpath(root, self.project_root)

            for fname in sorted(filenames):
                rel_path = os.path.join(rel_root, fname) if rel_root != '.' else fname
                if query and query not in rel_path.lower():
                    continue
                files.append((rel_path, os.path.join(root, fname)))

        for rel_path, abs_path in files[:150]:
            # Иконка по расширению
            ext = os.path.splitext(rel_path)[1]
            icon = {"py": "🐍", "md": "📝", "json": "📋",
                    "txt": "📄", "env": "🔑", "bat": "⚙"}.get(ext.lstrip('.'), "📄")

            btn = ctk.CTkButton(
                self.scrollframe,
                text=f"{icon} {rel_path}",
                anchor="w",
                height=26,
                fg_color="transparent",
                hover_color=("#e0e0e0", "#333"),
                font=ctk.CTkFont(size=11),
                command=lambda p=abs_path: self.on_file_click(p),
            )
            btn.pack(fill="x", pady=1)
