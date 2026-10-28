"""
Dashboard View
Modern dark-glass inspired dashboard displaying genuine, real-time system metrics,
network status, disk capacity, Windows Update health, recent reports, and automation status.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QProgressBar, QPushButton, QScrollArea, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from ..core.system_info import (
    get_cpu_info,
    get_memory_info,
    get_disks_info,
    get_system_uptime,
    get_windows_version_details,
    get_logged_in_user,
    is_admin
)
from ..core.network import get_default_gateway, test_http_connectivity
from ..core.diagnostics import inspect_windows_services
from ..database.database import Database


class DashboardCard(QFrame):
    """Reusable modern glass-style dashboard card widget."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardCard")
        self.setStyleSheet("""
            QFrame#DashboardCard {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 10px;
                padding: 12px;
            }
            QFrame#DashboardCard:hover {
                border: 1px solid #38bdf8;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 14, 16, 14)
        self.layout.setSpacing(10)

        # Title row
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 700; text-transform: uppercase;")
        self.layout.addWidget(self.title_label)


class DashboardView(QWidget):
    request_quick_action = Signal(str)

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db

        # Main scrollable layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(20)

        # Header Title and Action Bar
        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        h1 = QLabel("System Overview & Health Dashboard")
        h1.setStyleSheet("color: #f8fafc; font-size: 24px; font-weight: 700;")
        sub = QLabel("Real-time operational telemetrics, hardware health, and automation audit")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        header_text.addWidget(h1)
        header_text.addWidget(sub)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        self.btn_refresh = QPushButton("Refresh Telemetry")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #38bdf8;
                color: #0f172a;
            }
        """)
        self.btn_refresh.clicked.connect(self.refresh_metrics)
        header_layout.addWidget(self.btn_refresh)

        self.content_layout.addLayout(header_layout)

        # 3x2 Top Grid Cards
        grid = QGridLayout()
        grid.setSpacing(16)

        # 1. System Health / CPU Card
        self.card_cpu = DashboardCard("CPU & System Health")
        self.lbl_cpu_val = QLabel("0%")
        self.lbl_cpu_val.setStyleSheet("color: #38bdf8; font-size: 28px; font-weight: bold;")
        self.bar_cpu = QProgressBar()
        self.bar_cpu.setFixedHeight(8)
        self.bar_cpu.setTextVisible(False)
        self.bar_cpu.setStyleSheet("""
            QProgressBar { background-color: #1e293b; border-radius: 4px; }
            QProgressBar::chunk { background-color: #00d2ff; border-radius: 4px; }
        """)
        self.lbl_cpu_detail = QLabel("Analyzing...")
        self.lbl_cpu_detail.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.card_cpu.layout.addWidget(self.lbl_cpu_val)
        self.card_cpu.layout.addWidget(self.bar_cpu)
        self.card_cpu.layout.addWidget(self.lbl_cpu_detail)
        grid.addWidget(self.card_cpu, 0, 0)

        # 2. Memory Usage Card
        self.card_mem = DashboardCard("Memory (RAM) Status")
        self.lbl_mem_val = QLabel("0.0 GB")
        self.lbl_mem_val.setStyleSheet("color: #a855f7; font-size: 28px; font-weight: bold;")
        self.bar_mem = QProgressBar()
        self.bar_mem.setFixedHeight(8)
        self.bar_mem.setTextVisible(False)
        self.bar_mem.setStyleSheet("""
            QProgressBar { background-color: #1e293b; border-radius: 4px; }
            QProgressBar::chunk { background-color: #9d4edd; border-radius: 4px; }
        """)
        self.lbl_mem_detail = QLabel("Analyzing...")
        self.lbl_mem_detail.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.card_mem.layout.addWidget(self.lbl_mem_val)
        self.card_mem.layout.addWidget(self.bar_mem)
        self.card_mem.layout.addWidget(self.lbl_mem_detail)
        grid.addWidget(self.card_mem, 0, 1)

        # 3. Primary Disk Usage Card
        self.card_disk = DashboardCard("Primary Storage (C:)")
        self.lbl_disk_val = QLabel("0.0 GB")
        self.lbl_disk_val.setStyleSheet("color: #10b981; font-size: 28px; font-weight: bold;")
        self.bar_disk = QProgressBar()
        self.bar_disk.setFixedHeight(8)
        self.bar_disk.setTextVisible(False)
        self.bar_disk.setStyleSheet("""
            QProgressBar { background-color: #1e293b; border-radius: 4px; }
            QProgressBar::chunk { background-color: #10b981; border-radius: 4px; }
        """)
        self.lbl_disk_detail = QLabel("Analyzing...")
        self.lbl_disk_detail.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.card_disk.layout.addWidget(self.lbl_disk_val)
        self.card_disk.layout.addWidget(self.bar_disk)
        self.card_disk.layout.addWidget(self.lbl_disk_detail)
        grid.addWidget(self.card_disk, 0, 2)

        # 4. Network Status Card
        self.card_net = DashboardCard("Network Connectivity")
        self.lbl_net_status = QLabel("ONLINE")
        self.lbl_net_status.setStyleSheet("color: #10b981; font-size: 24px; font-weight: bold;")
        self.lbl_net_gw = QLabel("Gateway: Probing...")
        self.lbl_net_gw.setStyleSheet("color: #f1f5f9; font-size: 13px;")
        self.lbl_net_web = QLabel("Web Access: Probing...")
        self.lbl_net_web.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.card_net.layout.addWidget(self.lbl_net_status)
        self.card_net.layout.addWidget(self.lbl_net_gw)
        self.card_net.layout.addWidget(self.lbl_net_web)
        grid.addWidget(self.card_net, 1, 0)

        # 5. Windows Update & Security Card
        self.card_sec = DashboardCard("Windows Update & Privilege")
        self.lbl_sec_status = QLabel("ACTIVE")
        self.lbl_sec_status.setStyleSheet("color: #38bdf8; font-size: 24px; font-weight: bold;")
        self.lbl_sec_admin = QLabel("Admin Privileges: No")
        self.lbl_sec_admin.setStyleSheet("color: #f1f5f9; font-size: 13px;")
        self.lbl_sec_svc = QLabel("Update Service (wuauserv): Checking...")
        self.lbl_sec_svc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.card_sec.layout.addWidget(self.lbl_sec_status)
        self.card_sec.layout.addWidget(self.lbl_sec_admin)
        self.card_sec.layout.addWidget(self.lbl_sec_svc)
        grid.addWidget(self.card_sec, 1, 1)

        # 6. Device Identity & Uptime Card
        self.card_dev = DashboardCard("Device & Uptime")
        self.lbl_dev_host = QLabel("HOSTNAME")
        self.lbl_dev_host.setStyleSheet("color: #f1f5f9; font-size: 22px; font-weight: bold;")
        self.lbl_dev_os = QLabel("Windows")
        self.lbl_dev_os.setStyleSheet("color: #94a3b8; font-size: 13px;")
        self.lbl_dev_uptime = QLabel("Uptime: 0d 0h")
        self.lbl_dev_uptime.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 600;")
        self.card_dev.layout.addWidget(self.lbl_dev_host)
        self.card_dev.layout.addWidget(self.lbl_dev_os)
        self.card_dev.layout.addWidget(self.lbl_dev_uptime)
        grid.addWidget(self.card_dev, 1, 2)

        self.content_layout.addLayout(grid)

        # Quick Actions Row
        actions_card = DashboardCard("Instant Support Actions")
        actions_row = QHBoxLayout()

        btn_bundle = QPushButton("Generate IT Support Bundle")
        btn_bundle.setStyleSheet(self._action_button_style("#38bdf8"))
        btn_bundle.clicked.connect(lambda: self.request_quick_action.emit("prepare_support_bundle"))
        actions_row.addWidget(btn_bundle)

        btn_net_diag = QPushButton("Run Full Network Diagnostics")
        btn_net_diag.setStyleSheet(self._action_button_style("#10b981"))
        btn_net_diag.clicked.connect(lambda: self.request_quick_action.emit("run_network_diagnostics"))
        actions_row.addWidget(btn_net_diag)

        btn_flush = QPushButton("Flush DNS Cache")
        btn_flush.setStyleSheet(self._action_button_style("#a855f7"))
        btn_flush.clicked.connect(lambda: self.request_quick_action.emit("flush_dns_cache"))
        actions_row.addWidget(btn_flush)

        btn_disk_scan = QPushButton("Analyze Temporary Disk Space")
        btn_disk_scan.setStyleSheet(self._action_button_style("#f59e0b"))
        btn_disk_scan.clicked.connect(lambda: self.request_quick_action.emit("analyze_disk_space"))
        actions_row.addWidget(btn_disk_scan)

        actions_card.layout.addLayout(actions_row)
        self.content_layout.addWidget(actions_card)

        # Split Bottom Section: Recent Reports & Automation History
        bottom_layout = QHBoxLayout()

        # Recent Reports Table
        rep_box = DashboardCard("Recent Diagnostic Reports")
        self.table_reports = QTableWidget(0, 3)
        self.table_reports.setHorizontalHeaderLabels(["Timestamp", "Title", "Status"])
        self.table_reports.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_reports.setStyleSheet(self._table_style())
        self.table_reports.setFixedHeight(200)
        rep_box.layout.addWidget(self.table_reports)
        bottom_layout.addWidget(rep_box)

        # Recent Automation Activity
        auto_box = DashboardCard("Recent Automation History")
        self.table_auto = QTableWidget(0, 3)
        self.table_auto.setHorizontalHeaderLabels(["Started", "Task Name", "Result"])
        self.table_auto.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_auto.setStyleSheet(self._table_style())
        self.table_auto.setFixedHeight(200)
        auto_box.layout.addWidget(self.table_auto)
        bottom_layout.addWidget(auto_box)

        self.content_layout.addLayout(bottom_layout)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Periodic refresh timer (every 10 seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_metrics)
        self.timer.start(10000)

        # Initial data population
        self.refresh_metrics()

    def _action_button_style(self, accent_color: str) -> str:
        return f"""
            QPushButton {{
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid {accent_color};
                border-radius: 6px;
                padding: 10px 14px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {accent_color};
                color: #0f172a;
            }}
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
            QTableWidget::item {
                padding: 6px;
            }
        """

    def refresh_metrics(self):
        """Fetches real metrics and updates all dashboard widgets."""
        # CPU
        cpu = get_cpu_info()
        usage = cpu["current_usage_percent"]
        self.lbl_cpu_val.setText(f"{usage}%")
        self.bar_cpu.setValue(int(usage))
        self.lbl_cpu_detail.setText(f"{cpu['cores_logical']} Cores | {cpu['model'][:35]}")

        # Memory
        mem = get_memory_info()
        self.lbl_mem_val.setText(f"{mem['used_gb']} GB")
        self.bar_mem.setValue(int(mem['percent_used']))
        self.lbl_mem_detail.setText(f"{mem['percent_used']}% of {mem['total_gb']} GB RAM in use")

        # Disk C:
        disks = get_disks_info()
        c_drive = next((d for d in disks if d.mountpoint.upper().startswith("C:")), None)
        if c_drive:
            self.lbl_disk_val.setText(f"{c_drive.free_gb} GB Free")
            self.bar_disk.setValue(int(c_drive.percent_used))
            self.lbl_disk_detail.setText(f"{c_drive.used_gb} GB used of {c_drive.total_gb} GB ({c_drive.percent_used}%)")
        elif disks:
            d = disks[0]
            self.lbl_disk_val.setText(f"{d.free_gb} GB Free")
            self.bar_disk.setValue(int(d.percent_used))
            self.lbl_disk_detail.setText(f"{d.used_gb} GB used of {d.total_gb} GB")

        # Network
        gw = get_default_gateway() or "None"
        self.lbl_net_gw.setText(f"Default Gateway: {gw}")
        web_check = test_http_connectivity(timeout_sec=2)
        if web_check["success"]:
            self.lbl_net_status.setText("ONLINE")
            self.lbl_net_status.setStyleSheet("color: #10b981; font-size: 24px; font-weight: bold;")
            self.lbl_net_web.setText(f"Web Ping: {web_check['latency_ms']} ms")
        else:
            self.lbl_net_status.setText("OFFLINE / DEGRADED")
            self.lbl_net_status.setStyleSheet("color: #ef4444; font-size: 24px; font-weight: bold;")
            self.lbl_net_web.setText("HTTP check unreachable")

        # Security & Privileges
        admin = is_admin()
        self.lbl_sec_admin.setText(f"Session Privilege: {'Elevated (Admin)' if admin else 'Standard User'}")
        if admin:
            self.lbl_sec_admin.setStyleSheet("color: #10b981; font-weight: 600;")
        else:
            self.lbl_sec_admin.setStyleSheet("color: #f59e0b; font-weight: 600;")

        # Update service
        svcs = inspect_windows_services()
        wu = svcs["services"].get("wuauserv", {})
        self.lbl_sec_svc.setText(f"Update Service: {wu.get('status', 'running').upper()}")

        # Device info & Uptime
        os_info = get_windows_version_details()
        uptime = get_system_uptime()
        import socket
        self.lbl_dev_host.setText(socket.gethostname())
        self.lbl_dev_os.setText(f"{os_info['os_name']} (Build {os_info['os_build']})")
        self.lbl_dev_uptime.setText(f"Uptime: {uptime['formatted']}")

        # Populate Recent Reports
        reports = self.db.get_recent_diagnostic_reports(limit=6)
        self.table_reports.setRowCount(len(reports))
        for row, rep in enumerate(reports):
            t_item = QTableWidgetItem(rep.created_at[:19].replace("T", " "))
            title_item = QTableWidgetItem(rep.title)
            status_item = QTableWidgetItem(rep.status)

            if rep.status == "PASS":
                status_item.setForeground(Qt.green)
            elif rep.status == "WARNING":
                status_item.setForeground(Qt.yellow)
            elif rep.status == "CRITICAL":
                status_item.setForeground(Qt.red)

            self.table_reports.setItem(row, 0, t_item)
            self.table_reports.setItem(row, 1, title_item)
            self.table_reports.setItem(row, 2, status_item)

        # Populate Automation History
        history = self.db.get_recent_automation_history(limit=6)
        self.table_auto.setRowCount(len(history))
        for row, entry in enumerate(history):
            start_item = QTableWidgetItem(entry.started_at[:19].replace("T", " "))
            name_item = QTableWidgetItem(entry.task_name)
            res_item = QTableWidgetItem(entry.status)

            if entry.status == "SUCCESS":
                res_item.setForeground(Qt.green)
            elif entry.status == "CANCELLED":
                res_item.setForeground(Qt.yellow)
            else:
                res_item.setForeground(Qt.red)

            self.table_auto.setItem(row, 0, start_item)
            self.table_auto.setItem(row, 1, name_item)
            self.table_auto.setItem(row, 2, res_item)

