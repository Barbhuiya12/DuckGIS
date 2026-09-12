# -*- coding: utf-8 -*-
"""
DuckGIS - Dependency Guidance Dialog
Provides clear instructions and 1-click clipboard command to install DuckDB.
Complies with QGIS security guidelines (no subprocess / privilege escalation).
"""

import sys

try:
    from qgis.PyQt.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QLineEdit,
        QApplication,
        QMessageBox,
    )
    from qgis.PyQt.QtCore import Qt
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


if QT_AVAILABLE:
    class DependencyDialog(QDialog):
        """Dialog guiding the user to install DuckDB safely without subprocess."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("DuckGIS — Setup DuckDB Dependency")
            self.setMinimumSize(480, 260)

            layout = QVBoxLayout(self)
            layout.setSpacing(12)

            # Header
            self.lbl_header = QLabel("<h3>DuckDB Python Package Required</h3>")
            layout.addWidget(self.lbl_header)

            self.lbl_desc = QLabel(
                "DuckGIS requires the <b>duckdb</b> Python library to execute ultra-fast spatial queries.<br>"
                "Please run the following command in your terminal or QGIS Python Console:"
            )
            self.lbl_desc.setWordWrap(True)
            layout.addWidget(self.lbl_desc)

            # Command text box
            self.txt_cmd = QLineEdit()
            self.txt_cmd.setReadOnly(True)
            install_cmd = f"{sys.executable} -m pip install --upgrade duckdb"
            self.txt_cmd.setText(install_cmd)
            self.txt_cmd.setStyleSheet("font-family: monospace; font-size: 11px; padding: 6px; background-color: #f5f5f5;")
            layout.addWidget(self.txt_cmd)

            # Instructions
            self.lbl_note = QLabel(
                "<small style='color: #666;'>"
                "<b>On Windows:</b> Run via OSGeo4W Shell.<br>"
                "<b>On macOS / Linux:</b> Run in your terminal or execute in QGIS Python Console (Ctrl+Alt+P)."
                "</small>"
            )
            self.lbl_note.setWordWrap(True)
            layout.addWidget(self.lbl_note)

            # Buttons
            btn_layout = QHBoxLayout()
            self.btn_copy = QPushButton("📋 Copy Command")
            self.btn_copy.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px 14px;")
            self.btn_copy.clicked.connect(self._copy_command)
            btn_layout.addWidget(self.btn_copy)

            self.btn_check = QPushButton("🔄 Check Again")
            self.btn_check.clicked.connect(self._check_installed)
            btn_layout.addWidget(self.btn_check)

            self.btn_close = QPushButton("Close")
            self.btn_close.clicked.connect(self.reject)
            btn_layout.addWidget(self.btn_close)

            layout.addLayout(btn_layout)

        def _copy_command(self):
            """Copies the pip command to clipboard."""
            clipboard = QApplication.clipboard()
            clipboard.setText(self.txt_cmd.text())
            QMessageBox.information(
                self,
                "Copied",
                "Command copied to clipboard!\nRun it in your terminal, then click 'Check Again'."
            )

        def _check_installed(self):
            """Checks if duckdb is now importable."""
            try:
                import duckdb  # noqa: F401
                QMessageBox.information(
                    self,
                    "DuckDB Detected",
                    "DuckDB was detected successfully! You can now use DuckGIS."
                )
                self.accept()
            except ImportError:
                QMessageBox.warning(
                    self,
                    "Not Detected Yet",
                    "DuckDB could not be found yet.\nPlease ensure the command finished installing, then try again."
                )
else:
    class DependencyDialog:
        pass
