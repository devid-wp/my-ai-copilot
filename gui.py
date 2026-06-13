# gui.py
"""Запуск GUI версии Citadex."""

import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from ui.app_window import AppWindow

if __name__ == "__main__":
    project = sys.argv[1] if len(sys.argv) > 1 else "."
    app = AppWindow(project_root=project)
    app.mainloop()
