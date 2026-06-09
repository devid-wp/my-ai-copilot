import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.llm_client import NVIDIAClient
from core.diff_applier import apply_diff
from core.context_manager import get_project_context
from ui.screen import draw_header, update_status, clear_screen

# Вставь свой реальный ключ сюда
client = NVIDIAClient("nvapi-...") 

def main():
    clear_screen()
    draw_header()
    while True:
        prompt = input("\n\033[92m[Ты]:\033[0m ")
        if prompt.lower() == "exit": break
        
        update_status("Анализ проекта...")
        context = get_project_context()
        
        update_status("Генерация кода...")
        response = client.ask(prompt, context)
        
        print(f"\n\033[36m[Ответ]:\033[0m\n{response}")
        
        if input("\nПрименить (y/n)? ").lower() == 'y':
            apply_diff("../main.py", response)
            print("Готово!")

if __name__ == "__main__":
    main()