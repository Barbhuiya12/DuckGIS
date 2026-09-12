# -*- coding: utf-8 -*-
"""
Tests for DuckDBEngine and query parsing.
"""

import unittest
from unittest.mock import MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from duckdb_engine import DuckDBEngine, DuckDBNotFoundError, DuckDBExecutionError


class TestDuckDBEngine(unittest.TestCase):

    def test_missing_duckdb_raises_error(self):
        """Verify that DuckDBNotFoundError is raised when duckdb is not installed."""
        original_module = sys.modules.get("duckdb")
        try:
            sys.modules["duckdb"] = None
            with self.assertRaises(DuckDBNotFoundError):
                DuckDBEngine(":memory:")
        finally:
            if original_module is not None:
                sys.modules["duckdb"] = original_module
            elif "duckdb" in sys.modules:
                del sys.modules["duckdb"]

    def test_detect_geometry_column_by_type(self):
        """Verify detection of GEOMETRY type columns."""
        mock_duckdb = MagicMock()
        sys.modules["duckdb"] = mock_duckdb
        try:
            engine = DuckDBEngine.__new__(DuckDBEngine)
            columns = ["id", "name", "the_spatial_col"]
            types = ["INTEGER", "VARCHAR", "GEOMETRY"]
            sample_rows = [(1, "sample", b"\x01\x01\x00\x00\x00")]

            detected = engine._detect_geometry_column(columns, types, sample_rows)
            self.assertEqual(detected, "the_spatial_col")
        finally:
            if "duckdb" in sys.modules and sys.modules["duckdb"] is mock_duckdb:
                del sys.modules["duckdb"]

    def test_detect_geometry_column_by_name(self):
        """Verify detection of standard geometry column names (geom, geometry)."""
        mock_duckdb = MagicMock()
        sys.modules["duckdb"] = mock_duckdb
        try:
            engine = DuckDBEngine.__new__(DuckDBEngine)
            columns = ["id", "geom", "population"]
            types = ["INTEGER", "BLOB", "INTEGER"]
            sample_rows = [(10, b"data", 5000)]

            detected = engine._detect_geometry_column(columns, types, sample_rows)
            self.assertEqual(detected, "geom")
        finally:
            if "duckdb" in sys.modules and sys.modules["duckdb"] is mock_duckdb:
                del sys.modules["duckdb"]

    def test_detect_geometry_column_by_wkt_string(self):
        """Verify detection of WKT geometry strings."""
        mock_duckdb = MagicMock()
        sys.modules["duckdb"] = mock_duckdb
        try:
            engine = DuckDBEngine.__new__(DuckDBEngine)
            columns = ["id", "shape_str"]
            types = ["INTEGER", "VARCHAR"]
            sample_rows = [(1, "POINT(-122.4 37.7)")]

            detected = engine._detect_geometry_column(columns, types, sample_rows)
            self.assertEqual(detected, "shape_str")
        finally:
            if "duckdb" in sys.modules and sys.modules["duckdb"] is mock_duckdb:
                del sys.modules["duckdb"]

    def test_empty_sql_raises_error(self):
        """Verify that empty SQL raises DuckDBExecutionError."""
        mock_duckdb = MagicMock()
        sys.modules["duckdb"] = mock_duckdb
        try:
            engine = DuckDBEngine.__new__(DuckDBEngine)
            engine._conn = mock_duckdb.connect.return_value
            with self.assertRaises(DuckDBExecutionError):
                engine.execute_query("   ;   ")
        finally:
            if "duckdb" in sys.modules and sys.modules["duckdb"] is mock_duckdb:
                del sys.modules["duckdb"]


if __name__ == "__main__":
    unittest.main()
