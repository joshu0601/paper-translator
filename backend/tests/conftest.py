import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Isolated SQLite database + storage for the test session (set before app import).
_TEST_DIR = ROOT / "data" / "test"
_TEST_DIR.mkdir(parents=True, exist_ok=True)
_DB = _TEST_DIR / "test.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB.as_posix()}"
os.environ["STORAGE_LOCAL_DIR"] = str(_TEST_DIR / "uploads")
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["TRANSLATION_PROVIDER"] = "mock"


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
