# -*- coding: utf-8 -*-
"""
DuckGIS - Layer Bridge
Two-way bridge for converting between DuckDB query results and QGIS Vector Layers.
"""

import os
import tempfile
from typing import Dict, Any, Optional, Tuple

try:
    from qgis.core import (
        QgsVectorLayer,
        QgsField,
        QgsFeature,
        QgsGeometry,
        QgsCoordinateReferenceSystem,
        QgsProject,
        QgsWkbTypes,
    )
    from PyQt5.QtCore import QVariant, QDate, QDateTime
    QGIS_AVAILABLE = True
except ImportError:
    # Standalone test / mock fallback
    QGIS_AVAILABLE = False


class LayerBridgeError(Exception):
    """Raised when layer conversion fails."""
    pass


class LayerBridge:
    """Handles data exchange between DuckDB and QGIS."""

    @staticmethod
    def is_qgis_active() -> bool:
        """Returns True if running inside QGIS environment."""
        return QGIS_AVAILABLE

    @classmethod
    def duckdb_result_to_layer(
        cls,
        result_data: Dict[str, Any],
        layer_name: str = "DuckDB Result",
        crs_authid: str = "EPSG:4326",
        geom_col_override: Optional[str] = None,
        use_temp_file_threshold: int = 25000,
    ) -> Any:
        """
        Converts DuckDB query result dictionary to a QgsVectorLayer.
        Uses in-memory layer for fast interactive queries, or temporary GeoPackage
        if row count exceeds threshold.
        """
        if not QGIS_AVAILABLE:
            raise LayerBridgeError("PyQGIS libraries are not available in this environment.")

        columns = result_data.get("columns", [])
        types = result_data.get("types", [])
        rows = result_data.get("rows", [])
        geom_col = geom_col_override or result_data.get("geom_column")

        if not rows:
            raise LayerBridgeError("Query returned 0 rows. No layer created.")

        geom_idx = -1
        if geom_col and geom_col in columns:
            geom_idx = columns.index(geom_col)

        # Detect primary geometry type from first valid feature
        wkb_type_str = "None"
        sample_geom = None
        if geom_idx >= 0:
            for row in rows:
                val = row[geom_idx]
                if val is not None:
                    sample_geom = cls._parse_geometry(val)
                    if sample_geom and not sample_geom.isNull():
                        wkb_type_str = cls._wkb_type_to_string(sample_geom.wkbType())
                        break

        # Build QGIS memory layer URI
        crs_def = crs_authid if crs_authid else "EPSG:4326"
        uri = f"{wkb_type_str}?crs={crs_def}"
        layer = QgsVectorLayer(uri, layer_name, "memory")

        if not layer.isValid():
            raise LayerBridgeError(f"Failed to create valid QGIS layer with URI: {uri}")

        pr = layer.dataProvider()

        # Map attribute columns (excluding geometry column)
        attribute_fields = []
        attr_indices = []
        for idx, (col_name, col_type) in enumerate(zip(columns, types)):
            if idx == geom_idx:
                continue
            variant_type = cls._duckdb_type_to_qvariant(col_type)
            attribute_fields.append(QgsField(col_name, variant_type))
            attr_indices.append(idx)

        layer.startEditing()
        pr.addAttributes(attribute_fields)
        layer.updateFields()

        # Build QgsFeature batch
        qgis_features = []
        for row in rows:
            feat = QgsFeature(layer.fields())
            
            # Geometry
            if geom_idx >= 0:
                raw_geom = row[geom_idx]
                if raw_geom is not None:
                    q_geom = cls._parse_geometry(raw_geom)
                    if q_geom and not q_geom.isNull():
                        feat.setGeometry(q_geom)

            # Attributes
            attrs = [cls._sanitize_attribute_value(row[i]) for i in attr_indices]
            feat.setAttributes(attrs)
            qgis_features.append(feat)

        pr.addFeatures(qgis_features)
        layer.commitChanges()
        layer.updateExtents()

        return layer

    @classmethod
    def _parse_geometry(cls, raw_val: Any) -> Optional[Any]:
        """Converts raw DuckDB geometry (WKB bytes, WKT string, or GeoJSON) into QgsGeometry."""
        if raw_val is None:
            return None

        # Binary WKB
        if isinstance(raw_val, (bytes, bytearray)):
            try:
                geom = QgsGeometry()
                geom.fromWkb(bytes(raw_val))
                return geom
            except Exception:
                return None

        # String: WKT or GeoJSON
        if isinstance(raw_val, str):
            s = raw_val.strip()
            if s.startswith("{") and s.endswith("}"):
                return QgsGeometry.fromGeoJson(s)
            elif s.upper().startswith(("POINT", "LINE", "POLY", "MULTI", "GEOMETRY")):
                return QgsGeometry.fromWkt(s)

        return None

    @staticmethod
    def _wkb_type_to_string(wkb_type: int) -> str:
        """Converts QgsWkbTypes into layer URI geometry string."""
        flat = QgsWkbTypes.flatType(wkb_type)
        type_map = {
            QgsWkbTypes.Point: "Point",
            QgsWkbTypes.LineString: "LineString",
            QgsWkbTypes.Polygon: "Polygon",
            QgsWkbTypes.MultiPoint: "MultiPoint",
            QgsWkbTypes.MultiLineString: "MultiLineString",
            QgsWkbTypes.MultiPolygon: "MultiPolygon",
            QgsWkbTypes.GeometryCollection: "GeometryCollection",
            QgsWkbTypes.Unknown: "Geometry",
            QgsWkbTypes.NoGeometry: "None",
        }
        return type_map.get(flat, "Geometry")

    @staticmethod
    def _duckdb_type_to_qvariant(type_str: str) -> Any:
        """Maps DuckDB SQL type string to QVariant type."""
        t = type_str.upper()
        if any(x in t for x in ("INT", "BIGINT", "SMALLINT", "TINYINT", "HUGEINT")):
            return QVariant.LongLong
        elif any(x in t for x in ("DOUBLE", "FLOAT", "REAL", "DECIMAL", "NUMERIC")):
            return QVariant.Double
        elif "BOOL" in t:
            return QVariant.Bool
        elif "DATE" in t:
            return QVariant.Date
        elif "TIME" in t:
            return QVariant.DateTime
        else:
            return QVariant.String

    @staticmethod
    def _sanitize_attribute_value(val: Any) -> Any:
        """Normalizes Python values for QgsFeature attributes."""
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            import json
            return json.dumps(val)
        return val

    @classmethod
    def register_qgis_layer_in_duckdb(cls, qgis_layer: Any, duckdb_engine: Any, view_name: Optional[str] = None) -> str:
        """
        Exposes an active QGIS layer inside DuckDB so users can query it with SQL.
        Uses direct zero-copy file reader for GeoPackage/Shapefile/Parquet, or
        temporary Parquet dump for memory layers.
        """
        if not QGIS_AVAILABLE or not qgis_layer or not qgis_layer.isValid():
            raise LayerBridgeError("Invalid QGIS layer.")

        name = view_name or qgis_layer.name().lower().replace(" ", "_").replace("-", "_")
        name = "".join(c for c in name if c.isalnum() or c == "_")
        if not name:
            name = "qgis_layer"

        source = qgis_layer.source()
        # If the layer points directly to a file that DuckDB Spatial can read directly
        if os.path.exists(source) and source.lower().endswith((".gpkg", ".shp", ".parquet", ".geojson", ".fgb")):
            escaped_source = source.replace("'", "''")
            if source.lower().endswith(".parquet"):
                sql = f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{escaped_source}');"
            else:
                sql = f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM ST_Read('{escaped_source}');"
            duckdb_engine.execute_query(sql)
            return name

        # Otherwise, export layer to a temporary GeoPackage and register
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, f"duckgis_{name}.gpkg").replace("\\", "/")
        
        from qgis.core import QgsVectorFileWriter
        write_result, _ = QgsVectorFileWriter.writeAsVectorFormat(
            qgis_layer,
            tmp_path,
            "UTF-8",
            qgis_layer.crs(),
            "GPKG"
        )
        if write_result != QgsVectorFileWriter.NoError:
            raise LayerBridgeError(f"Failed to export QGIS layer for DuckDB registration (Error {write_result}).")

        sql = f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM ST_Read('{tmp_path}');"
        duckdb_engine.execute_query(sql)
        return name
