"""MyDocs-QA 入口（兼容 streamlit run app.py）。"""

import importlib.util
from pathlib import Path

_app = Path(__file__).resolve().parent / "ui" / "app.py"
_spec = importlib.util.spec_from_file_location("_mydocs_ui_app", _app)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
