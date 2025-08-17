"""
Pytest configuration for nkd_agents tests.
"""

import pytest


def pytest_configure(config):
    """Configure pytest settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
