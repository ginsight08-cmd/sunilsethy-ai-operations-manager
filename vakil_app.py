"""Deploy this entry point for legal case management only."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("app.py")), init_globals={"DEPLOYMENT_PRODUCT": "vakil"})
