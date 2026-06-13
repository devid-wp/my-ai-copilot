# ui/model_selector.py
"""Дропдаун выбора провайдера и модели."""

import customtkinter as ctk


PROVIDERS = ["gemini", "nvidia", "ollama"]


class ModelSelector(ctk.CTkFrame):
    def __init__(self, parent, provider_manager, on_change_callback):
        super().__init__(parent, fg_color="transparent")
        self.pm = provider_manager
        self.on_change = on_change_callback
        self._build()

    def _build(self):
        # Выбор провайдера
        self.provider_var = ctk.StringVar(value="gemini")
        ctk.CTkOptionMenu(
            self,
            values=PROVIDERS,
            variable=self.provider_var,
            width=90, height=30,
            command=self._on_provider_change,
        ).pack(side="left", padx=(0, 4))

        # Выбор модели
        self.model_var = ctk.StringVar(value="gemini-2.0-flash")
        self.model_menu = ctk.CTkOptionMenu(
            self,
            values=["gemini-2.0-flash", "gemini-2.5-pro"],
            variable=self.model_var,
            width=180, height=30,
            command=self._on_model_change,
        )
        self.model_menu.pack(side="left")

    def _on_provider_change(self, provider: str):
        models = self.pm.get_available_models(provider)
        if not models:
            models = ["(нет моделей)"]
        self.model_menu.configure(values=models)
        self.model_var.set(models[0])
        self.on_change(provider, models[0])

    def _on_model_change(self, model: str):
        provider = self.provider_var.get()
        self.on_change(provider, model)
