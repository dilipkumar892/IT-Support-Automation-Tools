"""
Settings and Configuration View
Allows IT engineers to inspect safety policies, adjust execution timeouts,
view active allowlisted tasks, and toggle UI preferences.
"""

import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QSpinBox, QPushButton, QFrame, QScrollArea, QMessageBox,
    QListWidget, QGroupBox
)
from PySide6.QtCore import Qt, Signal

from ..core.safety import TASK_ALLOWLIST, is_admin


class SettingsView(QWidget):
    theme_changed = Signal(str)

    def __init__(self, config_path: str = "config/settings.json", parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.config_data = self._load_config()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        h1 = QLabel("Settings & Safety Configuration")
        h1.setStyleSheet("color: #f8fafc; font-size: 24px; font-weight: 700;")
        sub = QLabel("Operational policies, safety guardrails, execution timeouts, and audit parameters")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(h1)
        layout.addWidget(sub)

        # Safety & Security Guardrails Box
        sec_box = QGroupBox("Safety Guardrails & Elevation Policy")
        sec_box.setStyleSheet(self._group_box_style())
        sec_layout = QVBoxLayout(sec_box)

        admin_status = "Elevated (Administrator)" if is_admin() else "Standard User (Non-Elevated)"
        lbl_admin = QLabel(f"Current Session: {admin_status}")
        lbl_admin.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        sec_layout.addWidget(lbl_admin)

        self.chk_safety = QCheckBox("Enforce Strict Allowlist Execution (Recommended)")
        self.chk_safety.setChecked(self.config_data.get("safety_mode", True))
        self.chk_safety.setStyleSheet("color: #f1f5f9; font-size: 13px;")
        sec_layout.addWidget(self.chk_safety)

        self.chk_confirm = QCheckBox("Require Explicit Confirmation for Repair Actions (SFC/DISM)")
        self.chk_confirm.setChecked(self.config_data.get("require_confirmation_for_repairs", True))
        self.chk_confirm.setStyleSheet("color: #f1f5f9; font-size: 13px;")
        sec_layout.addWidget(self.chk_confirm)

        layout.addWidget(sec_box)

        # Timeouts Box
        time_box = QGroupBox("Subprocess Timeouts")
        time_box.setStyleSheet(self._group_box_style())
        time_layout = QHBoxLayout(time_box)

        lbl_t = QLabel("Standard Command Timeout (seconds):")
        lbl_t.setStyleSheet("color: #f1f5f9;")
        time_layout.addWidget(lbl_t)

        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(10, 1800)
        self.spin_timeout.setValue(self.config_data.get("default_timeout_seconds", 60))
        self.spin_timeout.setStyleSheet("""
            QSpinBox {
                background: #0f172a;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        time_layout.addWidget(self.spin_timeout)
        time_layout.addStretch()

        layout.addWidget(time_box)

        # Active Allowlist Box
        allow_box = QGroupBox("Registered Allowlisted Automation Tasks")
        allow_box.setStyleSheet(self._group_box_style())
        allow_layout = QVBoxLayout(allow_box)

        self.list_allow = QListWidget()
        self.list_allow.setStyleSheet("""
            QListWidget {
                background-color: #0d131f;
                border: 1px solid #1f2937;
                border-radius: 6px;
                color: #7dd3fc;
                font-family: Consolas, monospace;
                padding: 8px;
            }
        """)
        for task_id, meta in TASK_ALLOWLIST.items():
            req = " [ADMIN]" if meta["requires_admin"] else ""
            self.list_allow.addItem(f"{task_id:<26} -> {meta['name']}{req}")
        self.list_allow.setFixedHeight(160)
        allow_layout.addWidget(self.list_allow)

        layout.addWidget(allow_box)

        # Storage & Logs Box
        store_box = QGroupBox("Local Storage & Export Paths")
        store_box.setStyleSheet(self._group_box_style())
        store_layout = QVBoxLayout(store_box)

        db_path = os.path.abspath(self.config_data.get("database_path", "data/it_support.db"))
        lbl_db = QLabel(f"SQLite Database: {db_path}")
        lbl_db.setStyleSheet("color: #94a3b8; font-size: 12px;")
        store_layout.addWidget(lbl_db)

        log_path = os.path.abspath(self.config_data.get("log_file_path", "logs/it_support.log"))
        lbl_log = QLabel(f"Rolling Log File: {log_path}")
        lbl_log.setStyleSheet("color: #94a3b8; font-size: 12px;")
        store_layout.addWidget(lbl_log)

        layout.addWidget(store_box)

        # Save Button
        btn_save = QPushButton("Save Configuration Changes")
        btn_save.setStyleSheet("""
            QPushButton {
                background: #00d2ff;
                color: #090d16;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #38bdf8;
            }
        """)
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _group_box_style(self) -> str:
        return """
            QGroupBox {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 8px;
                margin-top: 14px;
                padding: 16px;
                font-weight: bold;
                color: #38bdf8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
            }
        """

    def _load_config(self) -> dict:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_settings(self):
        self.config_data["safety_mode"] = self.chk_safety.isChecked()
        self.config_data["require_confirmation_for_repairs"] = self.chk_confirm.isChecked()
        self.config_data["default_timeout_seconds"] = self.spin_timeout.value()

        os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2)
            QMessageBox.information(self, "Settings Saved", "Configuration updated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save settings: {str(e)}")

