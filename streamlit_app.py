"""
Streamlit Cloud entrypoint.

Streamlit Cloud auto-discovers `streamlit_app.py` at the repo root. This
shim simply forwards to the real app under `frontend/`.
"""

import os
import sys

# Make `frontend.*` importable when this file is invoked from the project root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the real Streamlit app; importing executes its top-level main() call.
from frontend import app  # noqa: F401
