"""
IT Support Automation Suite - Enterprise Edition
Main Application Entry Point
Supports both interactive modern GUI and headless CLI execution.
"""

import sys
import os
import argparse
from typing import Optional

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.logging import setup_logging
from app.database.database import Database
from app.core.automation import AutomationTaskRunner
from app.core.safety import is_admin, elevate_process


def run_cli_task(task_id: str, db: Database, runner: AutomationTaskRunner):
    """Executes an allowlisted task in headless/CLI mode."""
    import time

    def on_progress(pct: int, msg: str):
        print(f"[{pct}%] {msg}")

    finished = [False]

    def on_complete(ok: bool, data: dict, msg: str):
        print(f"\nTask Completed: {'SUCCESS' if ok else 'FAILED'}")
        print(f"Output: {msg}")
        finished[0] = True

    runner.execute_task_async(task_id, on_progress=on_progress, on_complete=on_complete)

    while not finished[0]:
        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="Professional IT Support Automation Suite")
    parser.add_argument("--task", type=str, help="Run a specific allowlisted automation task headlessly in CLI mode.")
    parser.add_argument("--list-tasks", action="store_true", help="List all allowlisted automation tasks.")
    parser.add_argument("--headless", action="store_true", help="Run without launching GUI.")
    parser.add_argument("--elevate", action="store_true", help="Request Windows Administrator elevation (UAC prompt) before executing.")
    args = parser.parse_args()

    # Handle explicit elevation request
    if args.elevate and not is_admin():
        remaining_args = [a for a in sys.argv[1:] if a != "--elevate"]
        print("Requesting Windows Administrator elevation (UAC prompt)...")
        elevated = elevate_process(args=remaining_args, exit_current=True)
        if not elevated:
            print("Administrator elevation was not granted or cancelled by user.")
            sys.exit(1)

    # Initialize subsystems
    logger = setup_logging()
    logger.info("Initializing IT Support Automation Suite...")

    db = Database(db_path=os.path.join(BASE_DIR, "data", "it_support.db"))
    runner = AutomationTaskRunner(db)

    # CLI tasks listing
    if args.list_tasks:
        print("\n=== Registered Allowlisted Tasks ===")
        for t in runner.get_registered_tasks():
            admin_flag = " [Requires Admin]" if t["requires_admin"] else ""
            print(f"- {t['id']:<26}: {t['name']} ({t['risk']}){admin_flag}")
            print(f"  {t['description']}")
        return

    # Headless task execution
    if args.task:
        print(f"Running headless automation task: {args.task}")
        run_cli_task(args.task, db, runner)
        return

    if args.headless:
        print("Suite initialized in headless mode. Run with --list-tasks or --task <id>.")
        return

    # Launch Desktop GUI via PySide6
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from app.ui.main_window import MainWindow

        # High DPI scaling attributes if available
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = QApplication(sys.argv)
        app.setApplicationName("IT Support Automation Suite")
        app.setOrganizationName("IT Operations")

        window = MainWindow(db, runner)
        window.show()

        logger.info("GUI successfully initialized and presented.")
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Failed to start GUI application: {str(e)}", exc_info=True)
        print(f"Error launching GUI: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

