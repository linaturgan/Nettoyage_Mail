#!/bin/zsh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
python3 "$SCRIPT_DIR/lanceur_nettoyage_mail.py"

