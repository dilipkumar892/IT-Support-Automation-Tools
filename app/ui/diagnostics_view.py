"""
Diagnostics & Troubleshooting View
Provides targeted troubleshooting tools for Windows: SFC, DISM, Event Log Auditing,
Disk Cleanup Analysis, Windows Update diagnostics, and Startup inspection.
Includes strict confirmation prompts, risk assessments, and permission validation.
"""

from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFrame, QProgressBar, QSplitter,
    QApplication
)
from PySide6.QtCore import Qt, QThread, Signal

from ..core.safety import is_admin, RiskLevel, elevate_process
from ..core.diagnostics import (
    run_sfc_scan,
    run_dism_health,
    analyze_disk_cleanup_targets,
    inspect_windows_services,
    inspect_startup_programs,
    collect_recent_event_log_errors,
    get_top_resource_consumers,
    fix_print_spooler_service,
    reset_network_adapter_and_stack,
    reset_windows_update_agent,
    generate_battery_report,
    clean_junk_files,
    audit_domain_and_identity,
    audit_bitlocker_status,
    generate_itsm_ticket_payload
)
from ..database.database import Database
from ..database.models import DiagnosticReport


class DiagnosticsWorker(QThread):
    finished = Signal(dict)

    def __init__(self, target_func, *args, **kwargs):
        super().__init__()
        self.target_func = target_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.target_func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"success": False, "error": str(e)})


class DiagnosticsView(QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.worker: Optional[DiagnosticsWorker] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        h1 = QLabel("Windows Troubleshooting & Diagnostics")
        h1.setStyleSheet("color: #f8fafc; font-size: 24px; font-weight: 700;")
        sub = QLabel("Verified diagnostic scans, component store repairs, event log audits, and service inspection")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(h1)
        layout.addWidget(sub)

        # Tabs for categories
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #1f2937;
                background: #0f172a;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #111827;
                color: #94a3b8;
                padding: 10px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #1e293b;
                color: #38bdf8;
                border-bottom: 2px solid #38bdf8;
            }
        """)

        # Add Tab Pages
        self.tabs.addTab(self._build_sfc_dism_tab(), "System Integrity (SFC/DISM)")
        self.tabs.addTab(self._build_repair_tools_tab(), "Repairs & Print Doctor (UAC)")
        self.tabs.addTab(self._build_identity_security_tab(), "Identity & BitLocker")
        self.tabs.addTab(self._build_battery_cleanup_tab(), "Battery & Cleanup")
        self.tabs.addTab(self._build_event_logs_tab(), "Event Log Audit")
        self.tabs.addTab(self._build_services_tab(), "Windows Services & Updates")
        self.tabs.addTab(self._build_startup_tab(), "Startup & Performance")
        self.tabs.addTab(self._build_ticket_tab(), "ITSM Ticket Packager")

        layout.addWidget(self.tabs)

        # Progress / Output Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #1e293b; border-radius: 3px; }
            QProgressBar::chunk { background: #38bdf8; border-radius: 3px; }
        """)
        layout.addWidget(self.progress_bar)

    # 1. SFC & DISM Tab
    def _build_sfc_dism_tab(self) -> QWidget:
        widget = QWidget()
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        intro = QLabel("System File Checker (SFC) and Deployment Image Servicing and Management (DISM)")
        intro.setStyleSheet("color: #cbd5e1; font-weight: 600;")
        l.addWidget(intro)

        btn_row = QHBoxLayout()

        btn_sfc_chk = QPushButton("SFC Verify Only (Read-Only)")
        btn_sfc_chk.setStyleSheet(self._btn_style("#38bdf8"))
        btn_sfc_chk.clicked.connect(lambda: self._run_task("sfc_verify", run_sfc_scan, False))
        btn_row.addWidget(btn_sfc_chk)

        btn_sfc_rep = QPushButton("SFC Repair (/scannow)")
        btn_sfc_rep.setStyleSheet(self._btn_style("#ef4444"))
        btn_sfc_rep.clicked.connect(self._confirm_and_run_sfc_repair)
        btn_row.addWidget(btn_sfc_rep)

        btn_dism_chk = QPushButton("DISM Check Health")
        btn_dism_chk.setStyleSheet(self._btn_style("#a855f7"))
        btn_dism_chk.clicked.connect(lambda: self._run_task("dism_check", run_dism_health, "check"))
        btn_row.addWidget(btn_dism_chk)

        btn_dism_scan = QPushButton("DISM Scan Health")
        btn_dism_scan.setStyleSheet(self._btn_style("#f59e0b"))
        btn_dism_scan.clicked.connect(lambda: self._run_task("dism_scan", run_dism_health, "scan"))
        btn_row.addWidget(btn_dism_scan)

        btn_dism_res = QPushButton("DISM Restore Health")
        btn_dism_res.setStyleSheet(self._btn_style("#ef4444"))
        btn_dism_res.clicked.connect(self._confirm_and_run_dism_restore)
        btn_row.addWidget(btn_dism_res)

        l.addLayout(btn_row)

        self.txt_sfc_output = QTextEdit()
        self.txt_sfc_output.setReadOnly(True)
        self.txt_sfc_output.setPlaceholderText("Execution output and results will appear here...")
        self.txt_sfc_output.setStyleSheet(self._console_style())
        l.addWidget(self.txt_sfc_output)

        return widget

    # 2. Event Logs Tab
    def _build_event_logs_tab(self) -> QWidget:
        widget = QWidget()
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        top_row = QHBoxLayout()
        lbl = QLabel("Recent System Critical and Error Events (Last 24 Hours)")
        lbl.setStyleSheet("color: #cbd5e1; font-weight: 600;")
        top_row.addWidget(lbl)
        top_row.addStretch()

        btn_fetch = QPushButton("Audit Event Logs")
        btn_fetch.setStyleSheet(self._btn_style("#38bdf8"))
        btn_fetch.clicked.connect(self._refresh_event_logs)
        top_row.addWidget(btn_fetch)
        l.addLayout(top_row)

        self.table_events = QTableWidget(0, 4)
        self.table_events.setHorizontalHeaderLabels(["Timestamp", "Source", "Event ID", "Details"])
        self.table_events.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_events.setStyleSheet(self._table_style())
        l.addWidget(self.table_events)

        return widget

    # 3. Services & Windows Updates Tab
    def _build_services_tab(self) -> QWidget:
        widget = QWidget()
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        top_row = QHBoxLayout()
        lbl = QLabel("Core Windows Services & Windows Update Client Status")
        lbl.setStyleSheet("color: #cbd5e1; font-weight: 600;")
        top_row.addWidget(lbl)
        top_row.addStretch()

        btn_fetch_svc = QPushButton("Inspect Services")
        btn_fetch_svc.setStyleSheet(self._btn_style("#38bdf8"))
        btn_fetch_svc.clicked.connect(self._refresh_services)
        top_row.addWidget(btn_fetch_svc)
        l.addLayout(top_row)

        self.table_services = QTableWidget(0, 3)
        self.table_services.setHorizontalHeaderLabels(["Service Name", "Display Name", "Current Status"])
        self.table_services.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_services.setStyleSheet(self._table_style())
        l.addWidget(self.table_services)

        return widget

    # 4. Startup & Performance Tab
    def _build_startup_tab(self) -> QWidget:
        widget = QWidget()
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        top_row = QHBoxLayout()
        lbl = QLabel("Startup Applications and Top Resource Consuming Processes")
        lbl.setStyleSheet("color: #cbd5e1; font-weight: 600;")
        top_row.addWidget(lbl)
        top_row.addStretch()

        btn_perf = QPushButton("Refresh Performance Metrics")
        btn_perf.setStyleSheet(self._btn_style("#38bdf8"))
        btn_perf.clicked.connect(self._refresh_performance)
        top_row.addWidget(btn_perf)
        l.addLayout(top_row)

        splitter = QSplitter(Qt.Vertical)

        # Startup Apps Table
        box_startup = QWidget()
        l_start = QVBoxLayout(box_startup)
        l_start.setContentsMargins(0, 0, 0, 0)
        lbl_s = QLabel("Registered Startup Programs (Registry Run Keys):")
        lbl_s.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        l_start.addWidget(lbl_s)
        self.table_startup = QTableWidget(0, 3)
        self.table_startup.setHorizontalHeaderLabels(["Application", "Scope", "Command Line"])
        self.table_startup.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_startup.setStyleSheet(self._table_style())
        l_start.addWidget(self.table_startup)
        splitter.addWidget(box_startup)

        # Top processes Table
        box_procs = QWidget()
        l_proc = QVBoxLayout(box_procs)
        l_proc.setContentsMargins(0, 0, 0, 0)
        lbl_p = QLabel("Top Resource Consuming Processes:")
        lbl_p.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        l_proc.addWidget(lbl_p)
        self.table_procs = QTableWidget(0, 4)
        self.table_procs.setHorizontalHeaderLabels(["PID", "Process Name", "CPU %", "Memory %"])
        self.table_procs.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_procs.setStyleSheet(self._table_style())
        l_proc.addWidget(self.table_procs)
        splitter.addWidget(box_procs)

        l.addWidget(splitter)
        return widget

    def _btn_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid {color};
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {color};
                color: #0f172a;
            }}
        """

    def _console_style(self) -> str:
        return """
            QTextEdit {
                background-color: #060911;
                border: 1px solid #1f2937;
                border-radius: 6px;
                color: #7dd3fc;
                font-family: "Cascadia Code", Consolas, Monaco, monospace;
                font-size: 12px;
                padding: 10px;
            }
        """

    def _table_style(self) -> str:
        return """
            QTableWidget {
                background-color: #0d131f;
                border: 1px solid #1f2937;
                border-radius: 6px;
                color: #f8fafc;
                gridline-color: #1e293b;
            }
            QHeaderView::section {
                background-color: #162032;
                color: #38bdf8;
                padding: 6px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
        """

    def _confirm_and_run_sfc_repair(self):
        if not is_admin():
            reply = QMessageBox.question(
                self,
                "Elevation Required",
                "Administrator privileges are required to run SFC repair.\n\n"
                "Would you like to relaunch the application as Administrator now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                elevate_process(exit_current=True)
            return

        reply = QMessageBox.question(
            self,
            "Confirm SFC System File Repair",
            "Are you sure you want to run 'sfc /scannow'?\n\n"
            "This will scan and automatically repair corrupted protected Windows system files.\n"
            "This operation may take several minutes.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._run_task("sfc_repair", run_sfc_scan, True)

    def _confirm_and_run_dism_restore(self):
        if not is_admin():
            reply = QMessageBox.question(
                self,
                "Elevation Required",
                "Administrator privileges are required to run DISM restore.\n\n"
                "Would you like to relaunch the application as Administrator now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                elevate_process(exit_current=True)
            return

        reply = QMessageBox.question(
            self,
            "Confirm DISM Component Store Restore",
            "Are you sure you want to execute 'DISM /Online /Cleanup-Image /RestoreHealth'?\n\n"
            "This scans for component store corruption and uses Windows Update to repair corrupted files.\n"
            "This process requires an active internet connection and may take 5 to 15 minutes.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._run_task("dism_restore", run_dism_health, "restore")

    def _run_task(self, name: str, func, *args):
        self.progress_bar.setVisible(True)
        self.txt_sfc_output.setText(f"Executing {name}... Please wait.\n")

        self.worker = DiagnosticsWorker(func, *args)
        self.worker.finished.connect(self._on_task_finished)
        self.worker.start()

    def _on_task_finished(self, result: dict):
        self.progress_bar.setVisible(False)
        output = result.get("output") or result.get("summary") or result.get("error") or str(result)
        self.txt_sfc_output.setText(output)

    def _refresh_event_logs(self):
        events = collect_recent_event_log_errors()
        self.table_events.setRowCount(len(events))
        for row, evt in enumerate(events):
            self.table_events.setItem(row, 0, QTableWidgetItem(evt.get("date", "Unknown")))
            self.table_events.setItem(row, 1, QTableWidgetItem(evt.get("source", "Unknown")))
            self.table_events.setItem(row, 2, QTableWidgetItem(str(evt.get("event_id", "Unknown"))))
            self.table_events.setItem(row, 3, QTableWidgetItem(evt.get("raw", "")[:250]))

    def _refresh_services(self):
        data = inspect_windows_services()
        services = data.get("services", {})
        self.table_services.setRowCount(len(services))
        for row, (k, s) in enumerate(services.items()):
            self.table_services.setItem(row, 0, QTableWidgetItem(k))
            self.table_services.setItem(row, 1, QTableWidgetItem(s.get("display_name", k)))
            status_item = QTableWidgetItem(s.get("status", "unknown").upper())
            if s.get("status") == "running":
                status_item.setForeground(Qt.green)
            else:
                status_item.setForeground(Qt.yellow)
            self.table_services.setItem(row, 2, status_item)

    def _refresh_performance(self):
        # Startup apps
        startups = inspect_startup_programs()
        self.table_startup.setRowCount(len(startups))
        for row, app in enumerate(startups):
            self.table_startup.setItem(row, 0, QTableWidgetItem(app.get("name", "")))
            self.table_startup.setItem(row, 1, QTableWidgetItem(app.get("scope", "")))
            self.table_startup.setItem(row, 2, QTableWidgetItem(app.get("command", "")))

        # Top processes
        consumers = get_top_resource_consumers()
        top_cpu = consumers.get("top_cpu", [])
        self.table_procs.setRowCount(len(top_cpu))
        for row, proc in enumerate(top_cpu):
            self.table_procs.setItem(row, 0, QTableWidgetItem(str(proc.get("pid"))))
            self.table_procs.setItem(row, 1, QTableWidgetItem(proc.get("name", "Unknown")))
            self.table_procs.setItem(row, 2, QTableWidgetItem(f"{proc.get('cpu_percent', 0.0)}%"))
            self.table_procs.setItem(row, 3, QTableWidgetItem(f"{round(proc.get('memory_percent', 0.0), 1)}%"))

    # 5. Repairs & Print Doctor Tab (UAC Required)
    def _build_repair_tools_tab(self) -> QWidget:
        widget = QWidget()
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        intro = QLabel("High-Impact Service & Stack Remediation (Requires Administrator Elevation)")
        intro.setStyleSheet("color: #cbd5e1; font-weight: 600;")
        l.addWidget(intro)

        btn_row = QHBoxLayout()

        btn_spool = QPushButton("Fix Print Spooler (Purge Queue)")
        btn_spool.setStyleSheet(self._btn_style("#00d2ff"))
        btn_spool.clicked.connect(self._run_print_spooler_fix)
        btn_row.addWidget(btn_spool)

        btn_net_rst = QPushButton("Reset Network Stack & Winsock")
        btn_net_rst.setStyleSheet(self._btn_style("#f59e0b"))
        btn_net_rst.clicked.connect(self._run_network_stack_reset)
        btn_row.addWidget(btn_net_rst)

        btn_wu_rst = QPushButton("Reset Windows Update Agent")
        btn_wu_rst.setStyleSheet(self._btn_style("#a855f7"))
        btn_wu_rst.clicked.connect(self._run_wu_reset)
        btn_row.addWidget(btn_wu_rst)

        l.addLayout(btn_row)

        self.txt_repair_output = QTextEdit()
        self.txt_repair_output.setReadOnly(True)
        self.txt_repair_output.setPlaceholderText("Remediation execution logs will appear here...")
        self.txt_repair_output.setStyleSheet(self._console_style())
        l.addWidget(self.txt_repair_output)

        return widget

    def _run_print_spooler_fix(self):
        if not is_admin():
            reply = QMessageBox.question(
                self,
                "Elevation Required",
                "Administrator privileges are required to stop and clear the Print Spooler.\n\n"
                "Would you like to relaunch the application as Administrator now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                elevate_process(exit_current=True)
            return

        self.txt_repair_output.setText("Stopping spooler service, purging PRINTERS queue, and restarting...\n")
        self.progress_bar.setVisible(True)
        self.worker = DiagnosticsWorker(fix_print_spooler_service)
        self.worker.finished.connect(lambda res: self._on_repair_finished("Print Spooler", res))
        self.worker.start()

    def _run_network_stack_reset(self):
        if not is_admin():
            reply = QMessageBox.question(
                self,
                "Elevation Required",
                "Administrator privileges are required to reset the network stack and Winsock catalog.\n\n"
                "Would you like to relaunch the application as Administrator now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                elevate_process(exit_current=True)
            return

        reply = QMessageBox.question(
            self,
            "Confirm Network Reset",
            "This will flush the DNS cache, reset the Winsock catalog, and reset TCP/IP.\n"
            "Active network connections may temporarily disconnect.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.txt_repair_output.setText("Executing TCP/IP & Winsock catalog reset...\n")
            self.progress_bar.setVisible(True)
            self.worker = DiagnosticsWorker(reset_network_adapter_and_stack)
            self.worker.finished.connect(lambda res: self._on_repair_finished("Network Stack", res))
            self.worker.start()

    def _run_wu_reset(self):
        if not is_admin():
            reply = QMessageBox.question(
                self,
                "Elevation Required",
                "Administrator privileges are required to reset Windows Update components.\n\n"
                "Would you like to relaunch the application as Administrator now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                elevate_process(exit_current=True)
            return

        self.txt_repair_output.setText("Stopping update services, clearing download cache, and restarting...\n")
        self.progress_bar.setVisible(True)
        self.worker = DiagnosticsWorker(reset_windows_update_agent)
        self.worker.finished.connect(lambda res: self._on_repair_finished("Windows Update", res))
        self.worker.start()

    def _on_repair_finished(self, name: str, res: dict):
        self.progress_bar.setVisible(False)
        output = res.get("output") or res.get("message") or str(res)
        self.txt_repair_output.append(f"[{name}] {output}")

    # 6. Identity & Security Tab
    def _build_identity_security_tab(self) -> QWidget:
        widget = QWidget()
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        top_row = QHBoxLayout()
        lbl = QLabel("Active Directory, Entra ID (Azure AD), and BitLocker Status")
        lbl.setStyleSheet("color: #cbd5e1; font-weight: 600;")
        top_row.addWidget(lbl)
        top_row.addStretch()

        btn_ident = QPushButton("Audit Domain & Identity")
        btn_ident.setStyleSheet(self._btn_style("#38bdf8"))
        btn_ident.clicked.connect(self._run_identity_audit)
        top_row.addWidget(btn_ident)

        btn_bit = QPushButton("Audit BitLocker (UAC)")
        btn_bit.setStyleSheet(self._btn_style("#a855f7"))
        btn_bit.clicked.connect(self._run_bitlocker_audit)
        top_row.addWidget(btn_bit)

        l.addLayout(top_row)

        self.txt_identity_output = QTextEdit()
        self.txt_identity_output.setReadOnly(True)
        self.txt_identity_output.setPlaceholderText("Domain trust and BitLocker telemetry will appear here...")
        self.txt_identity_output.setStyleSheet(self._console_style())
        l.addWidget(self.txt_identity_output)

        return widget

    def _run_identity_audit(self):
        data = audit_domain_and_identity()
        out = (
            f"=== WORKSTATION IDENTITY & TRUST AUDIT ===\n"
            f"Domain / Workgroup: {data['domain_name']}\n"
            f"Domain Joined:      {'YES' if data['domain_joined'] else 'NO (Workgroup)'}\n"
            f"Entra ID Joined:    {'YES' if data['azure_ad_joined'] else 'NO'}\n"
            f"Tenant Name:        {data['tenant_name'] or 'None'}\n"
            f"User Principal Name:{data['user_upn'] or 'None'}\n"
        )
        self.txt_identity_output.setText(out)

    def _run_bitlocker_audit(self):
        if not is_admin():
            reply = QMessageBox.question(
                self,
                "Elevation Required",
                "Administrator privileges are required to inspect BitLocker drive encryption.\n\n"
                "Would you like to relaunch as Administrator now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                elevate_process(exit_current=True)
            return

        res = audit_bitlocker_status()
        self.txt_identity_output.setText(res.get("output") or res.get("summary") or res.get("message"))

    # 7. Battery & Junk Cleanup Tab
    def _build_battery_cleanup_tab(self) -> QWidget:
        widget = QWidget()
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        btn_row = QHBoxLayout()

        btn_bat = QPushButton("Generate Battery Wear Report")
        btn_bat.setStyleSheet(self._btn_style("#10b981"))
        btn_bat.clicked.connect(self._run_battery_report)
        btn_row.addWidget(btn_bat)

        btn_user_clean = QPushButton("Clean User Temp (%TEMP%)")
        btn_user_clean.setStyleSheet(self._btn_style("#38bdf8"))
        btn_user_clean.clicked.connect(lambda: self._run_cleanup(False))
        btn_row.addWidget(btn_user_clean)

        btn_sys_clean = QPushButton("Clean System Temp & Logs (UAC)")
        btn_sys_clean.setStyleSheet(self._btn_style("#f59e0b"))
        btn_sys_clean.clicked.connect(lambda: self._run_cleanup(True))
        btn_row.addWidget(btn_sys_clean)

        l.addLayout(btn_row)

        self.txt_cleanup_output = QTextEdit()
        self.txt_cleanup_output.setReadOnly(True)
        self.txt_cleanup_output.setPlaceholderText("Battery health degradation and cleanup statistics will appear here...")
        self.txt_cleanup_output.setStyleSheet(self._console_style())
        l.addWidget(self.txt_cleanup_output)

        return widget

    def _run_battery_report(self):
        self.txt_cleanup_output.setText("Analyzing laptop battery capacity...\n")
        bat = generate_battery_report()
        if bat.get("has_battery"):
            out = (
                f"=== LAPTOP BATTERY HEALTH ASSESSMENT ===\n"
                f"Design Capacity:       {bat['design_capacity_mwh']} mWh\n"
                f"Full Charge Capacity:  {bat['full_charge_capacity_mwh']} mWh\n"
                f"Battery Wear Level:    {bat['battery_wear_percent']}%\n"
                f"Cycle Count:           {bat.get('cycle_count') or 'Unknown'}\n"
                f"Health Status:         {bat['health_assessment']}\n"
            )
        else:
            out = f"=== BATTERY REPORT ===\n{bat['health_assessment']}\n"
        self.txt_cleanup_output.setText(out)

    def _run_cleanup(self, system_level: bool):
        if system_level and not is_admin():
            reply = QMessageBox.question(
                self,
                "Elevation Required",
                "Administrator privileges are required for system-level temp file purging.\n\n"
                "Would you like to relaunch as Administrator now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                elevate_process(exit_current=True)
            return

        res = clean_junk_files(system_level=system_level)
        self.txt_cleanup_output.setText(f"=== CLEANUP SUMMARY ===\n{res['message']}")

    # 8. ITSM Ticket Generator Tab
    def _build_ticket_tab(self) -> QWidget:
        widget = QWidget()
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        top_row = QHBoxLayout()
        lbl = QLabel("Pre-Formatted IT Support Ticket Content (ServiceNow / Jira / Plain Text)")
        lbl.setStyleSheet("color: #cbd5e1; font-weight: 600;")
        top_row.addWidget(lbl)
        top_row.addStretch()

        btn_gen = QPushButton("Compile Ticket Template")
        btn_gen.setStyleSheet(self._btn_style("#38bdf8"))
        btn_gen.clicked.connect(self._compile_ticket)
        top_row.addWidget(btn_gen)

        btn_copy = QPushButton("📋 Copy to Clipboard")
        btn_copy.setStyleSheet(self._btn_style("#00d2ff"))
        btn_copy.clicked.connect(self._copy_ticket_clipboard)
        top_row.addWidget(btn_copy)

        l.addLayout(top_row)

        self.txt_ticket_output = QTextEdit()
        self.txt_ticket_output.setReadOnly(True)
        self.txt_ticket_output.setStyleSheet(self._console_style())
        l.addWidget(self.txt_ticket_output)

        return widget

    def _compile_ticket(self):
        payload = generate_itsm_ticket_payload()
        self.txt_ticket_output.setText(payload["markdown"])

    def _copy_ticket_clipboard(self):
        text = self.txt_ticket_output.toPlainText()
        if not text:
            self._compile_ticket()
            text = self.txt_ticket_output.toPlainText()
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Ticket summary copied to clipboard successfully!")

