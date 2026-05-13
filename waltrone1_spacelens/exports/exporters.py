from __future__ import annotations

import csv
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ..core.models import ScanError, ScanNode
from ..core.size_format import format_size


BRAND_URL = "https://waltrone1.de/wltones-admin-tools/"
LOGO_URL = "https://yt3.googleusercontent.com/zXzem7bbA0rm0FKIe8svIoqYl6FS3re2kqx31psWGF3W8SAzpc_kxg_N-y_LLwIHQHOc90nS8w=s900-c-k-c0x00ffffff-no-rj"
VERSION = "1.0.0.0"
BUILD = "2026-05-06"


def iter_nodes(root: ScanNode) -> Iterable[ScanNode]:
    yield root
    for child in root.children:
        yield from iter_nodes(child)


def top_folders(root: ScanNode, limit: int = 50) -> list[ScanNode]:
    folders = [node for node in iter_nodes(root) if node.is_dir and node.path != root.path]
    folders.sort(key=lambda node: node.size, reverse=True)
    return folders[:limit]


def top_files(root: ScanNode, limit: int = 50, min_size_bytes: int = 0) -> list[ScanNode]:
    files = [node for node in iter_nodes(root) if not node.is_dir and node.size >= min_size_bytes]
    files.sort(key=lambda node: node.size, reverse=True)
    return files[:limit]


def export_csv(root: ScanNode, destination: str) -> None:
    with open(destination, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["Typ", "Name", "Groesse Bytes", "Groesse", "Dateien", "Ordner", "Pfad"])
        for node in iter_nodes(root):
            writer.writerow([
                "Ordner" if node.is_dir else "Datei",
                node.name,
                node.size,
                format_size(node.size),
                node.file_count,
                node.folder_count,
                node.path,
            ])


def node_to_dict(node: ScanNode) -> dict:
    return {
        "name": node.name,
        "path": node.path,
        "type": "folder" if node.is_dir else "file",
        "size_bytes": node.size,
        "size": format_size(node.size),
        "file_count": node.file_count,
        "folder_count": node.folder_count,
        "children": [node_to_dict(child) for child in node.children],
    }


def export_json(root: ScanNode, category_totals: dict[str, int], errors: list[ScanError], destination: str) -> None:
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "root": node_to_dict(root),
        "category_totals": {
            key: {"size_bytes": value, "size": format_size(value)}
            for key, value in category_totals.items()
        },
        "errors": [{"path": error.path, "message": error.message} for error in errors],
    }
    Path(destination).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _report_table_rows(nodes: list[ScanNode], root_size: int) -> str:
    rows: list[str] = []
    total = root_size or 1
    for node in nodes:
        percent = node.size / total * 100
        icon = "📁" if node.is_dir else "📄"
        typ = "Ordner" if node.is_dir else "Datei"
        search = html.escape(f"{node.name} {node.path} {typ} {format_size(node.size)}")
        rows.append(
            "<tr class='row system' data-search='{}'>"
            "<td>{} {}</td><td>{}</td><td>{:.1f} %</td><td>{}</td><td class='small'>{}</td></tr>".format(
                search,
                icon,
                html.escape(node.name),
                format_size(node.size),
                percent,
                typ,
                html.escape(node.path),
            )
        )
    return "\n".join(rows)


def export_html_report(root: ScanNode, category_totals: dict[str, int], errors: list[ScanError], destination: str) -> None:
    created_at = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    folders = top_folders(root)
    files = top_files(root)
    total = root.size or 1

    category_rows = []
    for key, value in sorted(category_totals.items(), key=lambda item: item[1], reverse=True):
        if value <= 0:
            continue
        percent = value / total * 100
        search = html.escape(f"{key} {format_size(value)} {percent:.1f}")
        category_rows.append(
            "<tr class='row valid' data-search='{}'><td>📊 {}</td><td>{}</td><td>{:.1f} %</td></tr>".format(
                search, html.escape(key), format_size(value), percent
            )
        )
    category_rows_html = "\n".join(category_rows) or "<tr class='row info'><td colspan='3'>Keine Kategorie-Daten vorhanden.</td></tr>"

    error_rows = []
    for error in errors[:200]:
        search = html.escape(f"{error.path} {error.message}")
        error_rows.append(
            "<tr class='row expiring' data-search='{}'><td class='small'>{}</td><td class='small'>{}</td></tr>".format(
                search, html.escape(error.path), html.escape(error.message)
            )
        )
    error_rows_html = "\n".join(error_rows) or "<tr class='row valid'><td colspan='2'>Keine Scanfehler vorhanden.</td></tr>"

    path_escaped = html.escape(root.path)
    document = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>waltrone1-SpaceLens Bericht</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{{--brand:#0b3a67;--bg:#f4f6f8;--card:#ffffff;--muted:#6b7280;--line:#e5e7eb;--shadow:0 6px 18px rgba(16,24,40,.08);--radius:12px}}
*{{box-sizing:border-box}}
body{{font-family:Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);margin:20px;color:#1f2933}}
h1{{margin:0 0 6px 0;font-size:28px}}
h2{{margin:18px 0 8px 0;font-size:18px}}
.small{{font-size:12px;color:var(--muted)}}
.meta{{line-height:1.35}}
hr.sep{{border:none;border-top:1px solid var(--line);margin:16px 0}}
.header{{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:14px}}
.brandbox{{background:var(--card);padding:16px 18px;border-radius:var(--radius);box-shadow:var(--shadow);border:1px solid rgba(0,0,0,.04);flex:1}}
.logo-wrap{{display:flex;align-items:flex-start;justify-content:flex-end;min-width:220px}}
.logo{{height:120px;width:auto;border-radius:14px;box-shadow:0 4px 10px rgba(0,0,0,.10);border:1px solid rgba(0,0,0,.06)}}
.section{{background:var(--card);padding:20px;border-radius:var(--radius);box-shadow:var(--shadow);margin-bottom:20px;border:1px solid rgba(0,0,0,.04)}}
.kpis{{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}}
.kpi{{background:#f8fafc;border:1px solid var(--line);border-radius:12px;padding:10px 12px;min-width:170px}}
.kpi b{{font-size:18px;display:block}}
.kpi span{{font-size:12px;color:var(--muted)}}
table{{width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden}}
th{{background:var(--brand);color:#fff;padding:10px;font-size:13px;text-align:left}}
td{{padding:9px;border-bottom:1px solid var(--line);font-size:13px;vertical-align:top}}
tr.system{{background:#ffffff}}
tr.valid{{background:#e6f3f1}}
tr.expiring{{background:#fff4e6}}
tr.info{{background:#e8f0ff}}
.toolbar{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
input[type="text"]{{padding:8px 10px;width:460px;max-width:100%;border-radius:10px;border:1px solid #d1d5db;outline:none}}
input[type="text"]:focus{{border-color:var(--brand);box-shadow:0 0 0 3px rgba(11,58,103,.15)}}
button{{padding:8px 14px;border-radius:10px;font-weight:700;border:1px solid rgba(0,0,0,.08);cursor:pointer;background:#fff;transition:transform .08s ease,filter .15s ease,box-shadow .15s ease}}
button:hover{{filter:brightness(1.03);box-shadow:0 8px 18px rgba(0,0,0,.10);transform:translateY(-1px)}}
footer.footer{{margin-top:18px;font-size:12px;color:var(--muted);text-align:right;padding:10px 12px;width:100%;background:var(--card);border:1px solid var(--line);border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,.06);line-height:1.35}}
footer.footer a{{display:inline-block;padding:4px 10px;border-radius:999px;background:var(--brand);color:#fff;text-decoration:none;font-family:Roboto,Segoe UI,Arial,sans-serif;font-weight:500;letter-spacing:.3px;transition: transform .08s ease, filter .15s ease, box-shadow .15s ease}}
footer.footer a:hover{{filter:brightness(1.07);box-shadow:0 6px 14px rgba(0,0,0,.12);transform: translateY(-1px)}}
footer.footer b{{color:#374151}}
.rev{{display:inline-block;padding:2px 8px;margin-left:6px;border-radius:999px;border:1px solid var(--line);background:#f8fafc;color:var(--muted);font-weight:800;font-size:11px}}
.footer-row{{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}}
.footer-hint{{display:inline-block;padding:4px 10px;border-radius:999px;background:var(--brand);color:#fff;font-family:Roboto,Segoe UI,Arial,sans-serif;font-weight:500;letter-spacing:.3px;white-space:nowrap}}
@media (max-width:720px){{.header{{flex-direction:column}}.logo-wrap{{justify-content:flex-start}}}}
</style>
<script>
function normalize(s){{
  s = (s === null || s === undefined) ? "" : String(s);
  return s.toLowerCase().replace(/[^a-z0-9\u00C0-\u024F:.\\[\\]\\-\\\\/]+/g," ").replace(/\\s+/g," ").trim();
}}
function applySearch(){{
  const input = document.getElementById("searchBox");
  if(!input) return;
  const q = normalize(input.value);
  document.querySelectorAll("tr.row").forEach(r=>{{
    const source = r.getAttribute("data-search") || r.textContent || "";
    r.hidden = !!(q && !normalize(source).includes(q));
  }});
}}
function resetAll(){{
  const input = document.getElementById("searchBox");
  if(!input) return;
  input.value="";
  applySearch();
  input.focus();
}}
window.addEventListener('DOMContentLoaded', ()=>{{
  const input = document.getElementById('searchBox');
  if(input){{ input.addEventListener('input', applySearch); input.addEventListener('search', applySearch); }}
  applySearch();
}});
</script>
</head>
<body>
<div class="header">
  <div class="brandbox">
    <h1>waltrone1-SpaceLens - Bericht</h1>
    <div class="meta"><b>🧭 Pfad:</b> {path_escaped}<br>
<b>🕒 Erstellt am:</b> {created_at}</div>
    <div class="kpis"><div class="kpi"><b>{format_size(root.size)}</b><span>Gesamtgröße</span></div>
<div class="kpi"><b>{root.file_count:,}</b><span>Dateien</span></div>
<div class="kpi"><b>{root.folder_count:,}</b><span>Ordner</span></div>
<div class="kpi"><b>{len(folders)}</b><span>Top-Ordner</span></div>
<div class="kpi"><b>{len(files)}</b><span>Top-Dateien</span></div></div>
  </div>
  <div class="logo-wrap">
    <a class="logo-link" href="{BRAND_URL}" target="_blank" rel="noopener noreferrer">
      <img class="logo" src="{LOGO_URL}" alt="Logo">
    </a>
  </div>
</div>

<div class="section" id="resultsSection">
  <div class="toolbar">
    <input id="searchBox" type="text" placeholder="Suchen (Kategorie, Ordner, Datei, Pfad ...)">
    <button onclick="resetAll()">Zurücksetzen</button>
  </div>
  <hr class="sep">
  <h2>📊 Kategorien</h2>
  <table><tr><th>Kategorie</th><th>Größe</th><th>Anteil</th></tr>{category_rows_html}</table>

  <h2>📁 Top 50 größte Ordner</h2>
  <table><tr><th>Name</th><th>Größe</th><th>Anteil</th><th>Typ</th><th>Pfad</th></tr>{_report_table_rows(folders, root.size)}</table>

  <h2>📄 Top 50 größte Dateien</h2>
  <table><tr><th>Name</th><th>Größe</th><th>Anteil</th><th>Typ</th><th>Pfad</th></tr>{_report_table_rows(files, root.size)}</table>
  <div class="small" style="margin-top:12px;line-height:1.45">Hinweis: Gesperrte oder nicht lesbare Dateien, fehlende Berechtigungen und Offline-Netzlaufwerke werden beim Scan still übersprungen.</div>
</div>

<footer class="footer">
  <div>Bericht erstellt mit <b>waltrone1-SpaceLens</b><span class="rev">v{VERSION}</span></div>
  <div class="footer-row" style="margin-top:6px">
    <div></div>
    <div><a href="{BRAND_URL}" target="_blank" rel="noopener noreferrer">w@lt&reg;one1</a></div>
  </div>
</footer>
</body>
</html>"""
    Path(destination).write_text(document, encoding="utf-8")
