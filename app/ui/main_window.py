"""
Main Window for IT Support Automation Suite
Provides modern dark-mode UI with sleek sidebar navigation, neon accents,
glassmorphic styling, responsive layouts, and interconnected views.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QStatusBar, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont

from .dashboard import DashboardView
from .inventory_view import InventoryView
from .diagnostics_view import DiagnosticsView
from .automation_view import AutomationView
from .settings_view import SettingsView
from ..core.automation import AutomationTaskRunner
from ..core.safety import is_admin, elevate_process
from ..database.database import Database


class MainWindow(QMainWindow):
    def __init__(self, db: Database, runner: AutomationTaskRunner):
        super().__init__()
        self.db = db
        self.runner = runner

        self.setWindowTitle("IT Support Automation Suite - Enterprise Edition")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 680)

        # Apply Global Dark Neon Stylesheet
        self.setStyleSheet(self._global_stylesheet())

        # Main Central Layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Main Stacked Views (initialized before sidebar selection)
        self.stack = QStackedWidget()
        self.view_dashboard = DashboardView(self.db)
        self.view_inventory = InventoryView(self.db)
        self.view_diagnostics = DiagnosticsView(self.db)
        self.view_automation = AutomationView(self.db, self.runner)
        self.view_settings = SettingsView()

        self.stack.addWidget(self.view_dashboard)       # index 0
        self.stack.addWidget(self.view_inventory)       # index 1
        self.stack.addWidget(self.view_diagnostics)     # index 2
        self.stack.addWidget(self.view_automation)      # index 3
        self.stack.addWidget(self.view_settings)        # index 4

        # 2. Sidebar Navigation
        self.sidebar = self._build_sidebar()
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

        # Connect Dashboard Quick Action Signals to Automation Tab
        self.view_dashboard.request_quick_action.connect(self._handle_quick_action)

        # 3. Status Bar
        self._setup_statusbar()

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(230)
        sidebar.setObjectName("SidebarFrame")
        sidebar.setStyleSheet("""
            QFrame#SidebarFrame {{
                background-color: #0b0f19;
                border-right: 1px solid #1e293b;
            }}
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 20, 14, 20)
        layout.setSpacing(8)

        # Brand Logo / Title
        brand_box = QVBoxLayout()
        logo_lbl = QLabel("IT AUTOMATION")
        logo_lbl.setStyleSheet("""
            font-size: 18px;
            font-weight: 900;
            letter-spacing: 1.5px;
            color: #00d2ff;
        """)
        tag_lbl = QLabel("Enterprise Support Suite v1.0")
        tag_lbl.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 600;")
        brand_box.addWidget(logo_lbl)
        brand_box.addWidget(tag_lbl)
        layout.addLayout(brand_box)

        layout.addSpacing(24)

        # Nav Buttons
        self.nav_buttons = []

        btn_dash = self._create_nav_button("📊  Dashboard", 0)
        btn_inv = self._create_nav_button("💻  Asset Inventory", 1)
        btn_diag = self._create_nav_button("🔧  Windows Diagnostics", 2)
        btn_auto = self._create_nav_button("⚡  Automation Engine", 3)
        btn_set = self._create_nav_button("⚙️  Settings", 4)

        for btn in [btn_dash, btn_inv, btn_diag, btn_auto, btn_set]:
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        # Session Badge & Elevation Button at Sidebar bottom
        admin = is_admin()
        badge_text = "🛡️ ADMIN ELEVATED" if admin else "👤 STANDARD USER"
        badge_color = "#10b981" if admin else "#f59e0b"
        badge = QLabel(badge_text)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid {badge_color};
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 11px;
            font-weight: 700;
            color: {badge_color};
        """)
        layout.addWidget(badge)

        if not admin:
            btn_elevate = QPushButton("⚡ Elevate to Admin")
            btn_elevate.setCursor(Qt.PointingHandCursor)
            btn_elevate.setStyleSheet("""
                QPushButton {
                    background: linear-gradient(135deg, #00d2ff, #7928ca);
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 9px 12px;
                    font-size: 12px;
                    font-weight: 700;
                    margin-top: 4px;
                }
                QPushButton:hover {
                    background: #00d2ff;
                    color: #090d16;
                }
            """)
            btn_elevate.clicked.connect(self._request_elevation)
            layout.addWidget(btn_elevate)

        # Select dashboard by default
        self._select_nav(0)
        return sidebar

    def _request_elevation(self):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Request Administrator Elevation",
            "Would you like to relaunch the IT Support Automation Suite with full Administrator privileges?\n\n"
            "This will trigger a Windows User Account Control (UAC) prompt and unlock:\n"
            "• SFC System File Repair (/scannow)\n"
            "• DISM Component Store Online Restoration\n"
            "• Advanced Service Controls & DNS Cache Flush\n"
            "• Unrestricted Registry Access",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            success = elevate_process(exit_current=True)
            if not success:
                QMessageBox.warning(
                    self,
                    "Elevation Cancelled",
                    "Administrator elevation was cancelled or not granted."
                )

    def _create_nav_button(self, text: str, index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(self._nav_btn_style())
        btn.clicked.connect(lambda: self._select_nav(index))
        return btn

    def _nav_btn_style(self) -> str:
        return """
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                border-radius: 6px;
                padding: 10px 14px;
                text-align: left;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1e293b;
                color: #f1f5f9;
            }
            QPushButton:checked {
                background: #1e293b;
                color: #00d2ff;
                border-left: 3px solid #00d2ff;
                font-weight: 700;
            }
        """

    def _select_nav(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _handle_quick_action(self, task_id: str):
        # Switch to automation tab and trigger task
        self._select_nav(3)
        self.view_automation.trigger_task_by_id(task_id)

    def _setup_statusbar(self):
        status = QStatusBar()
        status.setStyleSheet("""
            QStatusBar {
                background-color: #0b0f19;
                color: #64748b;
                border-top: 1px solid #1e293b;
                font-size: 12px;
                padding: 4px 12px;
            }
        """)
        self.setStatusBar(status)

        status.showMessage("Ready. System monitors active.")

        # Permanent widgets
        db_label = QLabel("Database: Connected (SQLite)")
        db_label.setStyleSheet("color: #10b981; font-size: 11px; margin-right: 15px;")
        status.addPermanentWidget(db_label)

        ver_label = QLabel("Suite v1.0.0")
        ver_label.setStyleSheet("color: #64748b; font-size: 11px;")
        status.addPermanentWidget(ver_label)

    def _global_stylesheet(self) -> str:
        return """
            QMainWindow, QWidget {
                background-color: #090d16;
                color: #f8fafc;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            }
            QScrollBar:vertical {
                border: none;
                background: #0b0f19;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #1e293b;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """
