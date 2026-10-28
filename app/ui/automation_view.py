"""
Automation Engine View
Presents allowlisted task catalog, real-time threaded execution, progress bars,
cancellation controls, execution log streams, and SQLite task history.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal, QObject

from ..core.automation import AutomationTaskRunner
from ..database.database import Database
from ..core.safety import is_admin, elevate_process


class AutomationBridge(QObject):
    progress_signal = Signal(int, str)
    complete_signal = Signal(bool, dict, str)


class AutomationView(QWidget):
    def __init__(self, db: Database, runner: AutomationTaskRunner, parent=None):
        super().__init__(parent)
        self.db = db
        self.runner = runner
        self.bridge = AutomationBridge()
        self.bridge.progress_signal.connect(self._on_progress)
        self.bridge.complete_signal.connect(self._on_complete)
        self.current_task_id: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        h1 = QLabel("Automation Engine & Workflow Orchestration")
        h1.setStyleSheet("color: #f8fafc; font-size: 24px; font-weight: 700;")
        sub = QLabel("Strictly allowlisted automation tasks with progress tracking, timeouts, and safety checks")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(h1)
        layout.addWidget(sub)

        # Task Selection & Controls Box
        ctrl_frame = QFrame()
        ctrl_frame.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        ctrl_layout = QVBoxLayout(ctrl_frame)
        ctrl_layout.setSpacing(12)

        row1 = QHBoxLayout()
        lbl_select = QLabel("Select Allowlisted Task:")
        lbl_select.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 13px;")
        row1.addWidget(lbl_select)

        self.combo_tasks = QComboBox()
        self.combo_tasks.setStyleSheet("""
            QComboBox {
                background: #0f172a;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 600;
                min-width: 320px;
            }
        """)
        row1.addWidget(self.combo_tasks)
        row1.addStretch()

        self.btn_run = QPushButton("Execute Task")
        self.btn_run.setStyleSheet("""
            QPushButton {
                background: #00d2ff;
                color: #090d16;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #38bdf8;
            }
            QPushButton:disabled {
                background: #334155;
                color: #64748b;
            }
        """)
        self.btn_run.clicked.connect(self.start_task)
        row1.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Cancel Execution")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: #ef4444;
                color: #ffffff;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #dc2626;
            }
            QPushButton:disabled {
                background: #334155;
                color: #64748b;
            }
        """)
        self.btn_cancel.clicked.connect(self.cancel_task)
        row1.addWidget(self.btn_cancel)

        ctrl_layout.addLayout(row1)

        # Task metadata explanation
        self.lbl_task_desc = QLabel("")
        self.lbl_task_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.combo_tasks.currentIndexChanged.connect(self._on_task_selected)
        ctrl_layout.addWidget(self.lbl_task_desc)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #1e293b; border-radius: 4px; }
            QProgressBar::chunk { background: #38bdf8; border-radius: 4px; }
        """)
        ctrl_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Engine Ready.")
        self.lbl_status.setStyleSheet("color: #38bdf8; font-size: 12px; font-weight: 600;")
        ctrl_layout.addWidget(self.lbl_status)

        layout.addWidget(ctrl_frame)

        # Splitter: Task Live Output vs Automation History
        splitter = QSplitter(Qt.Vertical)

        # Console Output Box
        box_console = QWidget()
        l_console = QVBoxLayout(box_console)
        l_console.setContentsMargins(0, 0, 0, 0)
        lbl_c = QLabel("Task Output & Real-Time Telemetry:")
        lbl_c.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        l_console.addWidget(lbl_c)

        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setStyleSheet("""
            QTextEdit {
                background-color: #060911;
                border: 1px solid #1f2937;
                border-radius: 6px;
                color: #7dd3fc;
                font-family: "Cascadia Code", Consolas, Monaco, monospace;
                font-size: 12px;
                padding: 10px;
            }
        """)
        l_console.addWidget(self.txt_output)
        splitter.addWidget(box_console)

        # History Table Box
        box_hist = QWidget()
        l_hist = QVBoxLayout(box_hist)
        l_hist.setContentsMargins(0, 0, 0, 0)
        lbl_h = QLabel("Automation Execution History:")
        lbl_h.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        l_hist.addWidget(lbl_h)

        self.table_history = QTableWidget(0, 5)
        self.table_history.setHorizontalHeaderLabels(["Start Time", "Task Name", "Status", "Duration", "Summary"])
        self.table_history.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table_history.setStyleSheet("""
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
        """)
        l_hist.addWidget(self.table_history)
        splitter.addWidget(box_hist)

        layout.addWidget(splitter)

        # Populate tasks and history
        self._populate_task_list()
        self.refresh_history()

    def _populate_task_list(self):
        tasks = self.runner.get_registered_tasks()
        self.task_meta_cache = {t["id"]: t for t in tasks}
        self.combo_tasks.clear()
        for t in tasks:
            service_badge = "🛡️ UAC" if t.get("requires_admin") else "👤 Normal"
            self.combo_tasks.addItem(f"{t['name']}  [{service_badge}]", t["id"])
        self._on_task_selected()

    def _on_task_selected(self):
        task_id = self.combo_tasks.currentData()
        meta = self.task_meta_cache.get(task_id, {})
        req_admin = meta.get("requires_admin", False)
        desc = meta.get("description", "")
        admin_warning = " ⚠️ Requires Administrator Privileges." if req_admin else ""
        self.lbl_task_desc.setText(f"{desc}{admin_warning}")

    def trigger_task_by_id(self, task_id: str):
        """Allows dashboard quick actions to trigger a task."""
        index = self.combo_tasks.findData(task_id)
        if index >= 0:
            self.combo_tasks.setCurrentIndex(index)
            self.start_task()

    def start_task(self):
        task_id = self.combo_tasks.currentData()
        if not task_id:
            return

        meta = self.task_meta_cache.get(task_id, {})
        if meta.get("requires_admin") and not is_admin():
            reply = QMessageBox.question(
                self,
                "Administrator Elevation Required",
                f"The task '{meta.get('name')}' requires Administrator privileges to run safely.\n\n"
                "Would you like to relaunch the application with Administrator privileges now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                elevate_process(exit_current=True)
            return

        self.current_task_id = task_id
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(5)
        self.lbl_status.setText(f"Running: {meta.get('name')}...")
        self.txt_output.clear()
        self.txt_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Initializing task '{task_id}'...")

        self.runner.execute_task_async(
            task_id,
            on_progress=lambda pct, msg: self.bridge.progress_signal.emit(pct, msg),
            on_complete=lambda ok, data, msg: self.bridge.complete_signal.emit(ok, data, msg)
        )

    def cancel_task(self):
        if self.current_task_id:
            self.runner.cancel_task(self.current_task_id)
            self.lbl_status.setText("Cancellation requested...")
            self.btn_cancel.setEnabled(False)

    def _on_progress(self, percent: int, message: str):
        self.progress_bar.setValue(percent)
        self.lbl_status.setText(message)
        self.txt_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def _on_complete(self, success: bool, data: dict, message: str):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(100 if success else 0)
        self.lbl_status.setText(message)
        self.txt_output.append(f"\n--- Final Execution Result ---\nStatus: {'SUCCESS' if success else 'FAILED'}\n{message}\n")
        self.refresh_history()

    def refresh_history(self):
        entries = self.db.get_recent_automation_history(limit=25)
        self.table_history.setRowCount(len(entries))
        for row, item in enumerate(entries):
            self.table_history.setItem(row, 0, QTableWidgetItem(item.started_at[:19].replace("T", " ")))
            self.table_history.setItem(row, 1, QTableWidgetItem(item.task_name))

            st = QTableWidgetItem(item.status)
            if item.status == "SUCCESS":
                st.setForeground(Qt.green)
            elif item.status == "CANCELLED":
                st.setForeground(Qt.yellow)
            else:
                st.setForeground(Qt.red)
            self.table_history.setItem(row, 2, st)

            duration = "Running"
            if item.completed_at:
                try:
                    t1 = datetime.fromisoformat(item.started_at)
                    t2 = datetime.fromisoformat(item.completed_at)
                    secs = (t2 - t1).total_seconds()
                    duration = f"{secs:.1f}s"
                except Exception:
                    duration = "Done"
            self.table_history.setItem(row, 3, QTableWidgetItem(duration))
            self.table_history.setItem(row, 4, QTableWidgetItem(item.output_text or item.error_text))

