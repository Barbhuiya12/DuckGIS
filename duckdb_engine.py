# -*- coding: utf-8 -*-
"""
DuckGIS - DuckDB Spatial Engine
Provides connection management, extension loading, and query execution for DuckDB Spatial.
"""

import time
import re
from typing import Dict, List, Any, Optional, Tuple


class DuckDBNotFoundError(ImportError):
    """Raised when duckdb package is not installed in the Python environment."""
    pass


class DuckDBExecutionError(Exception):
    """Raised when a SQL query execution fails in DuckDB."""
    pass


class DuckDBEngine:
    """Manages DuckDB instance, spatial extension, and query execution."""

    def __init__(self, database_path: str = ":memory:"):
        self.database_path = database_path
        self._conn = None
        self._duckdb = None
        self._spatial_loaded = False
        self._httpfs_loaded = False
        self._init_duckdb()

    def _init_duckdb(self):
        """Attempts to import duckdb and initialize database connection."""
        try:
            import duckdb
            self._duckdb = duckdb
        except ImportError:
            raise DuckDBNotFoundError(
                "The 'duckdb' Python package is not installed in this environment. "
                "Please use DuckGIS Dependency Installer to install it."
            )

        self._conn = self._duckdb.connect(self.database_path)
        self.load_extensions()

    @property
    def is_ready(self) -> bool:
        """Returns True if duckdb connection is active."""
        return self._conn is not None

    def load_extensions(self) -> Dict[str, bool]:
        """Installs and loads spatial and httpfs extensions."""
        status = {"spatial": False, "httpfs": False}
        if not self._conn:
            return status

        # Load spatial extension
        try:
            self._conn.execute("INSTALL spatial; LOAD spatial;")
            self._spatial_loaded = True
            status["spatial"] = True
        except Exception as e:
            # On some pre-configured builds, spatial may already be bundled or needs LOAD only
            try:
                self._conn.execute("LOAD spatial;")
                self._spatial_loaded = True
                status["spatial"] = True
            except Exception:
                status["spatial"] = False

        # Load httpfs extension for remote querying (s3://, https://)
        try:
            self._conn.execute("INSTALL httpfs; LOAD httpfs;")
            self._httpfs_loaded = True
            status["httpfs"] = True
        except Exception:
            try:
                self._conn.execute("LOAD httpfs;")
                self._httpfs_loaded = True
                status["httpfs"] = True
            except Exception:
                status["httpfs"] = False

        return status

    def execute_query(
        self, 
        sql: str, 
        preview_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes a SQL query and returns schema, rows, geometry metadata, and execution timing.
        
        Returns:
            dict containing:
                - 'columns': list of column names
                - 'types': list of column types
                - 'rows': list of row tuples (up to preview_limit if set)
                - 'total_rows': total number of rows returned
                - 'geom_column': detected geometry column name or None
                - 'execution_time_ms': execution time in milliseconds
                - 'is_preview': True if rows were truncated by preview_limit
        """
        if not self._conn:
            self._init_duckdb()

        # Sanitize and strip
        cleaned_sql = sql.strip().rstrip(";")
        if not cleaned_sql:
            raise DuckDBExecutionError("SQL query is empty.")

        start_time = time.perf_counter()
        try:
            cursor = self._conn.cursor()
            result = cursor.execute(cleaned_sql)
            description = cursor.description or []
            columns = [desc[0] for desc in description]
            types = [str(desc[1]) for desc in description]

            # Fetch data
            all_rows = cursor.fetchall()
            total_rows = len(all_rows)
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Detect geometry column
            geom_col = self._detect_geometry_column(columns, types, all_rows[:10])

            rows_to_return = all_rows
            is_preview = False
            if preview_limit and total_rows > preview_limit:
                rows_to_return = all_rows[:preview_limit]
                is_preview = True

            return {
                "columns": columns,
                "types": types,
                "rows": rows_to_return,
                "total_rows": total_rows,
                "geom_column": geom_col,
                "execution_time_ms": elapsed_ms,
                "is_preview": is_preview,
            }
        except Exception as err:
            raise DuckDBExecutionError(str(err)) from err

    def _detect_geometry_column(
        self, 
        columns: List[str], 
        types: List[str], 
        sample_rows: List[Tuple]
    ) -> Optional[str]:
        """Identifies which column represents spatial geometries."""
        # 1. Check by DuckDB column type name (GEOMETRY, POINT, etc.)
        for col, col_type in zip(columns, types):
            t_upper = col_type.upper()
            if "GEOMETRY" in t_upper or "POINT" in t_upper or "POLYGON" in t_upper:
                return col

        # 2. Check by column name conventions
        geom_names = {"geom", "geometry", "the_geom", "wkb_geometry", "shape", "wkt", "wkb"}
        for col in columns:
            if col.lower() in geom_names:
                return col

        # 3. Check sample values for WKB binary or GeoJSON / WKT
        for col_idx, col in enumerate(columns):
            for row in sample_rows:
                val = row[col_idx]
                if val is None:
                    continue
                # Byte/WKB check (starts with 0x00 or 0x01 byte order flag)
                if isinstance(val, (bytes, bytearray)) and len(val) >= 21:
                    if val[0] in (0, 1):
                        return col
                # WKT string check
                if isinstance(val, str):
                    val_strip = val.strip().upper()
                    if val_strip.startswith(("POINT", "LINESTRING", "POLYGON", "MULTIPOINT", "MULTILINESTRING", "MULTIPOLYGON", "GEOMETRYCOLLECTION")):
                        return col
        return None

    def export_query_to_file(self, sql: str, output_path: str, file_format: str = "PARQUET") -> float:
        """
        Exports query result directly to GeoParquet, GeoPackage, or CSV using DuckDB COPY.
        """
        if not self._conn:
            self._init_duckdb()

        start_time = time.perf_counter()
        fmt = file_format.upper()

        if fmt == "PARQUET":
            copy_sql = f"COPY ({sql.rstrip(';')}) TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD);"
        elif fmt == "CSV":
            copy_sql = f"COPY ({sql.rstrip(';')}) TO '{output_path}' (HEADER, DELIMITER ',');"
        elif fmt in ("GPKG", "GEOPACKAGE"):
            copy_sql = f"COPY ({sql.rstrip(';')}) TO '{output_path}' WITH (FORMAT GDAL, DRIVER 'GPKG');"
        elif fmt == "GEOJSON":
            copy_sql = f"COPY ({sql.rstrip(';')}) TO '{output_path}' WITH (FORMAT GDAL, DRIVER 'GeoJSON');"
        else:
            copy_sql = f"COPY ({sql.rstrip(';')}) TO '{output_path}';"

        try:
            self._conn.execute(copy_sql)
            return (time.perf_counter() - start_time) * 1000.0
        except Exception as e:
            raise DuckDBExecutionError(f"Export failed: {str(e)}") from e

    def close(self):
        """Closes connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
