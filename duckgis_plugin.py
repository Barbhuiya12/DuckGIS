# -*- coding: utf-8 -*-
"""
DuckGIS - Plugin Main Lifecycle Controller
Manages QGIS GUI integration, menus, toolbar actions, and dock widget registration.
"""

import os
from typing import Optional

try:
    from PyQt5.QtWidgets import QAction
    from PyQt5.QtGui import QIcon
    from PyQt5.QtCore import Qt
    from qgis.gui import QgisInterface
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

from ui.dock_widget import DuckGISDockWidget


class DuckGISPlugin:
    """Main QGIS Plugin class for DuckGIS."""

    def __init__(self, iface: "QgisInterface"):
        self.iface = iface
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.dock_widget: Optional[DuckGISDockWidget] = None
        self.action: Optional[QAction] = None
        self.toolbar = None

    def initGui(self):
        """Initializes the plugin GUI components into QGIS."""
        if not QT_AVAILABLE:
            return

        icon_path = os.path.join(self.plugin_dir, "resources", "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        # Create action
        self.action = QAction(icon, "DuckGIS Studio", self.iface.mainWindow())
        self.action.setToolTip("Open DuckGIS Spatial Studio (DuckDB SQL Engine)")
        self.action.triggered.connect(self.toggle_dock_widget)

        # Add to Database Menu & Toolbar
        self.iface.addPluginToDatabaseMenu("&DuckGIS", self.action)
        self.iface.addDatabaseToolBarIcon(self.action)

        # Initialize dock widget (deferred or direct)
        self.dock_widget = DuckGISDockWidget(self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        self.dock_widget.hide()

    def toggle_dock_widget(self):
        """Toggles the visibility of DuckGIS dock widget."""
        if not self.dock_widget:
            return

        if self.dock_widget.isVisible():
            self.dock_widget.hide()
        else:
            self.dock_widget.show()
            self.dock_widget.raise_()

    def unload(self):
        """Cleans up GUI elements on plugin unload / disable."""
        if not QT_AVAILABLE:
            return

        if self.action:
            self.iface.removePluginDatabaseMenu("&DuckGIS", self.action)
            self.iface.removeDatabaseToolBarIcon(self.action)
            self.action = None

        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None
