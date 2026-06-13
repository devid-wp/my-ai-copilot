#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHELL_RC="$HOME/.bashrc"

# Для zsh
if [ -n "$ZSH_VERSION" ] || [ "$SHELL" = "/bin/zsh" ]; then
    SHELL_RC="$HOME/.zshrc"
fi

LINE="alias Citadex='python3 $SCRIPT_DIR/gui.py'"

if ! grep -q "alias Citadex" "$SHELL_RC"; then
    echo "" >> "$SHELL_RC"
    echo "# Citadex AI Copilot" >> "$SHELL_RC"
    echo "$LINE" >> "$SHELL_RC"
    echo "✅ Алиас Citadex добавлен в $SHELL_RC"
    echo "Перезапусти терминал или выполни: source $SHELL_RC"
else
    echo "Алиас Citadex уже существует в $SHELL_RC"
fi
