"""
IT Asset Inventory View
Displays detailed hardware specifications, network interfaces, and installed software.
Supports dynamic filtering and exports to CSV, JSON, and HTML.
"""

import os
from typing import Optional, List
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QFrame, QSplitter
)
from PySide6.QtCore import Qt

from ..database.database import Database
from ..database.models import SystemInventorySnapshot
from ..core.inventory import (
    capture_and_store_inventory,
    filter_applications,
    export_inventory_csv,
    export_inventory_json,
    export_inventory_html
)


class InventoryView(QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_snapshot: Optional[SystemInventorySnapshot] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title and Action Bar
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        h1 = QLabel("IT Asset & Software Inventory")
        h1.setStyleSheet("color: #f8fafc; font-size: 24px; font-weight: 700;")
        sub = QLabel("Comprehensive hardware auditing and software license inventory")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(h1)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch()

        self.btn_scan = QPushButton("Capture New Inventory Snapshot")
        self.btn_scan.setStyleSheet("""
            QPushButton {
                background: #00d2ff;
                color: #090d16;
                border-radius: 6px;
                padding: 9px 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #38bdf8;
            }
        """)
        self.btn_scan.clicked.connect(self.scan_inventory)
        header.addWidget(self.btn_scan)

        layout.addLayout(header)

        # Hardware Specs Summary Card
        self.specs_card = QFrame()
        self.specs_card.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        specs_layout = QHBoxLayout(self.specs_card)
        specs_layout.setContentsMargins(14, 10, 14, 10)

        self.lbl_spec_host = QLabel("Device: Loading...")
        self.lbl_spec_host.setStyleSheet("color: #38bdf8; font-weight: 600;")
        self.lbl_spec_os = QLabel("OS: Loading...")
        self.lbl_spec_os.setStyleSheet("color: #e2e8f0;")
        self.lbl_spec_cpu = QLabel("CPU: Loading...")
        self.lbl_spec_cpu.setStyleSheet("color: #e2e8f0;")
        self.lbl_spec_ram = QLabel("RAM: Loading...")
        self.lbl_spec_ram.setStyleSheet("color: #a855f7; font-weight: 600;")

        specs_layout.addWidget(self.lbl_spec_host)
        specs_layout.addWidget(self.lbl_spec_os)
        specs_layout.addWidget(self.lbl_spec_cpu)
        specs_layout.addWidget(self.lbl_spec_ram)
        specs_layout.addStretch()

        layout.addWidget(self.specs_card)

        # Filter & Export Toolbar
        tools_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search installed applications by name or publisher...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                color: #f8fafc;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        self.txt_search.textChanged.connect(self.apply_filter)
        tools_layout.addWidget(self.txt_search, stretch=3)

        btn_csv = QPushButton("Export CSV")
        btn_csv.setStyleSheet(self._export_btn_style())
        btn_csv.clicked.connect(self.export_csv)
        tools_layout.addWidget(btn_csv)

        btn_json = QPushButton("Export JSON")
        btn_json.setStyleSheet(self._export_btn_style())
        btn_json.clicked.connect(self.export_json)
        tools_layout.addWidget(btn_json)

        btn_html = QPushButton("Export HTML")
        btn_html.setStyleSheet(self._export_btn_style())
        btn_html.clicked.connect(self.export_html)
        tools_layout.addWidget(btn_html)

        layout.addLayout(tools_layout)

        # Applications Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Application Name", "Version", "Publisher", "Install Date"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0d131f;
                border: 1px solid #1f2937;
                border-radius: 8px;
                color: #f8fafc;
                gridline-color: #1e293b;
            }
            QHeaderView::section {
                background-color: #162032;
                color: #38bdf8;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item:hover {
                background-color: #1e293b;
            }
        """)
        layout.addWidget(self.table)

        # Load existing inventory from database or prompt initial scan
        self.load_latest()

    def _export_btn_style(self) -> str:
        return """
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #38bdf8;
                border: 1px solid #38bdf8;
            }
        """

    def load_latest(self):
        snap = self.db.get_latest_inventory_snapshot()
        if snap:
            self.current_snapshot = snap
            self.update_display(snap)
        else:
            # Trigger quick initial capture
            self.scan_inventory()

    def scan_inventory(self):
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Scanning Registry...")
        try:
            self.current_snapshot = capture_and_store_inventory(self.db)
            self.update_display(self.current_snapshot)
        finally:
            self.btn_scan.setEnabled(True)
            self.btn_scan.setText("Capture New Inventory Snapshot")

    def update_display(self, snap: SystemInventorySnapshot):
        self.lbl_spec_host.setText(f"Device: {snap.hostname}")
        self.lbl_spec_os.setText(f"OS: {snap.os_name} ({snap.os_build})")
        self.lbl_spec_cpu.setText(f"CPU: {snap.cpu_model[:30]}")
        self.lbl_spec_ram.setText(f"RAM: {snap.ram_total_gb} GB")
        self.populate_table(snap.installed_apps)

    def populate_table(self, apps):
        self.table.setRowCount(len(apps))
        for row, app in enumerate(apps):
            self.table.setItem(row, 0, QTableWidgetItem(app.name))
            self.table.setItem(row, 1, QTableWidgetItem(app.version))
            self.table.setItem(row, 2, QTableWidgetItem(app.publisher))
            self.table.setItem(row, 3, QTableWidgetItem(app.install_date))

    def apply_filter(self):
        if not self.current_snapshot:
            return
        query = self.txt_search.text().strip()
        filtered = filter_applications(self.current_snapshot.installed_apps, query)
        self.populate_table(filtered)

    def export_csv(self):
        if not self.current_snapshot:
            QMessageBox.warning(self, "No Data", "No inventory data available to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Inventory to CSV", f"inventory_{self.current_snapshot.hostname}.csv", "CSV Files (*.csv)")
        if path:
            export_inventory_csv(self.current_snapshot, path)
            QMessageBox.information(self, "Export Successful", f"Inventory exported successfully to:\n{path}")

    def export_json(self):
        if not self.current_snapshot:
            QMessageBox.warning(self, "No Data", "No inventory data available to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Inventory to JSON", f"inventory_{self.current_snapshot.hostname}.json", "JSON Files (*.json)")
        if path:
            export_inventory_json(self.current_snapshot, path)
            QMessageBox.information(self, "Export Successful", f"Inventory exported successfully to:\n{path}")

    def export_html(self):
        if not self.current_snapshot:
            QMessageBox.warning(self, "No Data", "No inventory data available to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Inventory to HTML", f"inventory_{self.current_snapshot.hostname}.html", "HTML Files (*.html)")
        if path:
            export_inventory_html(self.current_snapshot, path)
            QMessageBox.information(self, "Export Successful", f"Inventory report exported successfully to:\n{path}")

