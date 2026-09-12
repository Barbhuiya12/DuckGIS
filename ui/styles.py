# -*- coding: utf-8 -*-
"""
DuckGIS - UI Styles and Theme Tokens
Adaptive styles providing a clean, modern aesthetic compatible with QGIS themes.
"""

MODERN_STYLESHEET = """
/* DuckGIS Dock Widget Container */
QDockWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 12px;
}

/* Primary Action Buttons */
QPushButton#btnRunQuery {
    background-color: #2e7d32;
    color: #ffffff;
    font-weight: 600;
    border-radius: 4px;
    padding: 6px 14px;
    border: 1px solid #1b5e20;
}
QPushButton#btnRunQuery:hover {
    background-color: #388e3c;
}
QPushButton#btnRunQuery:pressed {
    background-color: #1b5e20;
}

QPushButton#btnAddToMap {
    background-color: #0277bd;
    color: #ffffff;
    font-weight: 600;
    border-radius: 4px;
    padding: 6px 12px;
    border: 1px solid #01579b;
}
QPushButton#btnAddToMap:hover {
    background-color: #0288d1;
}

QPushButton#btnInsertBBox {
    background-color: #e65100;
    color: #ffffff;
    font-weight: 500;
    border-radius: 4px;
    padding: 5px 10px;
    border: 1px solid #bf360c;
}
QPushButton#btnInsertBBox:hover {
    background-color: #f57c00;
}

/* Status & Metric Badges */
QLabel#lblStatusBadge {
    padding: 3px 8px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#lblStatusBadge[status="ready"] {
    background-color: #e8f5e9;
    color: #2e7d32;
    border: 1px solid #a5d6a7;
}

QLabel#lblStatusBadge[status="running"] {
    background-color: #fff8e1;
    color: #f57f17;
    border: 1px solid #ffe082;
}

QLabel#lblStatusBadge[status="error"] {
    background-color: #ffebee;
    color: #c62828;
    border: 1px solid #ffcdd2;
}

/* Results Table */
QTableView#tblResults {
    gridline-color: #e0e0e0;
    selection-background-color: #bbdefb;
    selection-color: #0d47a1;
    font-size: 11px;
}

QHeaderView::section {
    background-color: #f5f5f5;
    font-weight: bold;
    padding: 4px;
    border: 1px solid #e0e0e0;
}

/* SQL Editor */
QPlainTextEdit#sqlEditor {
    font-family: "SF Mono", "Menlo", "Monaco", "Consolas", "Courier New", monospace;
    font-size: 12px;
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: #fafafa;
    line-height: 1.4;
}
"""

def get_editor_font_family() -> str:
    """Returns suitable monospace font for platform."""
    return '"SF Mono", "Menlo", "Monaco", "Consolas", "Courier New", monospace'
