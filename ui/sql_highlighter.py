# -*- coding: utf-8 -*-
"""
DuckGIS - SQL Syntax Highlighter
Provides syntax highlighting for SQL and DuckDB Spatial functions in QPlainTextEdit.
"""

try:
    from qgis.PyQt.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
    from qgis.PyQt.QtCore import QRegularExpression
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


if QT_AVAILABLE:
    class SQLHighlighter(QSyntaxHighlighter):
        """Syntax highlighter for SQL, DuckDB built-ins, and spatial functions."""

        def __init__(self, document):
            super().__init__(document)
            self._highlighting_rules = []

            # Formats
            keyword_format = QTextCharFormat()
            keyword_format.setForeground(QColor("#0000bb"))
            keyword_format.setFontWeight(QFont.Bold)

            spatial_format = QTextCharFormat()
            spatial_format.setForeground(QColor("#008080"))
            spatial_format.setFontWeight(QFont.Bold)

            duckdb_func_format = QTextCharFormat()
            duckdb_func_format.setForeground(QColor("#d35400"))
            duckdb_func_format.setFontWeight(QFont.Bold)

            macro_format = QTextCharFormat()
            macro_format.setForeground(QColor("#e67e22"))
            macro_format.setFontWeight(QFont.Bold)
            macro_format.setFontItalic(True)

            string_format = QTextCharFormat()
            string_format.setForeground(QColor("#a11"))

            number_format = QTextCharFormat()
            number_format.setForeground(QColor("#116644"))

            comment_format = QTextCharFormat()
            comment_format.setForeground(QColor("#7f8c8d"))
            comment_format.setFontItalic(True)

            # SQL Keywords
            keywords = [
                "SELECT", "FROM", "WHERE", "GROUP", "BY", "ORDER", "HAVING", "LIMIT",
                "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "CROSS", "FULL", "ON",
                "AS", "AND", "OR", "NOT", "IN", "IS", "NULL", "LIKE", "ILIKE",
                "EXISTS", "BETWEEN", "CASE", "WHEN", "THEN", "ELSE", "END", "DISTINCT",
                "UNION", "ALL", "EXCLUDE", "REPLACE", "WITH", "CREATE", "TABLE",
                "VIEW", "DROP", "INSERT", "INTO", "VALUES", "COPY", "TO", "DESCRIBE"
            ]
            for word in keywords:
                pattern = QRegularExpression(r"\b" + word + r"\b", QRegularExpression.CaseInsensitiveOption)
                self._highlighting_rules.append((pattern, keyword_format))

            # DuckDB Spatial Functions (ST_*)
            spatial_patterns = [
                r"\bST_[A-Za-z0-9_]+\b",
            ]
            for spat in spatial_patterns:
                self._highlighting_rules.append((QRegularExpression(spat, QRegularExpression.CaseInsensitiveOption), spatial_format))

            # DuckDB Special I/O Functions
            duck_funcs = [
                r"\bread_parquet\b", r"\bread_csv\b", r"\bread_json\b",
                r"\bparquet_scan\b", r"\brange\b"
            ]
            for df in duck_funcs:
                self._highlighting_rules.append((QRegularExpression(df, QRegularExpression.CaseInsensitiveOption), duckdb_func_format))

            # Template BBOX Macros: {{BBOX_...}}
            self._highlighting_rules.append((QRegularExpression(r"\{\{[A-Za-z0-9_]+\}\}"), macro_format))

            # Numbers
            self._highlighting_rules.append((QRegularExpression(r"\b[0-9]+(?:\.[0-9]+)?\b"), number_format))

            # Strings: 'single quoted'
            self._highlighting_rules.append((QRegularExpression(r"'[^'\\]*(?:\\.[^'\\]*)*'"), string_format))

            # Single-line comment: -- ...
            self._highlighting_rules.append((QRegularExpression(r"--[^\n]*"), comment_format))

        def highlightBlock(self, text):
            """Applies formatting rules across each block of text."""
            for pattern, char_format in self._highlighting_rules:
                match_iterator = pattern.globalMatch(text)
                while match_iterator.hasNext():
                    match = match_iterator.next()
                    self.setFormat(match.capturedStart(), match.capturedLength(), char_format)
else:
    class SQLHighlighter:
        """Dummy fallback when Qt is not installed."""
        def __init__(self, *args, **kwargs):
            pass
