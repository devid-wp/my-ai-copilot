# ui/chat_widget.py
import customtkinter as ctk
import tkinter as tk


class ChatWidget(ctk.CTkFrame):
    def __init__(self, parent, on_send):
        super().__init__(parent, fg_color="#0a0a0a", corner_radius=0)
        self.on_send = on_send
        self._current_bubble = None
        self._build()

    def _build(self):
        # Область сообщений
        self.canvas = tk.Canvas(self, bg="#0a0a0a", highlightthickness=0)
        self.scrollbar = ctk.CTkScrollbar(self, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.messages_frame = ctk.CTkFrame(self.canvas, fg_color="#0a0a0a")
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.messages_frame, anchor="nw"
        )

        self.messages_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(
            int(-1*(e.delta/120)), "units"))

        # Инпут
        self._build_input()

    def _on_frame_configure(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self.canvas_window, width=e.width)

    def _build_input(self):
        input_outer = ctk.CTkFrame(
            self.master, fg_color="#0a0a0a", corner_radius=0
        )
        input_outer.pack(side="bottom", fill="x", padx=20, pady=(8,4))

        input_frame = ctk.CTkFrame(
            input_outer, fg_color="#111111",
            corner_radius=12,
            border_width=1, border_color="#2a2a2a",
        )
        input_frame.pack(fill="x")

        self.input_box = ctk.CTkTextbox(
            input_frame,
            height=44,
            fg_color="transparent",
            border_width=0,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            wrap="word",
        )
        self.input_box.pack(side="left", fill="x", expand=True, padx=(12,4), pady=6)
        self.input_box.insert("1.0", "")
        self.input_box._textbox.configure(insertbackground="white")

        # Placeholder
        self._placeholder = "Сообщение Citadex..."
        self._placeholder_active = True
        self.input_box.insert("1.0", self._placeholder)
        self.input_box.configure(text_color="#555")
        self.input_box.bind("<FocusIn>", self._on_focus_in)
        self.input_box.bind("<FocusOut>", self._on_focus_out)
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)

        self.send_btn = ctk.CTkButton(
            input_frame, text="↑", width=36, height=36,
            corner_radius=18,
            fg_color="#7c3aed", hover_color="#6d28d9",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._send,
        )
        self.send_btn.pack(side="right", padx=(4,8), pady=6)

        # Подсказка
        ctk.CTkLabel(
            input_outer,
            text="Enter — отправить  •  Shift+Enter — новая строка",
            font=ctk.CTkFont(size=10),
            text_color="#333",
        ).pack(pady=(2,0))

    def _on_focus_in(self, e):
        if self._placeholder_active:
            self.input_box.delete("1.0", "end")
            self.input_box.configure(text_color="white")
            self._placeholder_active = False

    def _on_focus_out(self, e):
        if not self.input_box.get("1.0", "end").strip():
            self.input_box.insert("1.0", self._placeholder)
            self.input_box.configure(text_color="#555")
            self._placeholder_active = True

    def _on_enter(self, event):
        if not event.state & 0x1:
            self._send()
            return "break"

    def _send(self):
        if self._placeholder_active:
            return
        text = self.input_box.get("1.0", "end").strip()
        if text:
            self.input_box.delete("1.0", "end")
            self._placeholder_active = False
            self.on_send(text)

    def add_message(self, role, text):
        bubble = MessageBubble(self.messages_frame, role=role, text=text)
        bubble.pack(
            anchor="e" if role == "user" else "w",
            padx=16, pady=6,
            fill="none",
        )
        self._scroll_bottom()

    def start_ai_message(self):
        self._current_bubble = StreamingBubble(self.messages_frame)
        self._current_bubble.pack(anchor="w", padx=16, pady=6, fill="none")
        self._scroll_bottom()

    def append_ai_token(self, token):
        if self._current_bubble:
            self._current_bubble.append(token)
            self._scroll_bottom()

    def finish_ai_message(self):
        if self._current_bubble:
            self._current_bubble.finish()
            self._current_bubble = None

    def add_error(self, text):
        f = ctk.CTkFrame(
            self.messages_frame,
            fg_color="#1a0a0a",
            corner_radius=8,
            border_width=1,
            border_color="#7f1d1d",
            width=1, height=1,
        )
        f.pack(anchor="w", padx=16, pady=6)
        ctk.CTkLabel(
            f, text=f"⚠ {text}",
            text_color="#f87171",
            font=ctk.CTkFont(size=12),
            wraplength=600,
            justify="left",
        ).pack(padx=12, pady=8)

    def set_input_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.input_box.configure(state=state)
        self.send_btn.configure(state=state)

    def clear(self):
        for w in self.messages_frame.winfo_children():
            w.destroy()

    def _scroll_bottom(self):
        self.after(20, lambda: self.canvas.yview_moveto(1.0))


class MessageBubble(ctk.CTkFrame):
    MAX_WIDTH = 680

    def __init__(self, parent, role, text):
        is_user = role == "user"
        bg = "#1e1033" if is_user else "#141414"
        acc = "#7c3aed" if is_user else "#2a2a2a"

        super().__init__(
            parent,
            fg_color=bg,
            corner_radius=12,
        )

        # Цветная полоса слева
        ctk.CTkFrame(
            self, width=3, height=1, fg_color=acc, corner_radius=0
        ).pack(side="left", fill="y")

        # Контент
        content = ctk.CTkFrame(self, fg_color="transparent", width=1, height=1)
        content.pack(side="left", padx=(8,12), pady=(8,8))

        if not is_user:
            ctk.CTkLabel(
                content,
                text="⬡ Citadex",
                font=ctk.CTkFont(size=10),
                text_color="#555",
            ).pack(anchor="w")

        ctk.CTkLabel(
            content,
            text=text,
            wraplength=self.MAX_WIDTH,
            justify="left",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#e0e0e0",
            anchor="w",
        ).pack(anchor="w")

        if is_user:
            ctk.CTkLabel(
                self,
                text="Вы",
                font=ctk.CTkFont(size=10),
                text_color="#555",
            ).pack(side="right", anchor="ne", padx=8, pady=4)


class StreamingBubble(ctk.CTkFrame):
    MAX_WIDTH = 680

    def __init__(self, parent):
        super().__init__(parent, fg_color="#141414", corner_radius=12)
        self._text = ""

        ctk.CTkFrame(
            self, width=3, height=1, fg_color="#2a2a2a", corner_radius=0
        ).pack(side="left", fill="y")

        content = ctk.CTkFrame(self, fg_color="transparent", width=1, height=1)
        content.pack(side="left", padx=(8,12), pady=(8,8))

        ctk.CTkLabel(
            content,
            text="⬡ Citadex",
            font=ctk.CTkFont(size=10),
            text_color="#555",
        ).pack(anchor="w")

        self._label = ctk.CTkLabel(
            content,
            text="▋",
            wraplength=self.MAX_WIDTH,
            justify="left",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#e0e0e0",
            anchor="w",
        )
        self._label.pack(anchor="w")

    def append(self, token):
        self._text += token
        self._label.configure(text=self._text + "▋")

    def finish(self):
        self._label.configure(text=self._text)
