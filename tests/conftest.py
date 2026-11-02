"""pytest configuration and shared fixtures."""

import json
import os

import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def fixtures_dir():
    """Return the path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def load_fixture():
    """Return a function that loads a JSON fixture file."""
    def _load(filename: str) -> dict:
        filepath = os.path.join(FIXTURES_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return _load


@pytest.fixture
def load_text_fixture():
    """Return a function that loads a text fixture file."""
    def _load(filename: str) -> str:
        filepath = os.path.join(FIXTURES_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return _load
