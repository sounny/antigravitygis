"""
test_agent_core.py - Unit & Integration Test for AntigravityGIS Core Engine & ArcPy Tools
"""

import os
import sys
import unittest

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_core import (
    GISAntigravityAgent,
    inspect_directory_spatial_data,
    inspect_arcgis_workspace,
    describe_arcgis_dataset,
    run_arcpy_geoprocessing,
    format_graceful_error,
)
from qgis.qgis_agent_core import (
    inspect_qgis_active_project,
    describe_qgis_layer,
    run_pyqgis_code,
    zoom_to_qgis_layer,
    add_vector_layer_to_qgis,
)


class TestGISAntigravityCore(unittest.TestCase):

    def test_directory_spatial_data_inspection(self):
        """Test spatial dataset inspection utility."""
        test_dir = os.path.dirname(__file__)
        result = inspect_directory_spatial_data(test_dir)
        self.assertIn("shapefiles", result)
        self.assertIn("geodatabases", result)
        self.assertIn("geojson", result)

    def test_agent_initialization(self):
        """Test instantiation of GISAntigravityAgent."""
        runner = GISAntigravityAgent()
        cfg = runner._build_config()
        self.assertIsNotNone(cfg)
        self.assertGreaterEqual(len(runner.custom_tools), 4)

        # Test tool registration
        def custom_tool():
            pass
        runner.register_tool(custom_tool)
        self.assertIn("custom_tool", runner.custom_tools)
        cfg_updated = runner._build_config()
        self.assertEqual(len(cfg_updated.tools), len(runner.custom_tools))

    def test_arcpy_tool_fallback_handling(self):
        """Verify ArcPy tools return structured error/fallback when ArcPy is absent."""
        res_ws = inspect_arcgis_workspace("/non/existent/workspace.gdb")
        self.assertTrue("error" in res_ws or "workspace" in res_ws)

        res_desc = describe_arcgis_dataset("/non/existent/dataset")
        self.assertTrue("error" in res_desc or "dataset" in res_desc)

        res_gp = run_arcpy_geoprocessing("Buffer_analysis", in_features="a", out_feature_class="b")
        self.assertTrue("error" in res_gp or "status" in res_gp)

    def test_qgis_tool_fallback_handling(self):
        """Verify PyQGIS tools return structured fallback when PyQGIS is absent."""
        res_proj = inspect_qgis_active_project()
        self.assertIsInstance(res_proj, str)

        res_desc = describe_qgis_layer("test_layer")
        self.assertTrue("Error" in res_desc or "Layer" in res_desc or "{" in res_desc)

        res_code = run_pyqgis_code("x = 1 + 1")
        self.assertIn("✅", res_code)

    def test_graceful_error_formatting(self):
        """Verify graceful error formatter provides actionable messages."""
        err_dns = Exception("dial tcp: lookup generativelanguage.googleapis.com: no such host")
        msg_dns = format_graceful_error(err_dns)
        self.assertIn("Connectivity Notice", msg_dns)

        err_auth = Exception("API_KEY_INVALID")
        msg_auth = format_graceful_error(err_auth)
        self.assertIn("API Key Required", msg_auth)

        err_429 = Exception("RESOURCE_EXHAUSTED 429")
        msg_429 = format_graceful_error(err_429)
        self.assertIn("Rate Limit", msg_429)


if __name__ == "__main__":
    unittest.main()
