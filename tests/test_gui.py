"""
Unit Tests for Desktop GUI Components
"""

import sys
import tempfile
import os
import pytest
from PySide6.QtWidgets import QApplication
from app.database.database import Database
from app.core.automation import AutomationTaskRunner
from app.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        # Offscreen platform flag for clean headless testing
        app = QApplication(["app", "-platform", "offscreen"])
    return app


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(db_path=path)
    yield db
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def test_main_window_startup(qapp, temp_db):
    runner = AutomationTaskRunner(temp_db)
    window = MainWindow(temp_db, runner)
    assert window is not None
    assert window.windowTitle() == "IT Support Automation Suite - Enterprise Edition"
    assert window.stack.count() == 5  # 5 main views

    # Test navigating through pages
    for i in range(5):
        window._select_nav(i)
        assert window.stack.currentIndex() == i

    # Test triggering a dashboard quick action
    window._handle_quick_action("collect_system_info")
    assert window.stack.currentIndex() == 3  # Automation tab

    window.close()

