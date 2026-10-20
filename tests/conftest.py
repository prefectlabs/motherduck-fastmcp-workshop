"""Load the server under test.

By default the tests run against server.py at the repo root, which is the
file you deploy. To test a solution instead, set WORKSHOP_SERVER:

    WORKSHOP_SERVER=solutions/ex2/server.py uv run pytest tests/test_ex2.py
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from fastmcp import Client

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _load_server():
    path = ROOT / os.environ.get("WORKSHOP_SERVER", "server.py")
    spec = importlib.util.spec_from_file_location("server_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def server_module():
    return _load_server()


@pytest.fixture
async def client(server_module):
    async with Client(server_module.mcp) as connected:
        yield connected


@pytest.fixture(scope="session")
def server_source(server_module) -> str:
    return Path(server_module.__file__).read_text()
