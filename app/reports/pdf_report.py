"""
PDF Diagnostic Report Generator
Renders executive-grade PDF reports directly via PySide6 native PDF printing engine.
"""

import os
from datetime import datetime
from typing import Optional

from ..database.models import DiagnosticReport, SystemInventorySnapshot
from .html_report import generate_html_report


def generate_pdf_report(
    report: DiagnosticReport,
    system_snapshot: Optional[SystemInventorySnapshot] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Renders diagnostic report into a professional PDF using PySide6's QTextDocument/QPdfWriter.
    """
    if not output_path:
        timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"reports_export/DiagnosticReport_{timestamp_slug}.pdf"

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # First generate print-optimized HTML
    temp_html = output_path.replace(".pdf", "_temp.html")
    generate_html_report(report, system_snapshot, temp_html)

    with open(temp_html, "r", encoding="utf-8") as f:
        html_content = f.read()

    try:
        import sys
        from PySide6.QtCore import QCoreApplication, QMarginsF
        from PySide6.QtGui import QGuiApplication, QTextDocument, QPdfWriter, QPageLayout, QPageSize

        # Ensure a QGuiApplication instance exists for font and document rendering
        app = QCoreApplication.instance()
        created_temp_app = False
        if app is None:
            app = QGuiApplication(sys.argv if sys.argv else ["app", "-platform", "offscreen"])
            created_temp_app = True

        writer = QPdfWriter(output_path)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageOrientation(QPageLayout.Orientation.Portrait)
        writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)

        doc = QTextDocument()
        doc.setHtml(html_content)
        doc.print_(writer)

    except Exception as e:
        # Fallback if GUI engine isn't initialized or in headless mode:
        # Save HTML alongside and notify
        with open(output_path + ".html", "w", encoding="utf-8") as fallback:
            fallback.write(html_content)
        raise RuntimeError(f"PDF generation error: {str(e)}")
    finally:
        if os.path.exists(temp_html):
            try:
                os.remove(temp_html)
            except OSError:
                pass

    return output_path
