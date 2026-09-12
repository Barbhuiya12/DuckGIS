# -*- coding: utf-8 -*-
"""
DuckGIS - Main Dock Widget
Interactive Spatial SQL Studio and Cloud GeoParquet query engine.
"""

import os
import json
from typing import Optional, Dict, Any

try:
    from PyQt5.QtWidgets import (
        QDockWidget,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QSplitter,
        QLabel,
        QPushButton,
        QComboBox,
        QLineEdit,
        QPlainTextEdit,
        QTableWidget,
        QTableWidgetItem,
        QFileDialog,
        QMessageBox,
        QToolBar,
        QAction,
        QMenu,
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QSize
    from PyQt5.QtGui import QIcon, QFont, QKeySequence
    from qgis.core import QgsProject, QgsCoordinateReferenceSystem
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

from duckdb_engine import DuckDBEngine, DuckDBNotFoundError, DuckDBExecutionError
from layer_bridge import LayerBridge, LayerBridgeError
from ui.sql_highlighter import SQLHighlighter
from ui.dependency_dialog import DependencyDialog
from ui.styles import MODERN_STYLESHEET


class DuckGISDockWidget(QDockWidget if QT_AVAILABLE else object):
    """Dockable DuckDB Spatial Studio panel for QGIS."""

    def __init__(self, iface, parent=None):
        if not QT_AVAILABLE:
            return
        super().__init__("DuckGIS — Spatial Studio", parent)
        self.iface = iface
        self.engine: Optional[DuckDBEngine] = None
        self.last_result: Optional[Dict[str, Any]] = None

        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.setStyleSheet(MODERN_STYLESHEET)

        self._init_engine()
        self._setup_ui()
        self._load_presets()

    def _init_engine(self):
        """Initializes the DuckDB engine."""
        try:
            self.engine = DuckDBEngine(":memory:")
        except DuckDBNotFoundError:
            self.engine = None

    def _setup_ui(self):
        """Builds dock widget layout and controls."""
        main_widget = QWidget(self)
        self.setWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # -------------------------------------------------------------
        # 1. Top Control Bar (Presets, BBox Macro, Run Button)
        # -------------------------------------------------------------
        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)

        # Preset selector
        self.combo_presets = QComboBox()
        self.combo_presets.setToolTip("Select a pre-configured spatial query snippet")
        self.combo_presets.addItem("⚡ Select a Preset Query...")
        self.combo_presets.currentIndexChanged.connect(self._on_preset_selected)
        top_bar.addWidget(self.combo_presets, stretch=2)

        # Insert Bounding Box
        self.btn_insert_bbox = QPushButton("📍 Map BBox")
        self.btn_insert_bbox.setObjectName("btnInsertBBox")
        self.btn_insert_bbox.setToolTip("Insert current QGIS map canvas extent into query")
        self.btn_insert_bbox.clicked.connect(self._insert_canvas_bbox)
        top_bar.addWidget(self.btn_insert_bbox)

        # Query Active Layer
        self.btn_register_layer = QPushButton("📥 Import Layer")
        self.btn_register_layer.setToolTip("Register current active QGIS layer as a DuckDB table")
        self.btn_register_layer.clicked.connect(self._register_active_layer)
        top_bar.addWidget(self.btn_register_layer)

        # Run Button
        self.btn_run = QPushButton("▶ Run (Ctrl+Enter)")
        self.btn_run.setObjectName("btnRunQuery")
        self.btn_run.setToolTip("Execute SQL in DuckDB (Ctrl+Enter)")
        self.btn_run.clicked.connect(self.run_query)
        top_bar.addWidget(self.btn_run)

        main_layout.addLayout(top_bar)

        # -------------------------------------------------------------
        # 2. Main Vertical Splitter (SQL Editor on top, Results below)
        # -------------------------------------------------------------
        splitter = QSplitter(Qt.Vertical)

        # SQL Editor container
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(2)

        self.sql_editor = QPlainTextEdit()
        self.sql_editor.setObjectName("sqlEditor")
        self.sql_editor.setPlaceholderText(
            "-- Write Spatial SQL or select a preset above\n"
            "SELECT 1 AS id, ST_Point(0, 0) AS geom;"
        )
        self.highlighter = SQLHighlighter(self.sql_editor.document())
        editor_layout.addWidget(self.sql_editor)
        splitter.addWidget(editor_container)

        # Results Container
        results_container = QWidget()
        results_layout = QVBoxLayout(results_container)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(4)

        # Status & Metrics Bar
        status_bar = QHBoxLayout()
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("lblStatusBadge")
        self.lbl_status.setProperty("status", "ready")
        status_bar.addWidget(self.lbl_status)

        self.lbl_metrics = QLabel("")
        status_bar.addWidget(self.lbl_metrics, stretch=1)

        results_layout.addLayout(status_bar)

        # Table Preview
        self.tbl_results = QTableWidget()
        self.tbl_results.setObjectName("tblResults")
        self.tbl_results.setAlternatingRowColors(True)
        results_layout.addWidget(self.tbl_results)

        # Map Export & Layer Actions Bar
        actions_bar = QHBoxLayout()
        actions_bar.setSpacing(6)

        actions_bar.addWidget(QLabel("Layer Name:"))
        self.txt_layer_name = QLineEdit("duckdb_result")
        actions_bar.addWidget(self.txt_layer_name, stretch=1)

        actions_bar.addWidget(QLabel("Geom Col:"))
        self.combo_geom_col = QComboBox()
        self.combo_geom_col.setMinimumWidth(100)
        actions_bar.addWidget(self.combo_geom_col)

        actions_bar.addWidget(QLabel("CRS:"))
        self.combo_crs = QComboBox()
        self.combo_crs.addItems(["EPSG:4326", "EPSG:3857", "Project CRS"])
        actions_bar.addWidget(self.combo_crs)

        self.btn_add_to_map = QPushButton("🗺️ Add to Canvas")
        self.btn_add_to_map.setObjectName("btnAddToMap")
        self.btn_add_to_map.setToolTip("Add current query result as a vector layer to QGIS canvas")
        self.btn_add_to_map.setEnabled(False)
        self.btn_add_to_map.clicked.connect(self._add_to_qgis_canvas)
        actions_bar.addWidget(self.btn_add_to_map)

        self.btn_export = QPushButton("💾 Export...")
        self.btn_export.setToolTip("Export query results directly to GeoParquet, GeoPackage, or CSV")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export_results)
        actions_bar.addWidget(self.btn_export)

        results_layout.addLayout(actions_bar)
        splitter.addWidget(results_container)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter)

    def _load_presets(self):
        """Loads preset queries from query_library.json."""
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        preset_file = os.path.join(current_dir, "presets", "query_library.json")
        if not os.path.exists(preset_file):
            return

        try:
            with open(preset_file, "r", encoding="utf-8") as f:
                self.preset_data = json.load(f)
            for preset in self.preset_data:
                title = preset.get("title", "Untitled")
                category = preset.get("category", "")
                label = f"[{category}] {title}" if category else title
                self.combo_presets.addItem(label, preset)
        except Exception as e:
            self._set_status(f"Error loading presets: {e}", "error")

    def _on_preset_selected(self, index: int):
        """Inserts selected preset SQL into the editor."""
        if index <= 0:
            return
        preset = self.combo_presets.itemData(index)
        if preset and "sql" in preset:
            self.sql_editor.setPlainText(preset["sql"])

    def _insert_canvas_bbox(self):
        """Replaces {{BBOX_*}} macros or inserts current canvas bounding box."""
        if not self.iface:
            return
        extent = self.iface.mapCanvas().extent()
        # Transform extent to EPSG:4326 if map CRS is different
        map_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")

        from qgis.core import QgsCoordinateTransform
        transform = QgsCoordinateTransform(map_crs, epsg4326, QgsProject.instance())
        try:
            bbox = transform.transformBoundingBox(extent)
        except Exception:
            bbox = extent

        xmin, ymin, xmax, ymax = bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()

        current_text = self.sql_editor.toPlainText()
        if "{{BBOX_XMIN}}" in current_text or "{{BBOX_XMAX}}" in current_text:
            new_text = (
                current_text.replace("{{BBOX_XMIN}}", f"{xmin:.6f}")
                .replace("{{BBOX_YMIN}}", f"{ymin:.6f}")
                .replace("{{BBOX_XMAX}}", f"{xmax:.6f}")
                .replace("{{BBOX_YMAX}}", f"{ymax:.6f}")
            )
            self.sql_editor.setPlainText(new_text)
            self._set_status(f"Injected BBox: [{xmin:.3f}, {ymin:.3f}, {xmax:.3f}, {ymax:.3f}]", "ready")
        else:
            snippet = f"\n-- Filter by map extent:\nWHERE bbox.xmin <= {xmax:.6f} AND bbox.xmax >= {xmin:.6f} AND bbox.ymin <= {ymax:.6f} AND bbox.ymax >= {ymin:.6f}\n"
            cursor = self.sql_editor.textCursor()
            cursor.insertText(snippet)

    def _register_active_layer(self):
        """Registers the currently selected QGIS layer into DuckDB."""
        if not self.iface:
            return
        layer = self.iface.activeLayer()
        if not layer:
            QMessageBox.warning(self, "No Active Layer", "Please select a vector layer in QGIS first.")
            return

        if not self.engine:
            self._ensure_duckdb()
            return

        try:
            table_name = LayerBridge.register_qgis_layer_in_duckdb(layer, self.engine)
            snippet = f"\n-- Query registered layer:\nSELECT * FROM {table_name} LIMIT 100;\n"
            self.sql_editor.appendPlainText(snippet)
            self._set_status(f"Registered '{layer.name()}' as DuckDB table '{table_name}'", "ready")
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Could not register layer in DuckDB:\n{str(e)}")

    def _ensure_duckdb(self) -> bool:
        """Checks if DuckDB is installed; opens installer dialog if not."""
        if self.engine and self.engine.is_ready:
            return True
        dialog = DependencyDialog(self)
        if dialog.exec_() == DependencyDialog.Accepted:
            self._init_engine()
            return self.engine is not None and self.engine.is_ready
        return False

    def run_query(self):
        """Executes the query in SQL editor."""
        if not self._ensure_duckdb():
            return

        sql = self.sql_editor.toPlainText().strip()
        if not sql:
            self._set_status("SQL query is empty", "error")
            return

        self._set_status("Executing...", "running")
        self.btn_run.setEnabled(False)

        try:
            result = self.engine.execute_query(sql, preview_limit=500)
            self.last_result = result
            self._populate_results(result)
            self._set_status("Query completed", "ready")
            self.lbl_metrics.setText(
                f"⏱️ <b>{result['execution_time_ms']:.1f} ms</b> | "
                f"Rows: <b>{result['total_rows']:,}</b>"
                + (" (Showing 500)" if result["is_preview"] else "")
            )
            self.btn_add_to_map.setEnabled(result["total_rows"] > 0)
            self.btn_export.setEnabled(result["total_rows"] > 0)
        except DuckDBExecutionError as err:
            self._set_status("Error", "error")
            self.lbl_metrics.setText(f"<span style='color: #c62828;'>{str(err)}</span>")
            self.btn_add_to_map.setEnabled(False)
            self.btn_export.setEnabled(False)
        finally:
            self.btn_run.setEnabled(True)

    def _populate_results(self, result: Dict[str, Any]):
        """Populates the preview table and geometry dropdown."""
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        geom_col = result.get("geom_column")

        # Update table
        self.tbl_results.clear()
        self.tbl_results.setColumnCount(len(columns))
        self.tbl_results.setRowCount(len(rows))
        self.tbl_results.setHorizontalHeaderLabels(columns)

        for row_idx, row in enumerate(rows):
            for col_idx, val in enumerate(row):
                text_val = str(val) if val is not None else "NULL"
                if isinstance(val, (bytes, bytearray)):
                    text_val = f"<WKB Binary {len(val)} bytes>"
                elif len(text_val) > 100:
                    text_val = text_val[:100] + "..."
                item = QTableWidgetItem(text_val)
                self.tbl_results.setItem(row_idx, col_idx, item)

        self.tbl_results.resizeColumnsToContents()

        # Update geometry column dropdown
        self.combo_geom_col.clear()
        self.combo_geom_col.addItem("Auto-detect" if geom_col else "No geometry", geom_col)
        for col in columns:
            self.combo_geom_col.addItem(col, col)
        if geom_col and geom_col in columns:
            idx = self.combo_geom_col.findText(geom_col)
            if idx >= 0:
                self.combo_geom_col.setCurrentIndex(idx)

    def _add_to_qgis_canvas(self):
        """Converts DuckDB query results to a QGIS layer and displays on map."""
        if not self.last_result:
            return

        layer_name = self.txt_layer_name.text().strip() or "duckdb_result"
        geom_col = self.combo_geom_col.currentData()
        crs_text = self.combo_crs.currentText()

        crs_id = "EPSG:4326"
        if crs_text == "EPSG:3857":
            crs_id = "EPSG:3857"
        elif crs_text == "Project CRS" and self.iface:
            crs_id = self.iface.mapCanvas().mapSettings().destinationCrs().authid()

        try:
            layer = LayerBridge.duckdb_result_to_layer(
                self.last_result,
                layer_name=layer_name,
                crs_authid=crs_id,
                geom_col_override=geom_col
            )
            QgsProject.instance().addMapLayer(layer)
            self._set_status(f"Added layer '{layer_name}' to canvas ({layer.featureCount()} features)", "ready")
        except Exception as e:
            QMessageBox.critical(self, "Layer Creation Failed", str(e))

    def _export_results(self):
        """Exports the current query directly to GeoParquet, GeoPackage, or CSV."""
        if not self.engine:
            return
        sql = self.sql_editor.toPlainText().strip()
        if not sql:
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export DuckDB Query Result",
            "",
            "GeoParquet (*.parquet);;GeoPackage (*.gpkg);;CSV (*.csv);;GeoJSON (*.geojson)"
        )
        if not file_path:
            return

        fmt = "PARQUET"
        if file_path.endswith(".gpkg"):
            fmt = "GPKG"
        elif file_path.endswith(".csv"):
            fmt = "CSV"
        elif file_path.endswith(".geojson"):
            fmt = "GEOJSON"

        try:
            elapsed = self.engine.export_query_to_file(sql, file_path, fmt)
            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported query results to:\n{file_path}\n(Completed in {elapsed:.1f} ms)"
            )
        except Exception as err:
            QMessageBox.critical(self, "Export Failed", f"Could not export:\n{str(err)}")

    def _set_status(self, text: str, status: str = "ready"):
        """Updates status badge style and text."""
        self.lbl_status.setText(text)
        self.lbl_status.setProperty("status", status)
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)
