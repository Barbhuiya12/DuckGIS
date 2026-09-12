# -*- coding: utf-8 -*-
"""
End-to-end integration test with live DuckDB and DuckDB Spatial.
"""

import unittest
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from duckdb_engine import DuckDBEngine


class TestLiveDuckDB(unittest.TestCase):

    def setUp(self):
        self.engine = DuckDBEngine(":memory:")

    def test_engine_initialization(self):
        """Ensure DuckDB engine is ready and extensions are loaded."""
        self.assertTrue(self.engine.is_ready)
        exts = self.engine.load_extensions()
        print(f"\n[Live Test] Loaded extensions: {exts}")
        self.assertTrue(exts.get("spatial", False), "Spatial extension should be loaded successfully")

    def test_spatial_query_execution(self):
        """Execute real spatial SQL with ST_Point and ST_Buffer."""
        sql = """
        SELECT 
            1 AS id,
            'Central Park' AS location,
            ST_Point(-73.9654, 40.7829) AS geom,
            ST_Area(ST_Buffer(ST_Point(0, 0), 5.0)) AS circle_area;
        """
        result = self.engine.execute_query(sql)
        print(f"[Live Test] Spatial query execution time: {result['execution_time_ms']:.2f} ms")
        print(f"[Live Test] Columns: {result['columns']}")
        print(f"[Live Test] Geometry column detected: {result['geom_column']}")

        self.assertEqual(result["total_rows"], 1)
        self.assertEqual(result["columns"], ["id", "location", "geom", "circle_area"])
        self.assertEqual(result["geom_column"], "geom")
        self.assertGreater(result["rows"][0][3], 70.0)  # pi * r^2 ~ 78.5

    def test_export_to_parquet_and_csv(self):
        """Verify direct export to Parquet and CSV files."""
        sql = "SELECT i AS id, ST_Point(i * 0.1, i * 0.2) AS geom FROM range(1, 100) t(i);"
        with tempfile.TemporaryDirectory() as tmpdir:
            parquet_path = os.path.join(tmpdir, "test_output.parquet").replace("\\", "/")
            csv_path = os.path.join(tmpdir, "test_output.csv").replace("\\", "/")

            elapsed_p = self.engine.export_query_to_file(sql, parquet_path, "PARQUET")
            self.assertTrue(os.path.exists(parquet_path))
            self.assertGreater(os.path.getsize(parquet_path), 0)
            print(f"[Live Test] Exported 100 spatial rows to Parquet in {elapsed_p:.2f} ms ({os.path.getsize(parquet_path)} bytes)")

            elapsed_c = self.engine.export_query_to_file("SELECT i AS id, i*2 AS val FROM range(1, 50) t(i);", csv_path, "CSV")
            self.assertTrue(os.path.exists(csv_path))
            print(f"[Live Test] Exported to CSV in {elapsed_c:.2f} ms ({os.path.getsize(csv_path)} bytes)")


if __name__ == "__main__":
    unittest.main()
