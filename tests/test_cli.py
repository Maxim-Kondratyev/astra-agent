"""Tests for CLI argument handling."""

import subprocess
import sys


def test_help():
    """CLI should show help without errors."""
    result = subprocess.run([sys.executable, "-m", "astra", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "ASTRA" in result.stdout
    assert "--html" in result.stdout
    assert "--chat" in result.stdout
    assert "--checks-only" in result.stdout
    assert "--context-dir" in result.stdout


def test_module_choices():
    """CLI should list valid module choices."""
    result = subprocess.run([sys.executable, "-m", "astra", "--help"], capture_output=True, text=True)
    assert "security" in result.stdout
    assert "resilience" in result.stdout
    assert "saas" in result.stdout


def test_invalid_module():
    """CLI should reject invalid module names."""
    result = subprocess.run([sys.executable, "-m", "astra", "-m", "invalid"], capture_output=True, text=True)
    assert result.returncode != 0
