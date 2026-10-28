"""
SQLite Database Layer for Local Storage
"""

import sqlite3
import json
import os
from typing import List, Optional, Dict, Any
from .models import (
    SystemInventorySnapshot,
    DiskInfo,
    NetworkInterfaceInfo,
    InstalledApp,
    DiagnosticReport,
    AutomationHistoryEntry,
)


class Database:
    def __init__(self, db_path: str = "data/it_support.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Inventory snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    hostname TEXT NOT NULL,
                    os_name TEXT,
                    os_version TEXT,
                    os_build TEXT,
                    architecture TEXT,
                    cpu_model TEXT,
                    cpu_cores_logical INTEGER,
                    cpu_cores_physical INTEGER,
                    ram_total_gb REAL,
                    ram_available_gb REAL,
                    uptime_hours REAL,
                    logged_in_user TEXT,
                    is_admin INTEGER DEFAULT 0
                )
            """)

            # Disks table linked to snapshot
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_disks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    device TEXT,
                    mountpoint TEXT,
                    fstype TEXT,
                    total_gb REAL,
                    used_gb REAL,
                    free_gb REAL,
                    percent_used REAL,
                    FOREIGN KEY (snapshot_id) REFERENCES inventory_snapshots (id) ON DELETE CASCADE
                )
            """)

            # Network interfaces table linked to snapshot
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_networks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    name TEXT,
                    mac_address TEXT,
                    ipv4_json TEXT,
                    ipv6_json TEXT,
                    is_up INTEGER DEFAULT 0,
                    speed_mbps INTEGER DEFAULT 0,
                    FOREIGN KEY (snapshot_id) REFERENCES inventory_snapshots (id) ON DELETE CASCADE
                )
            """)

            # Installed applications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_apps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    version TEXT,
                    publisher TEXT,
                    install_date TEXT,
                    install_location TEXT,
                    FOREIGN KEY (snapshot_id) REFERENCES inventory_snapshots (id) ON DELETE CASCADE
                )
            """)

            # Diagnostic reports table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS diagnostic_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT,
                    findings_json TEXT,
                    recommendations_json TEXT,
                    logs TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Automation history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS automation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    exit_code INTEGER DEFAULT 0,
                    output_text TEXT,
                    error_text TEXT
                )
            """)

            # Helpful indices for fast querying
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_time ON inventory_snapshots(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_name ON inventory_apps(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_time ON diagnostic_reports(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_auto_time ON automation_history(started_at)")
            conn.commit()

    # --- INVENTORY OPERATIONS ---

    def save_inventory_snapshot(self, snapshot: SystemInventorySnapshot) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory_snapshots (
                    timestamp, hostname, os_name, os_version, os_build, architecture,
                    cpu_model, cpu_cores_logical, cpu_cores_physical,
                    ram_total_gb, ram_available_gb, uptime_hours,
                    logged_in_user, is_admin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot.timestamp, snapshot.hostname, snapshot.os_name, snapshot.os_version,
                snapshot.os_build, snapshot.architecture, snapshot.cpu_model,
                snapshot.cpu_cores_logical, snapshot.cpu_cores_physical,
                snapshot.ram_total_gb, snapshot.ram_available_gb, snapshot.uptime_hours,
                snapshot.logged_in_user, 1 if snapshot.is_admin else 0
            ))
            snapshot_id = cursor.lastrowid

            for disk in snapshot.disks:
                cursor.execute("""
                    INSERT INTO inventory_disks (
                        snapshot_id, device, mountpoint, fstype, total_gb, used_gb, free_gb, percent_used
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot_id, disk.device, disk.mountpoint, disk.fstype,
                    disk.total_gb, disk.used_gb, disk.free_gb, disk.percent_used
                ))

            for net in snapshot.network_interfaces:
                cursor.execute("""
                    INSERT INTO inventory_networks (
                        snapshot_id, name, mac_address, ipv4_json, ipv6_json, is_up, speed_mbps
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot_id, net.name, net.mac_address,
                    json.dumps(net.ipv4_addresses), json.dumps(net.ipv6_addresses),
                    1 if net.is_up else 0, net.speed_mbps
                ))

            for app in snapshot.installed_apps:
                cursor.execute("""
                    INSERT INTO inventory_apps (
                        snapshot_id, name, version, publisher, install_date, install_location
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    snapshot_id, app.name, app.version, app.publisher,
                    app.install_date, app.install_location
                ))

            conn.commit()
            snapshot.id = snapshot_id
            return snapshot_id

    def get_latest_inventory_snapshot(self) -> Optional[SystemInventorySnapshot]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventory_snapshots ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            snapshot_id = row["id"]

            # Load disks
            cursor.execute("SELECT * FROM inventory_disks WHERE snapshot_id = ?", (snapshot_id,))
            disks = [
                DiskInfo(
                    device=d["device"],
                    mountpoint=d["mountpoint"],
                    fstype=d["fstype"],
                    total_gb=d["total_gb"],
                    used_gb=d["used_gb"],
                    free_gb=d["free_gb"],
                    percent_used=d["percent_used"],
                )
                for d in cursor.fetchall()
            ]

            # Load network
            cursor.execute("SELECT * FROM inventory_networks WHERE snapshot_id = ?", (snapshot_id,))
            nets = [
                NetworkInterfaceInfo(
                    name=n["name"],
                    mac_address=n["mac_address"],
                    ipv4_addresses=json.loads(n["ipv4_json"] or "[]"),
                    ipv6_addresses=json.loads(n["ipv6_json"] or "[]"),
                    is_up=bool(n["is_up"]),
                    speed_mbps=n["speed_mbps"],
                )
                for n in cursor.fetchall()
            ]

            # Load apps
            cursor.execute("SELECT * FROM inventory_apps WHERE snapshot_id = ?", (snapshot_id,))
            apps = [
                InstalledApp(
                    name=a["name"],
                    version=a["version"] or "Unknown",
                    publisher=a["publisher"] or "Unknown",
                    install_date=a["install_date"] or "Unknown",
                    install_location=a["install_location"] or "",
                )
                for a in cursor.fetchall()
            ]

            return SystemInventorySnapshot(
                id=row["id"],
                timestamp=row["timestamp"],
                hostname=row["hostname"],
                os_name=row["os_name"] or "",
                os_version=row["os_version"] or "",
                os_build=row["os_build"] or "",
                architecture=row["architecture"] or "",
                cpu_model=row["cpu_model"] or "",
                cpu_cores_logical=row["cpu_cores_logical"] or 0,
                cpu_cores_physical=row["cpu_cores_physical"] or 0,
                ram_total_gb=row["ram_total_gb"] or 0.0,
                ram_available_gb=row["ram_available_gb"] or 0.0,
                uptime_hours=row["uptime_hours"] or 0.0,
                logged_in_user=row["logged_in_user"] or "",
                is_admin=bool(row["is_admin"]),
                disks=disks,
                network_interfaces=nets,
                installed_apps=apps,
            )

    def search_apps(self, query: str, snapshot_id: Optional[int] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{query}%"
            if snapshot_id is not None:
                cursor.execute("""
                    SELECT name, version, publisher, install_date, install_location
                    FROM inventory_apps
                    WHERE snapshot_id = ? AND (name LIKE ? OR publisher LIKE ?)
                    ORDER BY name ASC
                """, (snapshot_id, pattern, pattern))
            else:
                cursor.execute("""
                    SELECT name, version, publisher, install_date, install_location
                    FROM inventory_apps
                    WHERE name LIKE ? OR publisher LIKE ?
                    ORDER BY name ASC
                """, (pattern, pattern))
            return [dict(row) for row in cursor.fetchall()]

    # --- DIAGNOSTIC REPORTS ---

    def save_diagnostic_report(self, report: DiagnosticReport) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO diagnostic_reports (
                    report_type, title, status, summary, findings_json, recommendations_json, logs, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.report_type,
                report.title,
                report.status,
                report.summary,
                json.dumps(report.findings),
                json.dumps(report.recommendations),
                report.logs,
                report.created_at,
            ))
            conn.commit()
            report.id = cursor.lastrowid
            return report.id

    def get_recent_diagnostic_reports(self, limit: int = 10) -> List[DiagnosticReport]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM diagnostic_reports ORDER BY id DESC LIMIT ?
            """, (limit,))
            reports = []
            for r in cursor.fetchall():
                reports.append(DiagnosticReport(
                    id=r["id"],
                    report_type=r["report_type"],
                    title=r["title"],
                    status=r["status"],
                    summary=r["summary"],
                    findings=json.loads(r["findings_json"] or "[]"),
                    recommendations=json.loads(r["recommendations_json"] or "[]"),
                    logs=r["logs"] or "",
                    created_at=r["created_at"],
                ))
            return reports

    # --- AUTOMATION HISTORY ---

    def log_automation_start(self, task_id: str, task_name: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            entry = AutomationHistoryEntry(task_id=task_id, task_name=task_name, status="RUNNING")
            cursor.execute("""
                INSERT INTO automation_history (
                    task_id, task_name, status, started_at
                ) VALUES (?, ?, ?, ?)
            """, (entry.task_id, entry.task_name, entry.status, entry.started_at))
            conn.commit()
            return cursor.lastrowid

    def update_automation_entry(
        self,
        entry_id: int,
        status: str,
        completed_at: str,
        exit_code: int = 0,
        output_text: str = "",
        error_text: str = ""
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE automation_history
                SET status = ?, completed_at = ?, exit_code = ?, output_text = ?, error_text = ?
                WHERE id = ?
            """, (status, completed_at, exit_code, output_text, error_text, entry_id))
            conn.commit()

    def get_recent_automation_history(self, limit: int = 20) -> List[AutomationHistoryEntry]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM automation_history ORDER BY id DESC LIMIT ?
            """, (limit,))
            entries = []
            for r in cursor.fetchall():
                entries.append(AutomationHistoryEntry(
                    id=r["id"],
                    task_id=r["task_id"],
                    task_name=r["task_name"],
                    status=r["status"],
                    started_at=r["started_at"],
                    completed_at=r["completed_at"],
                    exit_code=r["exit_code"],
                    output_text=r["output_text"] or "",
                    error_text=r["error_text"] or "",
                ))
            return entries

