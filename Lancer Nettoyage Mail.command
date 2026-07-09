#!/bin/zsh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PYTHON_BIN="$(command -v python3)"

if [[ -z "$PYTHON_BIN" ]]; then
  osascript -e 'display alert "Python introuvable" message "python3 n\u2019est pas disponible sur ce Mac. Ouvrez Terminal puis installez Python 3 avant de relancer Nettoyage Mail." as critical'
  exit 1
fi

"$PYTHON_BIN" "$SCRIPT_DIR/lanceur_nettoyage_mail.py"
STATUS=$?

if [[ $STATUS -ne 0 ]]; then
  osascript -e 'display alert "Nettoyage Mail" message "Le lanceur s\u2019est arrêt\u00e9 avec une erreur. Si le projet vient d\u2019un zip GitHub, retirez d\u2019abord la quarantaine du dossier depuis Terminal."'
fi

exit $STATUS
