#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from classement_mail_core import apply_classification_rows, read_csv_rows


def choose_import_path() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser()

    typed = input("Chemin du CSV modifie a importer : ").strip()
    if not typed:
        raise SystemExit("Aucun chemin fourni.")
    return Path(typed).expanduser()


def main() -> int:
    import_path = choose_import_path()
    if not import_path.exists():
        raise SystemExit(f"Fichier introuvable : {import_path}")

    imported_rows = read_csv_rows(import_path)
    if not imported_rows:
        raise SystemExit("Le fichier importe est vide.")

    summary = apply_classification_rows(imported_rows)

    print("Import termine.")
    print(f"CSV source : {import_path}")
    print(f"Lignes lues : {summary['imported_count']}")
    print(f"Proteges : {summary['moved_counts']['protege']}")
    print(f"Bloques : {summary['moved_counts']['bloque']}")
    print(f"Nettoyer sans bloquer : {summary['moved_counts']['nettoyer_sans_bloquer']}")
    print(f"Retires de toutes les listes via 'inconnu' : {summary['removed_to_unknown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
