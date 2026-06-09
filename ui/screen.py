# ui/screen.py
import sys

def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def draw_header():
    print("\033[96m" + "="*60)
    print("   🚀 NVIDIA VIBE-CODING ENGINE | READY FOR TASKS")
    print("="*60 + "\033[0m")

def update_status(status):
    print(f"\033[93m[Статус]:\033[0m {status}")