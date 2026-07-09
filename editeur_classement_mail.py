#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from classement_mail_core import (
    OUTPUT_DIR,
    apply_classification_rows,
    ensure_default_files,
    read_csv_rows,
    write_pending_queue,
)


PENDING_FILE = OUTPUT_DIR / "expediteurs_a_traiter.csv"

HTML = """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Classement Mail</title>
  <style>
    :root {
      --bg: #f5efe4;
      --panel: #fffdfa;
      --ink: #2f2417;
      --line: #dacdbb;
      --accent: #b55222;
      --soft: #f7e2d2;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #fff3dc 0, transparent 28%),
        linear-gradient(180deg, #f3ead8 0, var(--bg) 45%, #efe5d2 100%);
    }
    .wrap {
      max-width: 1450px;
      margin: 0 auto;
      padding: 22px;
    }
    .hero, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 8px 30px rgba(69, 46, 23, 0.08);
    }
    .hero {
      padding: 22px;
      margin-bottom: 18px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: clamp(28px, 4vw, 44px);
    }
    p {
      margin: 0;
      line-height: 1.45;
    }
    .topbar {
      display: grid;
      gap: 14px;
      grid-template-columns: 1.2fr 1fr 1fr auto auto;
      margin-bottom: 18px;
    }
    .panel {
      padding: 14px;
    }
    .stat {
      font-size: 14px;
      color: #5e4d38;
    }
    select, button {
      width: 100%;
      min-height: 42px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: white;
      color: var(--ink);
      padding: 10px 12px;
      font: inherit;
    }
    button {
      cursor: pointer;
      border: none;
      background: linear-gradient(180deg, #bd5a28 0, var(--accent) 100%);
      color: #fff7f0;
      font-weight: 600;
    }
    button.secondary {
      background: var(--soft);
      color: var(--ink);
      border: 1px solid #ddb08f;
    }
    .table-wrap {
      overflow: auto;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: white;
    }
    table {
      width: 100%;
      min-width: 960px;
      border-collapse: collapse;
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid #eadfce;
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }
    th {
      position: sticky;
      top: 0;
      background: #f7efdf;
      z-index: 1;
    }
    td select, td input {
      width: 100%;
      min-height: 36px;
      border-radius: 10px;
      border: 1px solid #d7c7ad;
      padding: 8px 10px;
      font: inherit;
    }
    .message {
      margin-top: 14px;
      min-height: 22px;
      font-size: 14px;
      color: #5f4d39;
    }
    .accent {
      color: var(--accent);
      font-weight: 700;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Classement Mail</h1>
      <p>Cette interface ouvre le fichier <code>expediteurs_a_traiter.csv</code>, vous laisse classer rapidement les lignes, puis met a jour directement les trois listes de reference sur votre Mac.</p>
    </section>

    <section class="topbar">
      <div class="panel">
        <div class="stat" id="stats">Chargement...</div>
      </div>
      <div class="panel">
        <select id="bulkStatus">
          <option value="">Statut global</option>
          <option value="protege">protege</option>
          <option value="bloque">bloque</option>
          <option value="nettoyer_sans_bloquer">nettoyer_sans_bloquer</option>
          <option value="inconnu">inconnu</option>
        </select>
      </div>
      <div class="panel">
        <select id="bulkAction">
          <option value="">Action globale</option>
          <option value="conserver">conserver</option>
          <option value="nettoyer">nettoyer</option>
          <option value="revoir">revoir</option>
        </select>
      </div>
      <div class="panel">
        <button class="secondary" id="reloadButton">Recharger</button>
      </div>
      <div class="panel">
        <button id="saveButton">Valider et enregistrer</button>
      </div>
    </section>

    <section class="table-wrap">
      <table id="table">
        <thead></thead>
        <tbody></tbody>
      </table>
    </section>

    <div class="message" id="message"></div>
  </div>

  <script>
    const headers = ["nom", "adresse", "nombre_de_mails", "statut", "action_recommandee"];
    const statusOptions = ["protege", "bloque", "nettoyer_sans_bloquer", "inconnu"];
    const actionOptions = ["conserver", "nettoyer", "revoir"];

    const thead = document.querySelector("#table thead");
    const tbody = document.querySelector("#table tbody");
    const stats = document.getElementById("stats");
    const message = document.getElementById("message");
    const saveButton = document.getElementById("saveButton");
    const reloadButton = document.getElementById("reloadButton");
    const bulkStatus = document.getElementById("bulkStatus");
    const bulkAction = document.getElementById("bulkAction");

    let rows = [];

    reloadButton.addEventListener("click", loadRows);
    saveButton.addEventListener("click", saveRows);
    bulkStatus.addEventListener("change", () => applyBulk("statut", bulkStatus.value));
    bulkAction.addEventListener("change", () => applyBulk("action_recommandee", bulkAction.value));

    loadRows();

    async function loadRows() {
      message.textContent = "Chargement...";
      const response = await fetch("/api/pending");
      const payload = await response.json();
      rows = payload.rows || [];
      render();
      message.textContent = rows.length ? "Fichier charge." : "Aucune ligne a traiter actuellement.";
    }

    function render() {
      stats.innerHTML = `<span class="accent">${rows.length}</span> ligne(s) a traiter.`;
      thead.innerHTML = "";
      tbody.innerHTML = "";

      const headRow = document.createElement("tr");
      headers.forEach((header) => {
        const th = document.createElement("th");
        th.textContent = header;
        headRow.appendChild(th);
      });
      thead.appendChild(headRow);

      rows.forEach((row, rowIndex) => {
        const tr = document.createElement("tr");
        headers.forEach((header) => {
          const td = document.createElement("td");
          if (header === "statut") {
            td.appendChild(buildSelect(statusOptions, row[header] || "", (value) => {
              rows[rowIndex][header] = value;
              rows[rowIndex]["action_recommandee"] = recommendedAction(value, rows[rowIndex]["action_recommandee"]);
              render();
            }));
          } else if (header === "action_recommandee") {
            td.appendChild(buildSelect(actionOptions, row[header] || "", (value) => {
              rows[rowIndex][header] = value;
            }));
          } else {
            const input = document.createElement("input");
            input.type = "text";
            input.value = row[header] || "";
            input.addEventListener("input", (event) => {
              rows[rowIndex][header] = event.target.value;
            });
            td.appendChild(input);
          }
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
    }

    function buildSelect(options, currentValue, onChange) {
      const select = document.createElement("select");
      options.forEach((optionValue) => {
        const option = document.createElement("option");
        option.value = optionValue;
        option.textContent = optionValue;
        if (optionValue === currentValue) option.selected = true;
        select.appendChild(option);
      });
      if (!options.includes(currentValue)) {
        const option = document.createElement("option");
        option.value = currentValue;
        option.textContent = currentValue;
        option.selected = true;
        select.appendChild(option);
      }
      select.addEventListener("change", (event) => onChange(event.target.value));
      return select;
    }

    function recommendedAction(status, currentValue) {
      if (status === "protege") return "conserver";
      if (status === "bloque" || status === "nettoyer_sans_bloquer") return "nettoyer";
      if (status === "inconnu") return "revoir";
      return currentValue || "";
    }

    function applyBulk(column, value) {
      if (!value) return;
      rows = rows.map((row) => {
        const next = { ...row, [column]: value };
        if (column === "statut") {
          next.action_recommandee = recommendedAction(value, next.action_recommandee);
        }
        return next;
      });
      render();
    }

    async function saveRows() {
      message.textContent = "Enregistrement en cours...";
      const response = await fetch("/api/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rows }),
      });
      const payload = await response.json();
      rows = payload.pending_rows || [];
      render();
      message.innerHTML =
        `Enregistre. Proteges: <span class="accent">${payload.summary.moved_counts.protege}</span>, ` +
        `bloques: <span class="accent">${payload.summary.moved_counts.bloque}</span>, ` +
        `nettoyer sans bloquer: <span class="accent">${payload.summary.moved_counts.nettoyer_sans_bloquer}</span>.`;
    }
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    shutdown_after_save = False

    def do_GET(self) -> None:
        if self.path == "/":
            self._send_html(HTML)
            return

        if self.path == "/api/pending":
            self._send_json({"rows": read_csv_rows(PENDING_FILE)})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Page introuvable")

    def do_POST(self) -> None:
        if self.path != "/api/save":
            self.send_error(HTTPStatus.NOT_FOUND, "Page introuvable")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        rows = payload.get("rows", [])
        summary = apply_classification_rows(rows)
        pending_rows = [row for row in rows if (row.get("statut") or "").strip() == "inconnu"]
        write_pending_queue(PENDING_FILE, pending_rows)
        self._send_json({"summary": summary, "pending_rows": pending_rows})

        if self.shutdown_after_save:
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args) -> None:
        return

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Editeur local de classement Mail")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Ferme automatiquement le serveur apres le premier enregistrement.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_default_files()
    Handler.shutdown_after_save = args.once
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host, port = server.server_address
    url = f"http://{host}:{port}/"

    print("Editeur de classement lance.")
    print(f"Ouvrez cette adresse si le navigateur ne se lance pas : {url}")
    if args.once:
        print("Le serveur se fermera automatiquement apres la validation.")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nArret du serveur.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
