"""Pytest configuration for the backend test suite.

Adds the ``backend/`` directory to ``sys.path`` so tests can use bare imports
like ``from agents.orchestrator import run_pipeline`` regardless of where
pytest is invoked from.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
