"""Deploy this entry point for procurement only."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("app.py")), init_globals={"DEPLOYMENT_PRODUCT": "procurement"})
