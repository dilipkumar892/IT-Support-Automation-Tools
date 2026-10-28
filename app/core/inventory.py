"""
Inventory Collector and Exporter
Enumerates installed Windows applications, hardware specs, and provides
search, filtering, and export to CSV, JSON, and HTML.
Never collects personal files or browser histories.
"""

import os
import sys
import csv
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from .system_info import collect_full_system_snapshot
from ..database.models import InstalledApp, SystemInventorySnapshot
from ..database.database import Database


def get_installed_applications() -> List[InstalledApp]:
    """
    Scans Windows Registry uninstall keys (64-bit and 32-bit/WOW6432Node)
    for installed applications, deduplicating and cleaning output.
    Does not collect any personal documents, browsing data, or credentials.
    """
    apps: List[InstalledApp] = []
    seen = set()

    if sys.platform != "win32":
        # Mock/fallback for testing on non-windows
        return [
            InstalledApp(name="Python 3", version="3.11.0", publisher="Python Software Foundation", install_date="2024-01-01"),
            InstalledApp(name="PySide6", version="6.5.0", publisher="The Qt Company", install_date="2024-01-01")
        ]

    try:
        import winreg

        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

        for root_key, subkey_path in registry_paths:
            try:
                key = winreg.OpenKey(root_key, subkey_path, 0, winreg.KEY_READ)
            except OSError:
                continue

            num_subkeys = winreg.QueryInfoKey(key)[0]
            for i in range(num_subkeys):
                try:
                    sub_name = winreg.EnumKey(key, i)
                    app_key = winreg.OpenKey(key, sub_name)

                    # Retrieve display name
                    try:
                        name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                    except OSError:
                        winreg.CloseKey(app_key)
                        continue

                    # Filter out system components / updates / blanks
                    try:
                        is_sys, _ = winreg.QueryValueEx(app_key, "SystemComponent")
                        if is_sys == 1:
                            winreg.CloseKey(app_key)
                            continue
                    except OSError:
                        pass

                    try:
                        parent_key, _ = winreg.QueryValueEx(app_key, "ParentKeyName")
                        if parent_key:
                            winreg.CloseKey(app_key)
                            continue
                    except OSError:
                        pass

                    name_str = str(name).strip()
                    if not name_str or name_str in seen:
                        winreg.CloseKey(app_key)
                        continue

                    seen.add(name_str)

                    # Version
                    version = "Unknown"
                    try:
                        ver_val, _ = winreg.QueryValueEx(app_key, "DisplayVersion")
                        if ver_val:
                            version = str(ver_val).strip()
                    except OSError:
                        pass

                    # Publisher
                    publisher = "Unknown"
                    try:
                        pub_val, _ = winreg.QueryValueEx(app_key, "Publisher")
                        if pub_val:
                            publisher = str(pub_val).strip()
                    except OSError:
                        pass

                    # Install Date
                    install_date = "Unknown"
                    try:
                        date_val, _ = winreg.QueryValueEx(app_key, "InstallDate")
                        if date_val:
                            d_str = str(date_val).strip()
                            if len(d_str) == 8 and d_str.isdigit():
                                install_date = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
                            else:
                                install_date = d_str
                    except OSError:
                        pass

                    # Install Location
                    loc = ""
                    try:
                        loc_val, _ = winreg.QueryValueEx(app_key, "InstallLocation")
                        if loc_val:
                            loc = str(loc_val).strip()
                    except OSError:
                        pass

                    apps.append(InstalledApp(
                        name=name_str,
                        version=version,
                        publisher=publisher,
                        install_date=install_date,
                        install_location=loc
                    ))

                    winreg.CloseKey(app_key)
                except Exception:
                    continue

            winreg.CloseKey(key)

    except Exception:
        pass

    apps.sort(key=lambda a: a.name.lower())
    return apps


def capture_and_store_inventory(db: Database) -> SystemInventorySnapshot:
    """Takes a full inventory snapshot including apps, stores it in SQLite, and returns it."""
    snapshot = collect_full_system_snapshot()
    snapshot.installed_apps = get_installed_applications()
    db.save_inventory_snapshot(snapshot)
    return snapshot


def filter_applications(apps: List[InstalledApp], query: str = "") -> List[InstalledApp]:
    """Filters applications by name or publisher."""
    if not query:
        return apps
    q = query.lower().strip()
    return [
        a for a in apps
        if q in a.name.lower() or q in a.publisher.lower()
    ]


def export_inventory_csv(snapshot: SystemInventorySnapshot, filepath: str) -> str:
    """Exports inventory snapshot applications and hardware summary to CSV."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["=== SYSTEM INVENTORY SUMMARY ==="])
        writer.writerow(["Hostname", snapshot.hostname])
        writer.writerow(["Operating System", f"{snapshot.os_name} ({snapshot.os_build})"])
        writer.writerow(["Processor", snapshot.cpu_model])
        writer.writerow(["Total RAM (GB)", snapshot.ram_total_gb])
        writer.writerow(["Uptime (Hours)", snapshot.uptime_hours])
        writer.writerow(["User", snapshot.logged_in_user])
        writer.writerow(["Snapshot Date", snapshot.timestamp])
        writer.writerow([])

        writer.writerow(["=== INSTALLED APPLICATIONS ==="])
        writer.writerow(["Application Name", "Version", "Publisher", "Install Date", "Install Location"])
        for app in snapshot.installed_apps:
            writer.writerow([app.name, app.version, app.publisher, app.install_date, app.install_location])

    return filepath


def export_inventory_json(snapshot: SystemInventorySnapshot, filepath: str) -> str:
    """Exports inventory snapshot to structured JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot.to_dict(), f, indent=2)
    return filepath


def export_inventory_html(snapshot: SystemInventorySnapshot, filepath: str) -> str:
    """Exports inventory snapshot to an interactive, beautifully formatted HTML report."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    app_rows = "".join([
        f"<tr><td><b>{app.name}</b></td><td>{app.version}</td><td>{app.publisher}</td><td>{app.install_date}</td></tr>"
        for app in snapshot.installed_apps
    ])

    disk_rows = "".join([
        f"<tr><td>{d.mountpoint} ({d.device})</td><td>{d.fstype}</td><td>{d.total_gb} GB</td><td>{d.free_gb} GB</td><td>{d.percent_used}%</td></tr>"
        for d in snapshot.disks
    ])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>IT Asset Inventory - {snapshot.hostname}</title>
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background: #0f172a;
        color: #f8fafc;
        margin: 0;
        padding: 30px;
    }}
    .container {{
        max-width: 1100px;
        margin: auto;
    }}
    .header {{
        border-bottom: 2px solid #334155;
        padding-bottom: 20px;
        margin-bottom: 30px;
    }}
    .header h1 {{
        color: #38bdf8;
        margin: 0;
        font-size: 28px;
    }}
    .card {{
        background: #1e293b;
        border-radius: 8px;
        border: 1px solid #334155;
        padding: 20px;
        margin-bottom: 25px;
    }}
    .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 15px;
    }}
    .stat-label {{
        color: #94a3b8;
        font-size: 13px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }}
    .stat-value {{
        font-size: 16px;
        font-weight: 600;
        color: #f1f5f9;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
    }}
    th, td {{
        text-align: left;
        padding: 10px 14px;
        border-bottom: 1px solid #334155;
        font-size: 14px;
    }}
    th {{
        background: #0f172a;
        color: #38bdf8;
    }}
    tr:hover {{
        background: #273548;
    }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>IT Asset Inventory Report</h1>
        <p style="color: #94a3b8; margin-top: 5px;">Snapshot captured: {snapshot.timestamp} | Generated by IT Support Automation Suite</p>
    </div>

    <div class="card">
        <h2 style="color: #a855f7; margin-top: 0;">System Information</h2>
        <div class="grid">
            <div><div class="stat-label">Computer Name</div><div class="stat-value">{snapshot.hostname}</div></div>
            <div><div class="stat-label">Operating System</div><div class="stat-value">{snapshot.os_name} ({snapshot.os_build})</div></div>
            <div><div class="stat-label">Processor</div><div class="stat-value">{snapshot.cpu_model}</div></div>
            <div><div class="stat-label">Installed Memory</div><div class="stat-value">{snapshot.ram_total_gb} GB</div></div>
            <div><div class="stat-label">Uptime</div><div class="stat-value">{snapshot.uptime_hours} Hours</div></div>
            <div><div class="stat-label">Current User</div><div class="stat-value">{snapshot.logged_in_user}</div></div>
        </div>
    </div>

    <div class="card">
        <h2 style="color: #38bdf8; margin-top: 0;">Storage Volumes</h2>
        <table>
            <thead><tr><th>Mountpoint</th><th>Filesystem</th><th>Total Capacity</th><th>Free Space</th><th>Usage %</th></tr></thead>
            <tbody>{disk_rows}</tbody>
        </table>
    </div>

    <div class="card">
        <h2 style="color: #38bdf8; margin-top: 0;">Installed Software ({len(snapshot.installed_apps)} Applications)</h2>
        <table>
            <thead><tr><th>Application Name</th><th>Version</th><th>Publisher</th><th>Install Date</th></tr></thead>
            <tbody>{app_rows}</tbody>
        </table>
    </div>
</div>
</body>
</html>
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return filepath

