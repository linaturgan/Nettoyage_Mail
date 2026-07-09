#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from classement_mail_core import ensure_default_files


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
PLAN_SCRIPT = PROJECT_DIR / "02_plan_cleanup.applescript"
APPLY_SCRIPT = PROJECT_DIR / "03_apply_cleanup.applescript"
JUNK_SCRIPT = PROJECT_DIR / "04_send_blocked_to_junk.applescript"
EDITOR_SCRIPT = PROJECT_DIR / "editeur_classement_mail.py"
PENDING_FILE = OUTPUT_DIR / "expediteurs_a_traiter.csv"
HISTORY_FILE = OUTPUT_DIR / "historique_nettoyage.json"

MONTHS = {
    1: "janvier",
    2: "fevrier",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "aout",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "decembre",
}

HTML = """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pilote Nettoyage Mail</title>
  <style>
    :root {
      --bg: #f4efe7;
      --panel: #fffdf9;
      --ink: #2f2417;
      --line: #dccfbe;
      --accent: #205c47;
      --soft: #e7f2ed;
      --warn: #b55222;
      --gold: #b1842f;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, #fff6de 0, transparent 24%),
        linear-gradient(180deg, #efe7d9 0, var(--bg) 55%, #ebe2d2 100%);
    }
    .wrap {
      max-width: 1240px;
      margin: 0 auto;
      padding: 24px;
    }
    .hero, .panel, .status {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: 0 8px 28px rgba(70, 50, 28, 0.08);
    }
    .hero {
      padding: 24px;
      margin-bottom: 18px;
    }
    h1, h2 {
      margin: 0 0 10px;
    }
    h1 {
      font-size: clamp(30px, 4vw, 46px);
    }
    h2 {
      font-size: clamp(22px, 3vw, 30px);
    }
    p {
      margin: 0;
      line-height: 1.5;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr 1.4fr;
      gap: 16px;
      margin-bottom: 18px;
    }
    .lower-grid {
      display: grid;
      grid-template-columns: 1.3fr 1fr;
      gap: 18px;
    }
    .panel {
      padding: 16px;
    }
    label {
      display: block;
      font-size: 14px;
      margin-bottom: 8px;
      color: #5f513f;
    }
    select, input, button {
      width: 100%;
      min-height: 44px;
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
      color: #fffaf4;
      background: linear-gradient(180deg, #2d7058 0, var(--accent) 100%);
      font-weight: 700;
    }
    button.secondary {
      background: var(--soft);
      color: var(--ink);
      border: 1px solid #bad3c8;
    }
    button.warn {
      background: linear-gradient(180deg, #c66734 0, var(--warn) 100%);
    }
    button.gold {
      background: linear-gradient(180deg, #c39a43 0, var(--gold) 100%);
      color: #fff9f0;
    }
    button:disabled {
      cursor: not-allowed;
      opacity: 0.55;
    }
    .actions {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 14px;
      margin-bottom: 18px;
    }
    .preview-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 14px;
    }
    .status {
      padding: 18px;
      min-height: 180px;
      white-space: pre-line;
      line-height: 1.5;
    }
    .muted {
      color: #6b5a45;
      font-size: 14px;
    }
    .report-path {
      margin-top: 12px;
      font-size: 14px;
      color: #4e4538;
      word-break: break-word;
    }
    .history-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }
    .history-table th,
    .history-table td {
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid #eadfce;
      font-size: 14px;
    }
    .history-table th {
      color: #5f513f;
    }
    @media (max-width: 980px) {
      .grid, .actions, .lower-grid, .preview-actions {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Pilote de Nettoyage Mail</h1>
      <p>Choisissez une annee et un mois, regenerez la liste a traiter, ouvrez l'editeur de classement, puis lancez l'aperçu ou la suppression reelle sans retoucher les scripts.</p>
    </section>

    <section class="grid">
      <div class="panel">
        <label for="year">Annee</label>
        <input id="year" type="number" min="2000" max="2100" value="2026">
      </div>
      <div class="panel">
        <label for="month">Mois</label>
        <select id="month"></select>
      </div>
      <div class="panel">
        <div class="muted">Fichier de travail</div>
        <div style="margin-top: 10px;"><code>output/expediteurs_a_traiter.csv</code></div>
      </div>
    </section>

    <section class="actions">
      <button id="generateButton">1. Generer la liste a traiter</button>
      <button id="editorButton" class="secondary" disabled>2. Ouvrir l'editeur</button>
      <button id="previewButton" class="secondary" disabled>3. Apercu du nettoyage</button>
      <button id="deleteButton" class="warn" disabled>4. Supprimer vraiment</button>
    </section>

    <section class="lower-grid">
      <section class="panel">
        <h2>Apercu du nettoyage</h2>
        <div class="status" id="status">Chargement du pilote...</div>
        <div class="report-path" id="reportPath"></div>
        <div class="preview-actions">
          <button id="reportButton" class="secondary" disabled>Ouvrir le rapport</button>
        </div>
      </section>

      <section class="panel">
        <h2>Historique</h2>
        <p class="muted">Suivi des mois deja traites, avec le nombre d'aperçus, suppressions et envois vers les spams.</p>
        <div id="historyContainer"></div>
      </section>
    </section>
  </div>

  <script>
    const monthSelect = document.getElementById("month");
    const yearInput = document.getElementById("year");
    const generateButton = document.getElementById("generateButton");
    const editorButton = document.getElementById("editorButton");
    const previewButton = document.getElementById("previewButton");
    const deleteButton = document.getElementById("deleteButton");
    const reportButton = document.getElementById("reportButton");
    const statusBox = document.getElementById("status");
    const reportPath = document.getElementById("reportPath");
    const historyContainer = document.getElementById("historyContainer");

    const monthNames = {
      1: "janvier", 2: "fevrier", 3: "mars", 4: "avril",
      5: "mai", 6: "juin", 7: "juillet", 8: "aout",
      9: "septembre", 10: "octobre", 11: "novembre", 12: "decembre"
    };

    for (let month = 1; month <= 12; month += 1) {
      const option = document.createElement("option");
      option.value = String(month);
      option.textContent = `${month} - ${monthNames[month]}`;
      if (month === 7) option.selected = true;
      monthSelect.appendChild(option);
    }

    let state = null;
    let pollTimer = null;

    async function request(path, options = {}) {
      const response = await fetch(path, options);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Erreur inconnue");
      }
      return payload;
    }

    function periodPayload() {
      return {
        year: Number(yearInput.value),
        month: Number(monthSelect.value),
      };
    }

    function renderHistory(rows) {
      if (!rows || rows.length === 0) {
        historyContainer.innerHTML = '<p class="muted">Aucun mois traite pour le moment.</p>';
        return;
      }

      const header = `
        <table class="history-table">
          <thead>
            <tr>
              <th>Mois</th>
              <th>Apercus</th>
              <th>Suppressions</th>
              <th>Spams</th>
            </tr>
          </thead>
          <tbody>
      `;

      const body = rows.map((row) => `
        <tr>
          <td>${escapeHtml(row.label)}</td>
          <td>${row.preview_count}</td>
          <td>${row.delete_count}</td>
          <td>${row.spam_count}</td>
        </tr>
      `).join("");

      historyContainer.innerHTML = `${header}${body}</tbody></table>`;
    }

    function escapeHtml(value) {
      return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }

    function renderState(nextState) {
      state = nextState;
      statusBox.textContent = state.status_text;
      reportPath.textContent = state.last_report_path ? `Dernier rapport : ${state.last_report_path}` : "";
      editorButton.disabled = !(state.can_open_editor);
      previewButton.disabled = !(state.can_preview);
      deleteButton.disabled = !(state.can_delete);
      reportButton.disabled = !(state.can_open_report);
      generateButton.disabled = !!state.busy;
      yearInput.disabled = !!state.busy;
      monthSelect.disabled = !!state.busy;
      renderHistory(state.history_rows || []);
    }

    async function refreshState() {
      const payload = await request("/api/state");
      renderState(payload);
      if (state.editor_running || state.busy) {
        schedulePoll();
      }
    }

    function schedulePoll() {
      if (pollTimer) return;
      pollTimer = setTimeout(async () => {
        pollTimer = null;
        try {
          await refreshState();
        } catch (error) {
          statusBox.textContent = error.message;
        }
      }, 1500);
    }

    async function postAction(path, body = {}) {
      statusBox.textContent = "Traitement en cours...";
      const payload = await request(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      renderState(payload);
      if (payload.editor_running || payload.busy) schedulePoll();
    }

    generateButton.addEventListener("click", async () => {
      try {
        await postAction("/api/generate", periodPayload());
      } catch (error) {
        statusBox.textContent = error.message;
      }
    });

    editorButton.addEventListener("click", async () => {
      try {
        await postAction("/api/open-editor");
      } catch (error) {
        statusBox.textContent = error.message;
      }
    });

    previewButton.addEventListener("click", async () => {
      try {
        await postAction("/api/cleanup", { ...periodPayload(), dry_run: true });
      } catch (error) {
        statusBox.textContent = error.message;
      }
    });

    deleteButton.addEventListener("click", async () => {
      const confirmed = window.confirm("Le nettoyage va supprimer les mails classes comme bloques ou a supprimer. Continuer ?");
      if (!confirmed) return;
      try {
        await postAction("/api/cleanup", { ...periodPayload(), dry_run: false });
      } catch (error) {
        statusBox.textContent = error.message;
      }
    });

    reportButton.addEventListener("click", async () => {
      try {
        await postAction("/api/open-report");
      } catch (error) {
        statusBox.textContent = error.message;
      }
    });

    refreshState().catch((error) => {
      statusBox.textContent = error.message;
    });
  </script>
</body>
</html>
"""


def build_runtime_applescript(source_path: Path, year: int, month: int, dry_run: bool | None = None) -> Path:
    source_text = source_path.read_text(encoding="utf-8")
    source_text = source_text.replace("__PROJECT_DIR__", str(PROJECT_DIR))
    source_text = re.sub(r"set periodYear to \d+", f"set periodYear to {year}", source_text, count=1)
    source_text = re.sub(r"set periodMonthNumber to \d+", f"set periodMonthNumber to {month}", source_text, count=1)
    if dry_run is not None:
        source_text = re.sub(
            r"set dryRun to (true|false)",
            f"set dryRun to {'true' if dry_run else 'false'}",
            source_text,
            count=1,
        )

    runtime_path = Path(tempfile.gettempdir()) / f"{source_path.stem}_{year}_{month}.applescript"
    runtime_path.write_text(source_text, encoding="utf-8")
    return runtime_path


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=True)


def format_command_error(exc: Exception) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        details = [part for part in (stderr, stdout) if part]
        if details:
            return "\n".join(details)
    return str(exc)


def read_history_data() -> dict[str, dict[str, object]]:
    if not HISTORY_FILE.exists():
        return {}
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_history_data(data: dict[str, dict[str, object]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record_history_event(year: int, month: int, event_type: str, report_path: str) -> None:
    key = f"{year:04d}-{month:02d}"
    data = read_history_data()
    entry = data.get(
        key,
        {
            "year": year,
            "month": month,
            "label": f"{MONTHS[month]} {year}",
            "preview_count": 0,
            "delete_count": 0,
            "spam_count": 0,
        },
    )

    if event_type == "preview":
        entry["preview_count"] = int(entry.get("preview_count", 0)) + 1
    elif event_type == "delete":
        entry["delete_count"] = int(entry.get("delete_count", 0)) + 1
    elif event_type == "spam":
        entry["spam_count"] = int(entry.get("spam_count", 0)) + 1

    if report_path:
        entry["last_report_path"] = report_path
    entry["last_event_at"] = datetime.now().isoformat(timespec="seconds")
    data[key] = entry
    write_history_data(data)


def history_rows() -> list[dict[str, object]]:
    rows = list(read_history_data().values())
    rows.sort(key=lambda row: (int(row.get("year", 0)), int(row.get("month", 0))), reverse=True)
    return rows


def latest_report_path_from_history() -> str:
    rows = history_rows()
    if not rows:
        return ""
    return str(rows[0].get("last_report_path", "") or "")


class AppState:
    def __init__(self) -> None:
        self.busy = False
        self.editor_process: subprocess.Popen[str] | None = None
        self.current_year = 2026
        self.current_month = 7
        self.status_text = "Choisissez une periode puis lancez la preparation."
        self.last_report_path = latest_report_path_from_history()
        self.has_generated_plan = False

    def update_editor_state(self) -> None:
        if not self.editor_process:
            return
        if self.editor_process.poll() is None:
            return

        stdout, stderr = self.editor_process.communicate()
        if self.editor_process.returncode == 0:
            self.status_text = (
                "Classement enregistre.\n"
                "Vous pouvez maintenant lancer un apercu du nettoyage, supprimer vraiment ou configurer les bloques pour les prochains spams."
            )
        else:
            details = (stderr or "").strip() or (stdout or "").strip() or "L'editeur s'est ferme avec une erreur."
            self.status_text = f"Editeur interrompu.\n{details}"
        self.editor_process = None

    def as_payload(self) -> dict[str, object]:
        self.update_editor_state()
        editor_running = self.editor_process is not None and self.editor_process.poll() is None
        can_open_editor = self.has_generated_plan and not self.busy and not editor_running
        can_cleanup = self.has_generated_plan and not self.busy and not editor_running
        can_open_report = bool(self.last_report_path) and not self.busy
        can_send_spam = not self.busy and not editor_running
        return {
            "busy": self.busy,
            "editor_running": editor_running,
            "can_open_editor": can_open_editor,
            "can_preview": can_cleanup,
            "can_delete": can_cleanup,
            "can_open_report": can_open_report,
            "can_send_spam": can_send_spam,
            "status_text": self.status_text,
            "year": self.current_year,
            "month": self.current_month,
            "last_report_path": self.last_report_path,
            "history_rows": history_rows(),
        }


STATE = AppState()


def generate_plan_background(year: int, month: int) -> None:
    try:
        runtime_script = build_runtime_applescript(PLAN_SCRIPT, year, month)
        result = run_command(["osascript", str(runtime_script)])
        output_path = (result.stdout or "").strip() or str(PENDING_FILE)
        STATE.status_text = (
            f"Liste a traiter regeneree pour {MONTHS[month]} {year}.\n"
            f"Fichier : {output_path}\n\n"
            "Vous pouvez maintenant ouvrir l'editeur."
        )
        STATE.has_generated_plan = True
    except Exception as exc:
        STATE.status_text = f"Generation interrompue.\n{format_command_error(exc)}"
    finally:
        STATE.busy = False


def cleanup_background(year: int, month: int, dry_run: bool) -> None:
    try:
        runtime_script = build_runtime_applescript(APPLY_SCRIPT, year, month, dry_run=dry_run)
        result = run_command(["osascript", str(runtime_script)])
        output_path = (result.stdout or "").strip()
        STATE.last_report_path = output_path
        record_history_event(year, month, "preview" if dry_run else "delete", output_path)

        if dry_run:
            STATE.status_text = (
                f"Apercu termine pour {MONTHS[month]} {year}.\n"
                f"Rapport : {output_path}\n\n"
                "Vous pouvez ouvrir le rapport, configurer les bloques pour les prochains spams ou lancer la suppression reelle."
            )
        else:
            STATE.status_text = (
                f"Suppression terminee pour {MONTHS[month]} {year}.\n"
                f"Rapport : {output_path}"
            )
    except Exception as exc:
        STATE.status_text = f"Nettoyage interrompu.\n{format_command_error(exc)}"
    finally:
        STATE.busy = False


def send_spam_background(year: int, month: int) -> None:
    try:
        runtime_script = build_runtime_applescript(JUNK_SCRIPT, year, month)
        result = run_command(["osascript", str(runtime_script)])
        output_path = (result.stdout or "").strip()
        STATE.last_report_path = output_path
        record_history_event(year, month, "spam", output_path)
        STATE.status_text = (
            f"Regle spam mise a jour pour {MONTHS[month]} {year}.\n"
            f"Rapport : {output_path}"
        )
    except Exception as exc:
        STATE.status_text = f"Mise a jour de la regle spam interrompue.\n{format_command_error(exc)}"
    finally:
        STATE.busy = False


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self._send_html(HTML)
            return
        if self.path == "/api/state":
            self._send_json(STATE.as_payload())
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Page introuvable")

    def do_POST(self) -> None:
        if self.path == "/api/generate":
            self._handle_generate()
            return
        if self.path == "/api/open-editor":
            self._handle_open_editor()
            return
        if self.path == "/api/open-report":
            self._handle_open_report()
            return
        if self.path == "/api/send-spam":
            self._handle_send_spam()
            return
        if self.path == "/api/cleanup":
            self._handle_cleanup()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Page introuvable")

    def log_message(self, format: str, *args) -> None:
        return

    def _read_payload(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        return json.loads(raw or "{}")

    def _validate_period(self, payload: dict[str, object]) -> tuple[int, int]:
        year = int(payload.get("year", 0))
        month = int(payload.get("month", 0))
        if year < 2000 or year > 2100:
            raise ValueError("Choisissez une annee entre 2000 et 2100.")
        if month < 1 or month > 12:
            raise ValueError("Le mois doit etre compris entre 1 et 12.")
        return year, month

    def _handle_generate(self) -> None:
        payload = self._read_payload()
        try:
            year, month = self._validate_period(payload)
            if STATE.busy:
                raise ValueError("Un traitement est deja en cours.")
            STATE.busy = True
            STATE.has_generated_plan = False
            STATE.current_year = year
            STATE.current_month = month
            STATE.status_text = f"Preparation de la liste a traiter pour {MONTHS[month]} {year}..."
            threading.Thread(target=generate_plan_background, args=(year, month), daemon=True).start()
            self._send_json(STATE.as_payload())
        except Exception as exc:
            STATE.busy = False
            error_text = format_command_error(exc)
            STATE.status_text = f"Generation interrompue.\n{error_text}"
            self._send_json({"error": error_text, **STATE.as_payload()}, status=HTTPStatus.BAD_REQUEST)

    def _handle_open_editor(self) -> None:
        try:
            STATE.update_editor_state()
            if STATE.busy:
                raise ValueError("Attendez la fin du traitement en cours avant d'ouvrir l'editeur.")
            if STATE.editor_process and STATE.editor_process.poll() is None:
                STATE.status_text = (
                    "L'editeur est deja ouvert dans votre navigateur.\n"
                    "Validez vos choix dans la page pour passer a l'etape suivante."
                )
                self._send_json(STATE.as_payload())
                return

            STATE.editor_process = subprocess.Popen(
                [sys.executable, str(EDITOR_SCRIPT), "--once"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            STATE.status_text = (
                "Editeur ouvert dans votre navigateur.\n"
                "Validez vos choix dans la page. Le pilote detectera automatiquement la fin."
            )
            self._send_json(STATE.as_payload())
        except Exception as exc:
            error_text = format_command_error(exc)
            STATE.status_text = f"Ouverture de l'editeur impossible.\n{error_text}"
            self._send_json({"error": error_text, **STATE.as_payload()}, status=HTTPStatus.BAD_REQUEST)

    def _handle_cleanup(self) -> None:
        payload = self._read_payload()
        try:
            year, month = self._validate_period(payload)
            dry_run = bool(payload.get("dry_run", True))
            if STATE.busy:
                raise ValueError("Un traitement est deja en cours.")
            if not STATE.has_generated_plan:
                raise ValueError("Commencez par generer la liste a traiter.")
            STATE.busy = True
            STATE.current_year = year
            STATE.current_month = month
            label = "Apercu du nettoyage" if dry_run else "Suppression reelle en cours"
            STATE.status_text = f"{label} pour {MONTHS[month]} {year}..."
            threading.Thread(target=cleanup_background, args=(year, month, dry_run), daemon=True).start()
            self._send_json(STATE.as_payload())
        except Exception as exc:
            STATE.busy = False
            error_text = format_command_error(exc)
            STATE.status_text = f"Nettoyage interrompu.\n{error_text}"
            self._send_json({"error": error_text, **STATE.as_payload()}, status=HTTPStatus.BAD_REQUEST)

    def _handle_open_report(self) -> None:
        try:
            if not STATE.last_report_path:
                raise ValueError("Aucun rapport n'est encore disponible.")
            run_command(["open", STATE.last_report_path])
            STATE.status_text = f"Rapport ouvert.\n{STATE.last_report_path}"
            self._send_json(STATE.as_payload())
        except Exception as exc:
            error_text = format_command_error(exc)
            STATE.status_text = f"Ouverture du rapport impossible.\n{error_text}"
            self._send_json({"error": error_text, **STATE.as_payload()}, status=HTTPStatus.BAD_REQUEST)

    def _handle_send_spam(self) -> None:
        payload = self._read_payload()
        try:
            year, month = self._validate_period(payload)
            if STATE.busy:
                raise ValueError("Un traitement est deja en cours.")
            STATE.busy = True
            STATE.current_year = year
            STATE.current_month = month
            STATE.status_text = f"Mise a jour de la regle spam pour {MONTHS[month]} {year}..."
            threading.Thread(target=send_spam_background, args=(year, month), daemon=True).start()
            self._send_json(STATE.as_payload())
        except Exception as exc:
            STATE.busy = False
            error_text = format_command_error(exc)
            STATE.status_text = f"Mise a jour de la regle spam interrompue.\n{error_text}"
            self._send_json({"error": error_text, **STATE.as_payload()}, status=HTTPStatus.BAD_REQUEST)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    ensure_default_files()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host, port = server.server_address
    url = f"http://{host}:{port}/"

    print("Pilote de nettoyage lance.")
    print(f"Ouvrez cette adresse si le navigateur ne se lance pas : {url}")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nArret du pilote.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
