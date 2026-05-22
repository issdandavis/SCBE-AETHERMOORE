import sys
from pathlib import Path

# apps/aether-desktop has a hyphen so it can't be a dotted Python import.
# Insert it on sys.path so `from backend.main import app` resolves correctly.
_APP_DIR = Path(__file__).resolve().parents[2]
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from backend.main import app

    return TestClient(app)
