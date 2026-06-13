# Citadex — Установка

## Windows
```powershell
cd D:\copilot\my-ai-copilot
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File install_alias.ps1
# Затем в новом терминале:
Citadex
```

## Linux / Ubuntu
```bash
cd ~/my-ai-copilot
pip3 install -r requirements.txt
bash install_alias.sh
source ~/.bashrc
# Затем:
Citadex
```

## Mac
```bash
cd ~/my-ai-copilot
pip3 install -r requirements.txt
bash install_alias.sh
source ~/.zshrc
Citadex
```

## Ollama (локальные модели, бесплатно)
```bash
# Установить Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Скачать модель
ollama pull llama3.2        # лёгкая, быстрая
ollama pull codellama       # для кода

# Запустить
ollama serve

# Citadex автоматически найдёт Ollama
Citadex
```

## API ключи
- Gemini (бесплатно): https://aistudio.google.com/apikey
- NVIDIA (бесплатно): https://build.nvidia.com

После запуска Citadex нажми ⚙ и вставь ключи в настройках.
