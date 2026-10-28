"""
HTML, CSV, and JSON Diagnostic Report Generator
Produces clean, responsive, dark/light compatible diagnostic reports.
"""

import os
import csv
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..database.models import DiagnosticReport, SystemInventorySnapshot


def generate_html_report(
    report: DiagnosticReport,
    system_snapshot: Optional[SystemInventorySnapshot] = None,
    output_path: Optional[str] = None
) -> str:
    """Generates an executive-ready HTML diagnostic report."""
    if not output_path:
        timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"reports_export/DiagnosticReport_{timestamp_slug}.html"

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Status color badge mapping
    status_colors = {
        "PASS": ("#10b981", "#064e3b", "Normal / Operational"),
        "WARNING": ("#f59e0b", "#78350f", "Warning / Attention Needed"),
        "CRITICAL": ("#ef4444", "#7f1d1d", "Critical / Action Required"),
        "INFO": ("#38bdf8", "#0c4a6e", "Informational")
    }
    badge_fg, badge_bg, badge_desc = status_colors.get(report.status.upper(), ("#38bdf8", "#0c4a6e", report.status))

    # Format findings list
    findings_html = ""
    if report.findings:
        findings_html = "<ul>" + "".join([
            f"<li>{item.get('item', item.get('detail', str(item)))}</li>"
            if isinstance(item, dict) else f"<li>{item}</li>"
            for item in report.findings
        ]) + "</ul>"
    else:
        findings_html = "<p style='color: #94a3b8;'>No anomalies or defects reported.</p>"

    # Format recommendations
    rec_html = ""
    if report.recommendations:
        rec_html = "<ol>" + "".join([f"<li>{rec}</li>" for rec in report.recommendations]) + "</ol>"
    else:
        rec_html = "<p style='color: #94a3b8;'>No remediation steps currently required.</p>"

    # System specs summary block
    sys_html = ""
    if system_snapshot:
        sys_html = f"""
        <div class="card">
            <h2>Target Machine Specifications</h2>
            <div class="grid">
                <div><div class="stat-lbl">Hostname</div><div class="stat-val">{system_snapshot.hostname}</div></div>
                <div><div class="stat-lbl">OS</div><div class="stat-val">{system_snapshot.os_name} ({system_snapshot.os_build})</div></div>
                <div><div class="stat-lbl">Processor</div><div class="stat-val">{system_snapshot.cpu_model}</div></div>
                <div><div class="stat-lbl">RAM Total</div><div class="stat-val">{system_snapshot.ram_total_gb} GB</div></div>
                <div><div class="stat-lbl">Uptime</div><div class="stat-val">{system_snapshot.uptime_hours} Hours</div></div>
                <div><div class="stat-lbl">Admin Session</div><div class="stat-val">{'Yes' if system_snapshot.is_admin else 'No'}</div></div>
            </div>
        </div>
        """

    logs_section = ""
    if report.logs:
        logs_section = f"""
        <div class="card">
            <h2>Diagnostic Logs & Execution Trace</h2>
            <pre class="log-box">{report.logs}</pre>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{report.title} - IT Support Report</title>
<style>
    :root {{
        --bg: #090d16;
        --card: #131b2e;
        --border: #233554;
        --text: #f1f5f9;
        --muted: #94a3b8;
        --accent: #00d2ff;
        --purple: #9d4edd;
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background-color: var(--bg);
        color: var(--text);
        margin: 0;
        padding: 40px 20px;
        line-height: 1.6;
    }}
    .container {{
        max-width: 950px;
        margin: 0 auto;
    }}
    .header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 1px solid var(--border);
        padding-bottom: 20px;
        margin-bottom: 25px;
    }}
    h1 {{
        margin: 0 0 6px 0;
        font-size: 26px;
        background: linear-gradient(135deg, var(--accent), var(--purple));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .meta {{
        color: var(--muted);
        font-size: 13px;
    }}
    .badge {{
        display: inline-block;
        padding: 6px 14px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 13px;
        letter-spacing: 0.5px;
        background-color: {badge_bg};
        color: {badge_fg};
        border: 1px solid {badge_fg};
    }}
    .card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }}
    h2 {{
        margin-top: 0;
        font-size: 18px;
        color: var(--accent);
        border-bottom: 1px solid rgba(255,255,255,0.08);
        padding-bottom: 8px;
    }}
    .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
    }}
    .stat-lbl {{
        color: var(--muted);
        font-size: 12px;
        text-transform: uppercase;
        font-weight: 600;
    }}
    .stat-val {{
        font-size: 15px;
        font-weight: 600;
        color: #fff;
    }}
    ul, ol {{
        padding-left: 22px;
        margin: 10px 0;
    }}
    li {{
        margin-bottom: 8px;
    }}
    .log-box {{
        background: #060911;
        border: 1px solid #1a2333;
        border-radius: 6px;
        padding: 14px;
        color: #7dd3fc;
        font-family: "Cascadia Code", Consolas, Monaco, monospace;
        font-size: 12px;
        overflow-x: auto;
        white-space: pre-wrap;
    }}
    .footer {{
        text-align: center;
        font-size: 12px;
        color: var(--muted);
        margin-top: 40px;
        border-top: 1px solid var(--border);
        padding-top: 15px;
    }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1>{report.title}</h1>
            <div class="meta">Report Type: {report.report_type.upper()} | Timestamp: {report.created_at} | Suite Version: 1.0.0</div>
        </div>
        <div>
            <span class="badge">{report.status.upper()}</span>
        </div>
    </div>

    <div class="card">
        <h2>Executive Summary</h2>
        <p style="font-size: 15px; margin: 0;">{report.summary or 'Automated diagnostic scan completed.'}</p>
    </div>

    {sys_html}

    <div class="card">
        <h2>Diagnostic Findings</h2>
        {findings_html}
    </div>

    <div class="card">
        <h2>Recommended Remediation Actions</h2>
        {rec_html}
    </div>

    {logs_section}

    <div class="footer">
        Generated by Professional IT Support Automation Suite &bull; Confidential Internal Diagnostics
    </div>
</div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def export_report_json(report: DiagnosticReport, output_path: str) -> str:
    """Exports diagnostic report to JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)
    return output_path


def export_report_csv(report: DiagnosticReport, output_path: str) -> str:
    """Exports diagnostic report summary and findings to CSV."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Field", "Value"])
        writer.writerow(["Title", report.title])
        writer.writerow(["Status", report.status])
        writer.writerow(["Type", report.report_type])
        writer.writerow(["Created At", report.created_at])
        writer.writerow(["Summary", report.summary])
        writer.writerow([])
        writer.writerow(["=== FINDINGS ==="])
        for idx, finding in enumerate(report.findings, 1):
            val = finding.get("item", finding.get("detail", str(finding))) if isinstance(finding, dict) else str(finding)
            writer.writerow([f"Finding #{idx}", val])
        writer.writerow([])
        writer.writerow(["=== RECOMMENDATIONS ==="])
        for idx, rec in enumerate(report.recommendations, 1):
            writer.writerow([f"Recommendation #{idx}", rec])
    return output_path

