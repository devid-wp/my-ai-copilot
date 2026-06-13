import customtkinter as ctk

class SideMenu(ctk.CTkFrame):
    WIDTH = 240

    def __init__(self, app_window, provider_manager, on_change):
        super().__init__(
            app_window,
            width=self.WIDTH,
            height=600,
            fg_color="#111111",
            corner_radius=0,
        )
        self._app = app_window
        self._visible = False
        self._build(provider_manager, on_change)

    def _build(self, pm, on_change):
        # Заголовок
        ctk.CTkLabel(
            self, text="Модели",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#888",
        ).pack(anchor="w", padx=16, pady=(16,8))

        groups = {
            "GEMINI": [
                ("gemini-2.0-flash", "free", "gemini", "gemini-2.0-flash"),
                ("gemini-2.5-pro", "25/day", "gemini", "gemini-2.5-pro"),
            ],
            "NVIDIA": [
                ("llama-3.1-8b", "fast", "nvidia", "meta/llama-3.1-8b-instruct"),
                ("llama-3.3-70b", "smart", "nvidia", "meta/llama-3.3-70b-instruct"),
            ],
        }

        for group, items in groups.items():
            # Разделитель с названием группы
            sep_frame = ctk.CTkFrame(self, fg_color="transparent")
            sep_frame.pack(fill="x", padx=12, pady=(8,2))
            ctk.CTkLabel(
                sep_frame, text=group,
                font=ctk.CTkFont(size=10),
                text_color="#444",
            ).pack(side="left")
            ctk.CTkFrame(sep_frame, height=1, fg_color="#222").pack(
                side="left", fill="x", expand=True, padx=(6,0)
            )

            for label, badge, provider, model in items:
                row = ctk.CTkFrame(self, fg_color="transparent", height=36)
                row.pack(fill="x", padx=8, pady=1)
                row.pack_propagate(False)

                ctk.CTkButton(
                    row,
                    text=label,
                    anchor="w",
                    fg_color="transparent",
                    hover_color="#1e1e1e",
                    text_color="white",
                    font=ctk.CTkFont(size=12),
                    height=34,
                    command=lambda p=provider, m=model: (
                        on_change(p, m), self.hide()
                    ),
                ).pack(side="left", fill="x", expand=True)

                ctk.CTkLabel(
                    row,
                    text=badge,
                    font=ctk.CTkFont(size=9),
                    text_color="#555",
                ).pack(side="right", padx=8)

        # Ollama секция
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=1)
            models = [m["name"] for m in r.json().get("models", [])]
        except:
            models = []

        sep_frame2 = ctk.CTkFrame(self, fg_color="transparent")
        sep_frame2.pack(fill="x", padx=12, pady=(8,2))
        ctk.CTkLabel(sep_frame2, text="OLLAMA",
                     font=ctk.CTkFont(size=10), text_color="#444").pack(side="left")
        ctk.CTkFrame(sep_frame2, height=1, fg_color="#222").pack(
            side="left", fill="x", expand=True, padx=(6,0))

        if models:
            for m in models:
                ctk.CTkButton(
                    self, text=m, anchor="w",
                    fg_color="transparent", hover_color="#1e1e1e",
                    text_color="white", font=ctk.CTkFont(size=12), height=34,
                    command=lambda mod=m: (on_change("ollama", mod), self.hide()),
                ).pack(fill="x", padx=8, pady=1)
        else:
            ctk.CTkLabel(self, text="ollama не запущен",
                         text_color="#444", font=ctk.CTkFont(size=11)).pack(
                anchor="w", padx=20, pady=4)

        # Нижний разделитель — настройки
        ctk.CTkFrame(self, height=1, fg_color="#1e1e1e").pack(
            fill="x", side="bottom", pady=(0,0))
        ctk.CTkButton(
            self, text="⚙ Настройки API ключей",
            anchor="w", fg_color="transparent",
            hover_color="#1e1e1e", text_color="#666",
            font=ctk.CTkFont(size=11), height=36,
            command=lambda: print("TODO: settings"),
        ).pack(side="bottom", fill="x", padx=8, pady=4)

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def show(self):
        self._app.update_idletasks()
        h = self._app.winfo_height() - 44
        self.configure(width=self.WIDTH, height=h)
        self.place(x=0, y=44)
        self.lift()
        self._visible = True
        self._app.bind("<Button-1>", self._on_outside_click, add="+")

    def hide(self):
        self.place_forget()
        self._visible = False

    def _on_outside_click(self, event):
        if not self._visible:
            return
        mx = self.winfo_rootx()
        my = self.winfo_rooty()
        mw = self.winfo_width()
        mh = self.winfo_height()
        if not (mx <= event.x_root <= mx+mw and my <= event.y_root <= my+mh):
            self.hide()
