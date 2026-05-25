"""Bootstrap src/ no PYTHONPATH e logging isolado para unittest."""
import os
import sys
import tempfile
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_LOG_DIR = tempfile.mkdtemp(prefix="nbr12721-test-logs-")
os.environ.setdefault("PASTA_LOGS", _LOG_DIR)
os.environ.setdefault("LOG_LEVEL", "WARNING")

from nbr12721.settings.logging_setup import configurar_logging, reset_logging

reset_logging()
configurar_logging()
