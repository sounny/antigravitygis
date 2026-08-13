# AntigravityGIS for QGIS (Coming Soon)

**AntigravityGIS by Sounny** ([sounny.com](https://sounny.com)) is expanding to support **QGIS** natively!

Because [`agent_core.py`](file:///g:/My%20Drive/AntigravityGIS/agent_core.py) is decoupled from desktop UI frameworks, the core Google Antigravity Agent engine works seamlessly across both ArcGIS Pro and QGIS.

---

## 🗺️ QGIS Plugin Architecture Blueprint

- **Core Engine**: Shares the platform-agnostic `GISAntigravityAgent` harness.
- **PyQGIS & GDAL Bindings**: Exposes PyQGIS tools (`QgsProject`, `QgsVectorLayer`, `QgsRasterLayer`, GDAL) to the Antigravity Agent.
- **Qt Dockable Panel**: Provides an interactive dockable panel directly inside the QGIS interface for natural-language spatial prompting off your Google Antigravity account.

---

## PyQGIS Tool Example

```python
from qgis.core import QgsProject

def inspect_qgis_active_project() -> str:
    """Tool registered with Antigravity Agent when running inside QGIS."""
    layers = QgsProject.instance().mapLayers().values()
    summary = []
    for layer in layers:
        summary.append(f"Layer: {layer.name()} | Type: {layer.type().name} | Feature Count: {layer.featureCount()}")
    return "\n".join(summary)
```
