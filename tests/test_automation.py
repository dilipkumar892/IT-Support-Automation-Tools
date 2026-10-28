"""
Unit Tests for Automation Engine
"""

import time
import tempfile
import os
import pytest
from app.database.database import Database
from app.core.automation import AutomationTaskRunner, CancellationToken


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


def test_task_runner_registration(temp_db):
    runner = AutomationTaskRunner(temp_db)
    tasks = runner.get_registered_tasks()
    assert len(tasks) >= 20
    task_ids = [t["id"] for t in tasks]
    assert "collect_system_info" in task_ids
    assert "run_network_diagnostics" in task_ids
    assert "fix_print_spooler" in task_ids
    assert "generate_battery_report" in task_ids
    assert "audit_domain_and_identity" in task_ids
    assert "generate_ticket_snippet" in task_ids

    # Verify service_type assignment
    spool_task = next(t for t in tasks if t["id"] == "fix_print_spooler")
    assert spool_task["service_type"] == "UAC_REQUIRED"
    assert spool_task["requires_admin"] is True

    battery_task = next(t for t in tasks if t["id"] == "generate_battery_report")
    assert battery_task["service_type"] == "NORMAL"
    assert battery_task["requires_admin"] is False


def test_task_runner_disallow_arbitrary_task(temp_db):
    runner = AutomationTaskRunner(temp_db)
    completed_event = [False, False, ""]

    def on_complete(ok, data, msg):
        completed_event[0] = True
        completed_event[1] = ok
        completed_event[2] = msg

    runner.execute_task_async("malicious_unregistered_task", on_complete=on_complete)
    time.sleep(0.1)

    assert completed_event[0] is True
    assert completed_event[1] is False
    assert "Security rejection" in completed_event[2]


def test_task_runner_execution_and_progress(temp_db):
    runner = AutomationTaskRunner(temp_db)
    progress_recorded = []
    completed = [False, False]

    def on_progress(pct, msg):
        progress_recorded.append((pct, msg))

    def on_complete(ok, data, msg):
        completed[0] = True
        completed[1] = ok

    runner.execute_task_async("collect_system_info", on_progress=on_progress, on_complete=on_complete)

    # Wait for completion
    timeout = 10
    start = time.time()
    while not completed[0] and (time.time() - start) < timeout:
        time.sleep(0.2)

    assert completed[0] is True
    assert completed[1] is True
    assert len(progress_recorded) >= 2

    # Check database persistence
    history = temp_db.get_recent_automation_history(limit=5)
    assert len(history) >= 1
    assert history[0].task_id == "collect_system_info"
    assert history[0].status == "SUCCESS"


def test_cancellation_token():
    token = CancellationToken()
    assert token.is_cancelled() is False
    token.cancel()
    assert token.is_cancelled() is True

