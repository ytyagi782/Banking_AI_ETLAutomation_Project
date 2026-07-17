"""
html_report.py
--------------
The third report: a clean, self-contained HTML page for management.
No external files or internet needed - CSS is embedded.
"""

import os
import base64
import getpass
import mimetypes
from datetime import datetime
from html import escape

from utilities import result_store, config_loader


def _current_user():
    """Best-effort system username for the report header."""
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def _branding():
    """Branding block from settings.yaml -> reporting.branding (may be empty)."""
    return (config_loader.get_settings().get("reporting", {}) or {}).get(
        "branding", {}) or {}


def _data_uri(path):
    """
    Read an image file and return a self-contained base64 data URI, so the HTML
    report needs no external files. Returns None if the path is missing/empty or
    the file does not exist (the element is then simply omitted).
    """
    if not path:
        return None
    abs_path = path if os.path.isabs(path) else config_loader.abs_path(path)
    if not os.path.exists(abs_path):
        return None
    mime = mimetypes.guess_type(abs_path)[0] or "image/png"
    try:
        with open(abs_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime};base64,{data}"
    except OSError:
        return None


def _kpi_card(label, value, color1, color2, icon):
    """A colourful gradient KPI tile with an icon and a faint watermark."""
    return f"""
      <div class="card" style="background:linear-gradient(135deg,{color1},{color2})">
        <div class="card-icon">{icon}</div>
        <div class="card-value">{value}</div>
        <div class="card-label">{label}</div>
        <div class="card-watermark">{icon}</div>
      </div>"""


def _rows_html(results):
    out = []
    css_map = {"PASS": "pass", "FAIL": "fail", "SKIP": "skip"}
    for r in results:
        css = css_map.get(r["status"], "fail")
        out.append(f"""
        <tr class="{css}">
          <td>{escape(r['layer'])}</td>
          <td>{escape(r['table'])}</td>
          <td>{escape(r['validation'])}</td>
          <td>{escape(r['category'])}</td>
          <td class="status">{r['status']}</td>
          <td>{escape(str(r['message']))}</td>
        </tr>""")
    return "".join(out)


def build_html_report(path):
    counts = result_store.summary_counts()
    by_layer = result_store.summary_by_layer()
    executed = result_store.get_executed()
    skipped = result_store.get_skipped()
    failures = result_store.get_failures()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = _current_user()

    status_color = "#2e7d32" if counts["failed"] == 0 else "#c62828"
    overall = "PASSED" if counts["failed"] == 0 else "ATTENTION NEEDED"

    # ---- branding (company logo + name on the left, author photo on the right) ----
    brand = _branding()
    company_name = brand.get("company_name", "")
    author_name = brand.get("author_name") or user
    author_role = brand.get("author_role", "Report Author")
    logo_uri = _data_uri(brand.get("company_logo"))
    author_uri = _data_uri(brand.get("author_image"))

    logo_html = (f'<img class="logo" src="{logo_uri}" alt="company logo">'
                 if logo_uri else "")
    company_html = (f'<div class="company">{escape(company_name)}</div>'
                    if company_name else "")
    author_img_html = (f'<img class="avatar" src="{author_uri}" alt="author">'
                       if author_uri else "")
    author_html = f"""
      <div class="author">
        {author_img_html}
        <div class="author-name">{escape(author_name)}</div>
        <div class="author-role">{escape(author_role)}</div>
      </div>"""

    layer_rows = "".join(
        f"<tr><td>{escape(l)}</td><td>{g['passed']}</td>"
        f"<td class='{'fail' if g['failed'] else 'pass'}'>{g['failed']}</td>"
        f"<td class='skip'>{g['skipped']}</td></tr>"
        for l, g in by_layer.items()
    )

    skipped_section = (
        "<p>No skipped tests in this run.</p>" if not skipped else
        f"""<table>
          <thead><tr><th>Layer</th><th>Table</th><th>Validation</th>
          <th>Category</th><th>Status</th><th>Message</th></tr></thead>
          <tbody>{_rows_html(skipped)}</tbody></table>"""
    )

    failures_section = (
        "<p class='ok'>&#10004; No failures - all validations passed.</p>"
        if not failures else
        f"""<table>
          <thead><tr><th>Layer</th><th>Table</th><th>Validation</th>
          <th>Category</th><th>Status</th><th>Message</th></tr></thead>
          <tbody>{_rows_html(failures)}</tbody></table>"""
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Banking ETL Automation Report</title>
<style>
  body {{ font-family: Segoe UI, Arial, sans-serif; margin:0; background:#f4f6f9; color:#243b53; }}
  header {{ background:linear-gradient(135deg,#102a43,#243b74); color:#fff; padding:22px 32px;
            display:flex; align-items:center; justify-content:space-between; gap:20px; }}
  header h1 {{ margin:0; font-size:22px; }}
  header p {{ margin:5px 0 0; color:#c3d0e8; font-size:13px; }}
  .brand {{ display:flex; align-items:center; gap:18px; }}
  .logo {{ height:52px; width:auto; max-width:160px; background:#fff;
           border-radius:8px; padding:5px; object-fit:contain; }}
  .company {{ font-size:15px; font-weight:700; color:#ffd27d; margin:2px 0 0;
              letter-spacing:.3px; }}
  .author {{ text-align:center; min-width:96px; }}
  .avatar {{ height:62px; width:62px; border-radius:50%; object-fit:cover;
             border:2px solid #ffffff; box-shadow:0 2px 8px rgba(0,0,0,.25); }}
  .author-name {{ font-size:13px; font-weight:600; margin-top:6px; }}
  .author-role {{ font-size:11px; color:#c3d0e8; }}
  .banner {{ padding:14px 32px; font-weight:bold; color:#fff; background:{status_color}; }}
  .wrap {{ padding:24px 32px; }}
  .cards {{ display:flex; gap:20px; flex-wrap:wrap; margin-bottom:28px; }}
  .card {{ flex:1 1 190px; border-radius:16px; padding:22px 24px; color:#fff;
           position:relative; overflow:hidden;
           box-shadow:0 8px 20px rgba(16,42,67,.18);
           transition:transform .18s ease, box-shadow .18s ease; }}
  .card:hover {{ transform:translateY(-5px); box-shadow:0 14px 28px rgba(16,42,67,.28); }}
  .card-icon {{ font-size:26px; line-height:1; opacity:.95; }}
  .card-value {{ font-size:44px; font-weight:800; line-height:1.05; margin-top:8px;
                 text-shadow:0 1px 2px rgba(0,0,0,.15); }}
  .card-label {{ font-size:12px; font-weight:600; text-transform:uppercase;
                 letter-spacing:1px; opacity:.95; margin-top:4px; }}
  .card-watermark {{ position:absolute; right:-8px; bottom:-22px; font-size:96px;
                     opacity:.13; pointer-events:none; }}
  h2 {{ font-size:16px; border-bottom:2px solid #d9e2ec; padding-bottom:6px; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; margin-bottom:28px;
           box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  th {{ background:#334e68; color:#fff; text-align:left; padding:9px 12px; font-size:13px; }}
  td {{ padding:8px 12px; border-bottom:1px solid #e6ecf2; font-size:13px; }}
  tr.pass .status {{ color:#2e7d32; font-weight:bold; }}
  tr.fail .status {{ color:#c62828; font-weight:bold; }}
  tr.skip .status {{ color:#607d8b; font-weight:bold; }}
  tr.fail {{ background:#fff5f5; }}
  tr.skip {{ background:#f4f6f8; color:#607d8b; }}
  td.fail {{ color:#c62828; font-weight:bold; }}
  td.pass {{ color:#2e7d32; }}
  td.skip {{ color:#607d8b; }}
  .ok {{ color:#2e7d32; font-weight:bold; }}
  footer {{ text-align:center; color:#829ab1; font-size:12px; padding:20px; }}
</style>
</head>
<body>
  <header>
    <div class="brand">
      {logo_html}
      <div class="brand-text">
        <h1>Banking ETL Automation &ndash; Test Execution Report</h1>
        {company_html}
        <p>Generated on : {now}</p>
        <p>Generated by : {escape(user)}</p>
      </div>
    </div>
    {author_html}
  </header>
  <div class="banner">Overall result: {overall} &nbsp; | &nbsp; Pass rate: {counts['pass_rate']}%</div>
  <div class="wrap">
    <div class="cards">
      {_kpi_card("Total TestCases", counts['total'], "#3b4a63", "#5a6f91", "&#128203;")}
      {_kpi_card("Passed", counts['passed'], "#1e8e3e", "#4cc46b", "&#9989;")}
      {_kpi_card("Failed", counts['failed'], "#c62828", "#ef5350", "&#10060;")}
      {_kpi_card("Skipped", counts['skipped'], "#607d8b", "#90a4ae", "&#9193;")}
      {_kpi_card("Pass Rate", str(counts['pass_rate']) + "%", "#1565c0", "#42a5f5", "&#128200;")}
    </div>

    <h2>Results by layer</h2>
    <table>
      <thead><tr><th>Layer</th><th>Passed</th><th>Failed</th><th>Skipped</th></tr></thead>
      <tbody>{layer_rows}</tbody>
    </table>

    <h2>Failures</h2>
    {failures_section}

    <h2>Executed validations ({counts['executed']})</h2>
    <table>
      <thead><tr><th>Layer</th><th>Table</th><th>Validation</th>
      <th>Category</th><th>Status</th><th>Message</th></tr></thead>
      <tbody>{_rows_html(executed)}</tbody>
    </table>

    <h2>Skipped validations ({counts['skipped']})</h2>
    {skipped_section}
  </div>
  <footer>Banking ETL Automation Framework &bull; Automated report</footer>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
