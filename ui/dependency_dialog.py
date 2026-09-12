# -*- coding: utf-8 -*-
"""
DuckGIS - Dependency Installer Dialog
Provides a 1-click installer for DuckDB inside the QGIS Python environment.
"""

import sys
import subprocess
from typing import Optional

try:
    from PyQt5.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QTextEdit,
        QProgressBar,
        QMessageBox,
    )
    from PyQt5.QtCore import QThread, pyqtSignal, Qt
    from PyQt5.QtGui import QIcon
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


if QT_AVAILABLE:
    class PipInstallThread(QThread):
        """Worker thread to run pip install without freezing the UI."""
        log_signal = pyqtSignal(str)
        finished_signal = pyqtSignal(bool, str)

        def __init__(self, package_name="duckdb"):
            super().__init__()
            self.package_name = package_name

        def run(self):
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", self.package_name]
            self.log_signal.emit(f"Executing: {' '.join(cmd)}\n")
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )
                output_lines = []
                for line in process.stdout:
                    output_lines.append(line)
                    self.log_signal.emit(line.strip())

                process.wait()
                if process.returncode == 0:
                    self.finished_signal.emit(True, "Installation successful!")
                else:
                    self.finished_signal.emit(False, f"pip exited with code {process.returncode}")
            except Exception as ex:
                self.finished_signal.emit(False, str(ex))


    class DependencyDialog(QDialog):
        """Dialog prompting the user to install DuckDB if missing."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("DuckGIS — Setup Dependencies")
            self.setMinimumSize(500, 320)
            self._installer_thread: Optional[PipInstallThread] = None

            layout = QVBoxLayout(self)

            # Header
            self.lbl_header = QLabel("<h3>DuckDB Package Required</h3>")
            layout.addWidget(self.lbl_header)

            self.lbl_desc = QLabel(
                "DuckGIS requires the <b>duckdb</b> Python library to execute high-speed "
                "spatial queries.<br>Click <b>Install DuckDB Now</b> to automatically configure "
                "it for your QGIS Python environment."
            )
            self.lbl_desc.setWordWrap(True)
            layout.addWidget(self.lbl_desc)

            # Log / Output Box
            self.txt_log = QTextEdit()
            self.txt_log.setReadOnly(True)
            self.txt_log.setPlaceholderText("Installation logs will appear here...")
            layout.addWidget(self.txt_log)

            # Progress Bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setVisible(False)
            layout.addWidget(self.progress_bar)

            # Actions
            btn_layout = QHBoxLayout()
            self.btn_install = QPushButton("Install DuckDB Now")
            self.btn_install.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px 16px;")
            self.btn_install.clicked.connect(self.start_install)
            btn_layout.addWidget(self.btn_install)

            self.btn_close = QPushButton("Cancel")
            self.btn_close.clicked.connect(self.reject)
            btn_layout.addWidget(self.btn_close)

            layout.addLayout(btn_layout)

        def start_install(self):
            """Launches the pip installer in the background."""
            self.btn_install.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.txt_log.clear()

            self._installer_thread = PipInstallThread("duckdb")
            self._installer_thread.log_signal.connect(self._on_log)
            self._installer_thread.finished_signal.connect(self._on_finished)
            self._installer_thread.start()

        def _on_log(self, text: str):
            self.txt_log.append(text)

        def _on_finished(self, success: bool, message: str):
            self.progress_bar.setVisible(False)
            self.btn_install.setEnabled(True)
            if success:
                QMessageBox.information(
                    self,
                    "Installation Complete",
                    "DuckDB was successfully installed! You can now use DuckGIS."
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Installation Failed",
                    f"Failed to install DuckDB automatically:\n{message}\n\n"
                    "You can also run manually in your terminal:\n"
                    f"{sys.executable} -m pip install duckdb"
                )
else:
    class DependencyDialog:
        pass
