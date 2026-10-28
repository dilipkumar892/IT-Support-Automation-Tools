"""
Automation Engine
Provides threaded, cancellable task orchestration with progress signals,
timeout management, error recovery, and execution history persistence.
Strictly disallows arbitrary unattended execution: all tasks must be registered in the allowlist.
"""

import threading
import time
from datetime import datetime
from typing import Dict, Any, Callable, Optional, List

from .safety import is_task_allowed, get_task_metadata, RiskLevel
from .system_info import collect_full_system_snapshot
from .network import run_comprehensive_network_diagnostics, flush_dns
from .inventory import capture_and_store_inventory
from .diagnostics import (
    run_sfc_scan,
    run_dism_health,
    analyze_disk_cleanup_targets,
    inspect_windows_services,
    inspect_startup_programs,
    collect_recent_event_log_errors,
    clean_junk_files,
    fix_print_spooler_service,
    reset_network_adapter_and_stack,
    reset_windows_update_agent,
    generate_battery_report,
    audit_domain_and_identity,
    audit_bitlocker_status,
    generate_itsm_ticket_payload
)
from ..database.database import Database
from ..database.models import DiagnosticReport


class CancellationToken:
    def __init__(self):
        self._is_cancelled = False
        self._lock = threading.Lock()

    def cancel(self):
        with self._lock:
            self._is_cancelled = True

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._is_cancelled


class AutomationTaskRunner:
    def __init__(self, db: Database):
        self.db = db
        self.active_threads: Dict[str, threading.Thread] = {}
        self.tokens: Dict[str, CancellationToken] = {}

    def get_registered_tasks(self) -> List[Dict[str, Any]]:
        """Returns metadata for all supported automation tasks."""
        tasks = []
        from .safety import TASK_ALLOWLIST
        for task_id, meta in TASK_ALLOWLIST.items():
            tasks.append({
                "id": task_id,
                "name": meta["name"],
                "risk": meta["risk"].value,
                "requires_admin": meta["requires_admin"],
                "service_type": meta.get("service_type", "NORMAL"),
                "description": meta["description"]
            })
        return tasks

    def cancel_task(self, task_id: str) -> bool:
        """Requests cancellation for an active task."""
        token = self.tokens.get(task_id)
        if token:
            token.cancel()
            return True
        return False

    def is_running(self, task_id: str) -> bool:
        thread = self.active_threads.get(task_id)
        return thread is not None and thread.is_alive()

    def execute_task_async(
        self,
        task_id: str,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_complete: Optional[Callable[[bool, Dict[str, Any], str], None]] = None,
        timeout_sec: int = 120
    ):
        """Dispatches an allowlisted task in a worker thread."""
        if not is_task_allowed(task_id):
            if on_complete:
                on_complete(False, {}, f"Security rejection: Task '{task_id}' is not in the allowlist.")
            return

        if self.is_running(task_id):
            if on_complete:
                on_complete(False, {}, f"Task '{task_id}' is already executing.")
            return

        token = CancellationToken()
        self.tokens[task_id] = token

        thread = threading.Thread(
            target=self._worker,
            args=(task_id, token, on_progress, on_complete, timeout_sec),
            daemon=True
        )
        self.active_threads[task_id] = thread
        thread.start()

    def _worker(
        self,
        task_id: str,
        token: CancellationToken,
        on_progress: Optional[Callable[[int, str], None]],
        on_complete: Optional[Callable[[bool, Dict[str, Any], str], None]],
        timeout_sec: int
    ):
        meta = get_task_metadata(task_id) or {"name": task_id}
        task_name = meta.get("name", task_id)
        history_id = self.db.log_automation_start(task_id, task_name)

        def progress(percent: int, message: str):
            if on_progress:
                try:
                    on_progress(percent, message)
                except Exception:
                    pass

        progress(5, f"Starting task: {task_name}...")

        success = False
        result_data: Dict[str, Any] = {}
        error_msg = ""
        output_summary = ""

        try:
            if token.is_cancelled():
                raise InterruptedError("Task was cancelled prior to initialization.")

            # Route allowlisted tasks to appropriate handlers
            if task_id == "collect_system_info":
                progress(20, "Inspecting OS and hardware parameters...")
                snap = collect_full_system_snapshot()
                progress(80, "Storing snapshot in database...")
                self.db.save_inventory_snapshot(snap)
                result_data = snap.to_dict()
                success = True
                output_summary = f"System info collected: {snap.hostname} - {snap.cpu_model} ({snap.ram_total_gb} GB RAM)"

            elif task_id == "run_network_diagnostics":
                progress(20, "Probing gateway and internet targets...")
                if token.is_cancelled():
                    raise InterruptedError("Cancelled")
                diag = run_comprehensive_network_diagnostics()
                progress(80, "Analyzing network reachability...")
                result_data = diag
                success = (diag["status"] != "CRITICAL")
                output_summary = f"Network status: {diag['status']}. Gateway: {diag.get('gateway')}"

                # Persist as diagnostic report
                self.db.save_diagnostic_report(DiagnosticReport(
                    report_type="network",
                    title="Network Diagnostics Assessment",
                    status=diag["status"],
                    summary=output_summary,
                    findings=[{"item": f} for f in diag["findings"]],
                    recommendations=diag["recommendations"],
                    logs=str(diag.get("internet_ping", {}).get("raw_output", ""))
                ))

            elif task_id == "scan_installed_software":
                progress(30, "Scanning 64-bit and 32-bit registry uninstall keys...")
                if token.is_cancelled():
                    raise InterruptedError("Cancelled")
                snap = capture_and_store_inventory(self.db)
                result_data = {"count": len(snap.installed_apps), "hostname": snap.hostname}
                success = True
                output_summary = f"Cataloged {len(snap.installed_apps)} installed applications."

            elif task_id == "analyze_disk_space":
                progress(30, "Scanning temporary folders and disk usage...")
                if token.is_cancelled():
                    raise InterruptedError("Cancelled")
                disk_analysis = analyze_disk_cleanup_targets()
                result_data = disk_analysis
                success = True
                output_summary = f"Analyzed disk space. Found {disk_analysis['total_reclaimable_mb']} MB in temporary caches."

            elif task_id == "sfc_verify_only":
                progress(20, "Initiating System File Checker (/verifyonly)...")
                sfc_res = run_sfc_scan(repair_mode=False)
                result_data = sfc_res
                success = sfc_res["success"]
                output_summary = sfc_res["summary"]

            elif task_id == "sfc_repair":
                progress(20, "Executing System File Checker repair (/scannow)...")
                sfc_res = run_sfc_scan(repair_mode=True)
                result_data = sfc_res
                success = sfc_res["success"]
                output_summary = sfc_res["summary"]

            elif task_id.startswith("dism_"):
                op = task_id.replace("dism_", "").replace("_health", "")
                progress(20, f"Executing DISM cleanup image /{op}...")
                dism_res = run_dism_health(operation=op)
                result_data = dism_res
                success = dism_res["success"]
                output_summary = f"DISM {op} completed. Corrupt detected: {dism_res.get('corrupt_detected')}"

            elif task_id == "check_windows_updates":
                progress(30, "Checking Windows Update services...")
                svc_res = inspect_windows_services()
                result_data = svc_res
                wu_svc = svc_res["services"].get("wuauserv", {})
                success = True
                output_summary = f"Windows Update Service status: {wu_svc.get('status', 'Unknown')}"

            elif task_id == "audit_event_logs":
                progress(30, "Querying System event log for errors and critical events...")
                logs = collect_recent_event_log_errors(max_events=20)
                result_data = {"events": logs, "count": len(logs)}
                success = True
                output_summary = f"Retrieved {len(logs)} recent system error/critical events."

            elif task_id == "audit_startup_programs":
                progress(40, "Auditing startup registry keys...")
                startups = inspect_startup_programs()
                result_data = {"startups": startups, "count": len(startups)}
                success = True
                output_summary = f"Found {len(startups)} startup applications."

            elif task_id == "flush_dns_cache":
                progress(50, "Flushing DNS client resolver cache...")
                flushed, msg = flush_dns()
                success = flushed
                output_summary = msg
                result_data = {"message": msg}

            elif task_id == "prepare_support_bundle":
                progress(10, "Gathering system info...")
                sys_snap = collect_full_system_snapshot()
                progress(40, "Running network checks...")
                net_diag = run_comprehensive_network_diagnostics()
                progress(70, "Scanning disk usage...")
                disk_diag = analyze_disk_cleanup_targets()
                progress(90, "Creating support report...")

                rep = DiagnosticReport(
                    report_type="support_bundle",
                    title="Comprehensive IT Support Diagnostic Bundle",
                    status="PASS" if net_diag["status"] == "PASS" else "WARNING",
                    summary=f"Automated diagnostics on {sys_snap.hostname}. Network: {net_diag['status']}. Reclaimable disk: {disk_diag['total_reclaimable_mb']} MB.",
                    findings=[{"category": "Network", "detail": f} for f in net_diag["findings"]],
                    recommendations=net_diag["recommendations"] + ["Run regular disk cleanup and keep Windows updated."],
                    logs=f"Uptime: {sys_snap.uptime_hours}h | Memory: {sys_snap.ram_available_gb}GB free of {sys_snap.ram_total_gb}GB."
                )
                self.db.save_diagnostic_report(rep)
                result_data = rep.to_dict()
                success = True
                output_summary = "IT Support Bundle prepared and saved to database."

            elif task_id == "clean_disk_junk":
                progress(30, "Cleaning user temporary cache and logs...")
                clean_res = clean_junk_files(system_level=False)
                result_data = clean_res
                success = clean_res["success"]
                output_summary = clean_res["message"]

            elif task_id == "clean_system_junk":
                progress(30, "Cleaning Windows system temp and WER queues (UAC)...")
                clean_res = clean_junk_files(system_level=True)
                result_data = clean_res
                success = clean_res["success"]
                output_summary = clean_res["message"]

            elif task_id == "reset_windows_update_components":
                progress(20, "Stopping update services and purging download cache...")
                wu_res = reset_windows_update_agent()
                result_data = wu_res
                success = wu_res["success"]
                output_summary = wu_res["message"]

            elif task_id == "reset_network_stack":
                progress(20, "Executing Winsock catalog and TCP/IP stack reset...")
                net_res = reset_network_adapter_and_stack()
                result_data = net_res
                success = net_res["success"]
                output_summary = net_res["message"]

            elif task_id == "fix_print_spooler":
                progress(20, "Stopping spooler, clearing PRINTERS queue, and restarting...")
                spool_res = fix_print_spooler_service()
                result_data = spool_res
                success = spool_res["success"]
                output_summary = f"Spooler service {spool_res.get('service_status')}. Purged {spool_res.get('deleted_spool_jobs', 0)} stuck jobs."

            elif task_id == "generate_battery_report":
                progress(30, "Analyzing laptop battery health and charge wear...")
                bat_res = generate_battery_report()
                result_data = bat_res
                success = True
                if bat_res.get("has_battery"):
                    output_summary = f"Battery Wear: {bat_res['battery_wear_percent']}%. Health: {bat_res['health_assessment']}"
                else:
                    output_summary = bat_res["health_assessment"]

            elif task_id == "audit_domain_and_identity":
                progress(30, "Auditing Active Directory & Microsoft Entra ID status...")
                id_res = audit_domain_and_identity()
                result_data = id_res
                success = True
                joined = "Domain Joined" if id_res.get("domain_joined") else "Workgroup"
                entra = "Entra ID Registered" if id_res.get("azure_ad_joined") else "Not Entra Joined"
                output_summary = f"Identity: {id_res.get('domain_name')} ({joined}) | {entra}"

            elif task_id == "audit_bitlocker":
                progress(30, "Querying BitLocker protection and encryption status...")
                bit_res = audit_bitlocker_status()
                result_data = bit_res
                success = bit_res["success"]
                output_summary = bit_res.get("summary", bit_res.get("message", "BitLocker audit finished."))

            elif task_id == "generate_ticket_snippet":
                progress(30, "Compiling system specs and findings into ITSM ticket template...")
                ticket_res = generate_itsm_ticket_payload()
                result_data = ticket_res
                success = True
                output_summary = "ITSM Ticket Snippet prepared successfully."

            else:
                raise ValueError(f"Task {task_id} handler not implemented.")

            if token.is_cancelled():
                raise InterruptedError("Task was cancelled during execution.")

            progress(100, f"Completed: {task_name}")

        except InterruptedError:
            success = False
            output_summary = "Task was cancelled by user."
            error_msg = "Task cancelled."
        except Exception as e:
            success = False
            error_msg = str(e)
            output_summary = f"Task encountered an error: {str(e)}"

        # Finalize database entry
        status_label = "CANCELLED" if token.is_cancelled() else ("SUCCESS" if success else "FAILED")
        self.db.update_automation_entry(
            entry_id=history_id,
            status=status_label,
            completed_at=datetime.now().isoformat(),
            exit_code=0 if success else 1,
            output_text=output_summary,
            error_text=error_msg
        )

        if on_complete:
            try:
                on_complete(success, result_data, output_summary)
            except Exception:
                pass

