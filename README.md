# Citadex

Citadex — безопасный CLI AI-ассистент для работы с локальными проектами. Он умеет отвечать в режиме чата и, при явном включении агентного режима, читать и изменять файлы или запускать ограниченный набор команд.

## Возможности

- NVIDIA NIM, Google Gemini и локальный Ollama.
- Потоковый вывод в терминал.
- Автоматический выбор chat/code модели.
- Контекст структуры проекта и Git.
- Native tool calls без текстовых псевдокоманд.
- Защита корня проекта, `.git` и `.env`.
- Подтверждение каждого изменения и запуска команды.
- Сохранение истории сессии в `logs/session.json`.

## Установка

Требуется Python 3.10–3.13.

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

Добавьте ключ выбранного провайдера в `.env`. Для Ollama API-ключ не требуется.

## Запуск

Обычный чат:

```bash
citadex --provider nvidia --project .
```

Агентный режим:

```bash
citadex --agent --project .
```

Одна задача:

```bash
citadex --agent --oneshot "проверь тесты и исправь ошибку" --project .
```

По умолчанию каждое изменение и каждая команда требуют подтверждения. `--yes` отключает подтверждения и должен использоваться только в доверенной автоматизации.

Полезные флаги:

```text
--provider nvidia|gemini|ollama
--model MODEL
--agent
--oneshot PROMPT
--project PATH
--max-steps N
--yes
```

Команды интерактивной сессии: `!help`, `!clear`, `exit`.

## Безопасность и приватность

Облачные провайдеры получают выбранный контекст исходного кода. Не используйте их для закрытых проектов без разрешения владельца данных. Citadex исключает `.env`, но автоматическая фильтрация не заменяет проверку пользователя.

Командный runner не использует shell, запрещает chaining, redirects и inline interpreter code. Это снижает риск, но агент всё равно способен менять проект — внимательно читайте approval prompt.

Уязвимости сообщайте по инструкции в [SECURITY.md](SECURITY.md).

## Разработка

```bash
python -m pytest -q
python -m ruff check .
python -m mypy core main.py
python -m build
```

## Лицензия

MIT — см. [LICENSE](LICENSE).
