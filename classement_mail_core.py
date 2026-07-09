#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import OrderedDict
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
MASTER_FILES = {
    "protege": PROJECT_DIR / "expediteurs_proteges.csv",
    "bloque": PROJECT_DIR / "expediteurs_bloques.csv",
    "nettoyer_sans_bloquer": PROJECT_DIR / "expediteurs_nettoyer_sans_bloquer.csv",
}

OUTPUT_STATUS_BY_LIST = {
    "protege": "proteges",
    "bloque": "bloques",
    "nettoyer_sans_bloquer": "nettoyer_sans_bloquer",
}

MASTER_HEADER = ["nom", "adresse", "nombre_de_mails", "statut", "commentaire"]
PENDING_HEADER = ["nom", "adresse", "nombre_de_mails", "statut", "action_recommandee"]
KNOWN_STATUSES = {"protege", "bloque", "nettoyer_sans_bloquer", "inconnu", ""}


def normalize_address(address: str) -> str:
    return address.strip().strip('"').lower()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        return list(reader)


def write_csv_rows(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in header})


def ensure_default_files() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in MASTER_FILES.values():
        if not path.exists():
            write_csv_rows(path, MASTER_HEADER, [])


def read_master_entries(path: Path) -> OrderedDict[str, dict[str, str]]:
    entries: OrderedDict[str, dict[str, str]] = OrderedDict()
    for row in read_csv_rows(path):
        address = normalize_address(row.get("adresse", ""))
        if not address:
            continue
        entries[address] = {
            "nom": (row.get("nom") or "").strip(),
            "adresse": address,
            "nombre_de_mails": (row.get("nombre_de_mails") or "").strip(),
            "statut": (row.get("statut") or "").strip(),
            "commentaire": (row.get("commentaire") or "").strip(),
        }
    return entries


def write_master_entries(path: Path, entries: OrderedDict[str, dict[str, str]]) -> None:
    write_csv_rows(path, MASTER_HEADER, list(entries.values()))


def build_master_row(import_row: dict[str, str], destination_status: str, previous_comment: str) -> dict[str, str]:
    return {
        "nom": (import_row.get("nom") or "").strip(),
        "adresse": normalize_address(import_row.get("adresse", "")),
        "nombre_de_mails": (import_row.get("nombre_de_mails") or "").strip(),
        "statut": OUTPUT_STATUS_BY_LIST[destination_status],
        "commentaire": previous_comment,
    }


def sort_entries(entries: OrderedDict[str, dict[str, str]]) -> OrderedDict[str, dict[str, str]]:
    return OrderedDict(sorted(entries.items(), key=lambda item: ((item[1].get("nom") or "").lower(), item[0])))


def recommended_action_from_status(status: str) -> str:
    if status == "protege":
        return "conserver"
    if status in {"bloque", "nettoyer_sans_bloquer"}:
        return "nettoyer"
    return "revoir"


def keep_pending_row(row: dict[str, str]) -> bool:
    return (row.get("statut") or "").strip().lower() == "inconnu"


def normalize_pending_row(row: dict[str, str]) -> dict[str, str]:
    status = (row.get("statut") or "").strip().lower()
    return {
        "nom": (row.get("nom") or "").strip(),
        "adresse": normalize_address(row.get("adresse", "")),
        "nombre_de_mails": (row.get("nombre_de_mails") or "").strip(),
        "statut": status,
        "action_recommandee": (row.get("action_recommandee") or recommended_action_from_status(status)).strip(),
    }


def apply_classification_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    masters = {status: read_master_entries(path) for status, path in MASTER_FILES.items()}

    imported_count = 0
    moved_counts = {key: 0 for key in MASTER_FILES}
    removed_to_unknown = 0

    for raw_row in rows:
        row = normalize_pending_row(raw_row)
        address = row["adresse"]
        status = row["statut"]
        if not address or status not in KNOWN_STATUSES:
            continue

        imported_count += 1
        previous_comment = ""

        for entries in masters.values():
            existing = entries.pop(address, None)
            if existing and not previous_comment:
                previous_comment = existing.get("commentaire", "")

        if status in MASTER_FILES:
            masters[status][address] = build_master_row(row, status, previous_comment)
            moved_counts[status] += 1
        elif status == "inconnu":
            removed_to_unknown += 1

    for status, path in MASTER_FILES.items():
        write_master_entries(path, sort_entries(masters[status]))

    return {
        "imported_count": imported_count,
        "moved_counts": moved_counts,
        "removed_to_unknown": removed_to_unknown,
    }


def write_pending_queue(path: Path, rows: list[dict[str, str]]) -> None:
    normalized_rows = [normalize_pending_row(row) for row in rows if keep_pending_row(row)]
    write_csv_rows(path, PENDING_HEADER, normalized_rows)


ensure_default_files()
