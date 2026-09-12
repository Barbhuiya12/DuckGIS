# -*- coding: utf-8 -*-
"""
Tests for LayerBridge data transformation logic.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layer_bridge import LayerBridge


class TestLayerBridge(unittest.TestCase):

    def test_sanitize_attribute_values(self):
        """Verify handling of complex attributes like JSON dicts or lists."""
        self.assertEqual(LayerBridge._sanitize_attribute_value(None), None)
        self.assertEqual(LayerBridge._sanitize_attribute_value("hello"), "hello")
        self.assertEqual(LayerBridge._sanitize_attribute_value(1234), 1234)
        self.assertEqual(LayerBridge._sanitize_attribute_value({"key": "val"}), '{"key": "val"}')
        self.assertEqual(LayerBridge._sanitize_attribute_value([1, 2, 3]), '[1, 2, 3]')

    def test_empty_rows_raises_error(self):
        """Verify that 0-row results raise descriptive LayerBridgeError if QGIS is present."""
        if LayerBridge.is_qgis_active():
            from layer_bridge import LayerBridgeError
            with self.assertRaises(LayerBridgeError):
                LayerBridge.duckdb_result_to_layer({"columns": ["a"], "types": ["INT"], "rows": []})


if __name__ == "__main__":
    unittest.main()
