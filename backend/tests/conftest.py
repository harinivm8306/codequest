import os
import sys
import tempfile
from pathlib import Path

# isolated DB, no external services, before the app is imported
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["BHASHINI_USER_ID"] = ""
os.environ["BHASHINI_API_KEY"] = ""
os.environ["FRONTEND_DIST"] = f"{_tmp}/no-frontend"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def session(client):
    tok = client.post("/api/v1/session").json()["token"]
    return {"Authorization": f"Bearer {tok}"}
