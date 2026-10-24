import sys
from pathlib import Path

# Torna o pacote "app" (que está em backend/) importável
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402